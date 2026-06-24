"""Integration coverage for the E1 real installer bootstrap."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from creator_engine_validator import v3_installer


requires_ssh_keygen = pytest.mark.skipif(shutil.which("ssh-keygen") is None, reason="stock ssh-keygen not available")


def _signature_key_id(spec_text: str) -> str:
    match = re.search(r"(?m)^  key_id: (.+)$", spec_text)
    assert match is not None
    return match.group(1)


def _sign_with_test_key(spec_text: str, tmp_path: Path) -> tuple[str, str]:
    key_id = _signature_key_id(spec_text)
    key = tmp_path / "ce-test-root"
    subprocess.run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key), "-C", "ce-test-root"],
        check=True,
        capture_output=True,
    )
    canonical = v3_installer.canonical_spec_bytes(spec_text)
    canonical_path = tmp_path / "ce-spec.canonical"
    canonical_path.write_bytes(canonical)
    subprocess.run(
        ["ssh-keygen", "-Y", "sign", "-f", str(key), "-n", v3_installer.SSH_SIG_NAMESPACE, str(canonical_path)],
        check=True,
        capture_output=True,
    )
    sig_value = base64.b64encode((tmp_path / "ce-spec.canonical.sig").read_bytes()).decode("ascii")
    digest = hashlib.sha256(canonical).hexdigest()
    signed = re.sub(r"(?m)^(  value: ).*$", rf"\g<1>{sig_value}", spec_text)
    signed = re.sub(r"(?m)^(  content_sha256: ).*$", rf"\g<1>{digest}", signed)
    pub = (tmp_path / "ce-test-root.pub").read_text(encoding="utf-8").split()
    trust_root = f"{key_id} {pub[0]} {pub[1]}\n"
    return signed, trust_root


def _make_site(tmp_path: Path, repo_root: Path, *, tamper: bool = False) -> Path:
    site = tmp_path / "site"
    (site / "keys").mkdir(parents=True)
    (site / "schemas").mkdir()
    (site / "trust").mkdir()
    shutil.copytree(repo_root / "docs" / "downloads", site / "downloads")
    shutil.copy2(repo_root / "schemas" / "install-answers.schema.yaml", site / "schemas" / "install-answers.schema.yaml")
    spec_text = (repo_root / "docs" / "llms-install.md").read_text(encoding="utf-8")
    signed, trust_root = _sign_with_test_key(spec_text, tmp_path)
    if tamper:
        signed += "\ntamper\n"
    (site / "llms-install.md").write_text(signed, encoding="utf-8")
    (site / "keys" / "ce-root-v1").write_text(trust_root, encoding="utf-8")
    key_id = _signature_key_id(spec_text)
    fingerprint = v3_installer.public_key_fingerprint(trust_root)
    (site / "trust" / "ce-root-v1.txt").write_text(f"{key_id}={fingerprint}\n", encoding="utf-8")
    return site


def _fake_curl_bin(tmp_path: Path) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    curl = bin_dir / "curl"
    curl.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
orig="$*"
printf '%s\n' "$orig" >> "${FAKE_CURL_LOG}"
out=""
url=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    -o) out="$2"; shift 2 ;;
    --proto|--tlsv1.2|-fsSL|-f|-s|-S|-L) shift ;;
    *) url="$1"; shift ;;
  esac
done
if [ -z "$out" ] || [ -z "$url" ]; then
  echo "fake curl: missing -o or URL" >&2
  exit 2
fi
case "$url" in
  https://creator-engine.dev/*) rel="${url#https://creator-engine.dev/}" ;;
  "https://dns.google/resolve?name=_ce-root-v1.creator-engine.dev&type=TXT") rel="trust/ce-root-v1.txt" ;;
  *) echo "fake curl: unsupported URL $url" >&2; exit 2 ;;
esac
if [ "${FAKE_404_DOWNLOAD:-}" = "1" ] && [[ "$rel" == downloads/* ]]; then
  echo "curl: (22) The requested URL returned error: 404" >&2
  exit 22
fi
if [ -n "${FAKE_BAD_WHEEL:-}" ] && [[ "$rel" == "downloads/0.2.0/${FAKE_BAD_WHEEL}" ]]; then
  printf 'not the signed wheel bytes' > "$out"
  exit 0
fi
src="${FAKE_SITE}/${rel}"
if [ ! -f "$src" ]; then
  echo "curl: (22) The requested URL returned error: 404" >&2
  exit 22
fi
cp "$src" "$out"
""",
        encoding="utf-8",
    )
    curl.chmod(0o755)
    return bin_dir


def _run_install(
    tmp_path: Path,
    repo_root: Path,
    *,
    site: Path,
    install_root: Path | None = None,
    extra_env: dict[str, str] | None = None,
    answers: Path | None = None,
    extra_args: list[str] | None = None,
) -> subprocess.CompletedProcess[str]:
    fake_bin = _fake_curl_bin(tmp_path)
    curl_log = tmp_path / "curl.log"
    install_root = install_root or (tmp_path / "install-root")
    env = {
        **os.environ,
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
        "HOME": str(tmp_path / "home"),
        "FAKE_SITE": str(site),
        "FAKE_CURL_LOG": str(curl_log),
        "CE_TRUST_ANCHOR_SOURCE": "dns-txt:test",
    }
    # The bootstrap contract being tested is the signed wheel install. CI runs
    # pytest with PYTHONPATH=validators, but leaking that into the subprocess
    # makes the venv entry points import checkout source instead of the wheel.
    env.pop("PYTHONPATH", None)
    env.update(extra_env or {})
    argv = [
        shutil.which("bash") or "bash",
        str(repo_root / "docs" / "install.sh"),
        "--site",
        "https://creator-engine.dev",
        "--install-root",
        str(install_root),
    ]
    if answers is not None:
        argv += ["--answers", str(answers)]
    argv += list(extra_args or [])
    argv.append("--json")
    return subprocess.run(argv, cwd=repo_root, env=env, text=True, capture_output=True, timeout=120)


def _curl_urls(log_path: Path) -> list[str]:
    if not log_path.exists():
        return []
    urls = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        urls.extend(part for part in line.split() if part.startswith("https://"))
    return urls


@requires_ssh_keygen
def test_install_sh_ordering_refuses_before_artifacts_on_signature_failure(tmp_path: Path, repo_root: Path):
    site = _make_site(tmp_path, repo_root, tamper=True)
    install_root = tmp_path / "install-root"
    proc = _run_install(tmp_path, repo_root, site=site, install_root=install_root)
    assert proc.returncode != 0
    assert "signature_refused" in proc.stderr
    assert _curl_urls(tmp_path / "curl.log") == [
        "https://creator-engine.dev/llms-install.md",
        "https://creator-engine.dev/keys/ce-root-v1",
    ]
    assert not (install_root / "venv").exists()


@requires_ssh_keygen
def test_install_sh_refuses_equivalent_same_origin_anchor_before_artifacts(tmp_path: Path, repo_root: Path):
    site = _make_site(tmp_path, repo_root)
    install_root = tmp_path / "install-root"
    proc = _run_install(
        tmp_path,
        repo_root,
        site=site,
        install_root=install_root,
        extra_env={"CE_TRUST_ANCHOR_URL": "https://creator-engine.dev:443/trust/ce-root-v1.txt"},
    )
    assert proc.returncode != 0
    assert "trust_anchor_refused" in proc.stderr
    assert "shares origin" in proc.stderr
    assert _curl_urls(tmp_path / "curl.log") == [
        "https://creator-engine.dev/llms-install.md",
        "https://creator-engine.dev/keys/ce-root-v1",
    ]
    assert not (install_root / "venv").exists()


@requires_ssh_keygen
def test_install_sh_wheelhouse_hash_gate_leaves_venv_untouched(tmp_path: Path, repo_root: Path):
    site = _make_site(tmp_path, repo_root)
    install_root = tmp_path / "install-root"
    proc = _run_install(
        tmp_path,
        repo_root,
        site=site,
        install_root=install_root,
        extra_env={"FAKE_BAD_WHEEL": "attrs-26.1.0-py3-none-any.whl"},
    )
    assert proc.returncode != 0
    assert "artifact_hash_mismatch" in proc.stderr
    assert not (install_root / "venv").exists()


@requires_ssh_keygen
def test_install_sh_creates_venv_runs_inventory_and_idempotent_rerun(tmp_path: Path, repo_root: Path):
    site = _make_site(tmp_path, repo_root)
    install_root = tmp_path / "install-root"
    answers = tmp_path / "answers.yaml"
    answers.write_text("answers_version: 1\nprofile: solo-pilot\n", encoding="utf-8")
    first = _run_install(tmp_path, repo_root, site=site, install_root=install_root, answers=answers)
    assert first.returncode == 0, first.stderr
    payload = json.loads(first.stdout)
    assert payload["action"] == "onboard_inventory"
    assert payload["verified"]["trust_anchors"]["agreed"] == ["dns-txt:test"]
    assert "fingerprint" not in payload["verified"]["trust_anchors"]
    assert "trust_anchor_fingerprint" not in (install_root / "install-state").read_text(encoding="utf-8")
    rows = {row["key"]: row for row in payload["inventory"]}
    assert rows["profile"]["status"] == "answered:solo-pilot"
    assert (install_root / "venv" / "bin" / "cev3").is_file()
    local_bin = tmp_path / "home" / ".local" / "bin"
    for command in ("cev3", "ce"):
        shim = local_bin / command
        target = install_root / "venv" / "bin" / command
        assert shim.is_symlink()
        assert shim.resolve() == target.resolve()
    profile = tmp_path / "home" / ".profile"
    profile_text = profile.read_text(encoding="utf-8")
    assert "# >>> creator-engine PATH >>>" in profile_text
    assert "$HOME/.local/bin" in profile_text
    assert "npm" in profile_text
    assert not (install_root / "install.lock").exists()
    assert "installed=1" in first.stderr
    assert f"updated shell profile PATH block: {profile}" in first.stderr

    second = _run_install(tmp_path, repo_root, site=site, install_root=install_root, answers=answers)
    assert second.returncode == 0, second.stderr
    assert json.loads(second.stdout)["action"] == "onboard_inventory"
    assert "skipped_already_current=1" in second.stderr
    assert f"shell profile PATH block already current: {profile}" in second.stderr
    assert profile.read_text(encoding="utf-8") == profile_text
    for command in ("cev3", "ce"):
        shim = local_bin / command
        target = install_root / "venv" / "bin" / command
        assert shim.is_symlink()
        assert shim.resolve() == target.resolve()


@requires_ssh_keygen
def test_install_sh_no_fix_path_skips_profile_mutation(tmp_path: Path, repo_root: Path):
    site = _make_site(tmp_path, repo_root)
    install_root = tmp_path / "install-root"
    answers = tmp_path / "answers.yaml"
    answers.write_text("answers_version: 1\nprofile: solo-pilot\n", encoding="utf-8")

    proc = _run_install(
        tmp_path,
        repo_root,
        site=site,
        install_root=install_root,
        answers=answers,
        extra_args=["--no-fix-path"],
    )

    assert proc.returncode == 0, proc.stderr
    assert not (tmp_path / "home" / ".profile").exists()
    assert "skipped shell profile PATH update (--no-fix-path)" in proc.stderr


@requires_ssh_keygen
def test_install_sh_repairs_partial_or_corrupt_verified_venv_state(tmp_path: Path, repo_root: Path):
    site = _make_site(tmp_path, repo_root)
    answers = tmp_path / "answers.yaml"
    answers.write_text("answers_version: 1\nprofile: solo-pilot\n", encoding="utf-8")

    # Partial pre-state: a previous run left a non-symlink venv path and no
    # install-state. The rerun must preserve it out of the way, promote a
    # verified target, and converge without operator teardown.
    partial_root = tmp_path / "partial-root"
    partial_venv = partial_root / "venv"
    partial_venv.mkdir(parents=True)
    (partial_venv / "stale.txt").write_text("stale partial venv\n", encoding="utf-8")

    partial = _run_install(tmp_path, repo_root, site=site, install_root=partial_root, answers=answers)

    assert partial.returncode == 0, partial.stderr
    assert json.loads(partial.stdout)["action"] == "onboard_inventory"
    assert (partial_root / "venv").is_symlink()
    assert (partial_root / "venv" / "bin" / "cev3").is_file()
    assert not list(partial_root.glob("venv.previous.*"))

    # Corrupt pre-state: the state file exists, but the target entrypoint is
    # missing. The rerun must fail the current/target probes, rebuild from the
    # signed wheelhouse, and write a fresh valid state.
    corrupt_root = tmp_path / "corrupt-root"
    first = _run_install(tmp_path, repo_root, site=site, install_root=corrupt_root, answers=answers)
    assert first.returncode == 0, first.stderr
    state_before = (corrupt_root / "install-state").read_text(encoding="utf-8")
    target_line = next(line for line in state_before.splitlines() if line.startswith("venv_target="))
    target = Path(target_line.split("=", 1)[1])
    (target / "bin" / "cev3").unlink()

    repaired = _run_install(tmp_path, repo_root, site=site, install_root=corrupt_root, answers=answers)

    assert repaired.returncode == 0, repaired.stderr
    assert "building verified venv target" in repaired.stderr
    assert (target / "bin" / "cev3").is_file()
    assert (corrupt_root / "venv").is_symlink()
    assert json.loads(repaired.stdout)["action"] == "onboard_inventory"


def test_install_sh_missing_hard_dependency_refuses_before_fetch(tmp_path: Path, repo_root: Path):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    (fake_bin / "curl").write_text("#!/usr/bin/env sh\nexit 99\n", encoding="utf-8")
    (fake_bin / "curl").chmod(0o755)
    env = {**os.environ, "PATH": str(fake_bin), "HOME": str(tmp_path / "home")}
    proc = subprocess.run(
        [shutil.which("bash") or "bash", str(repo_root / "docs" / "install.sh"), "--install-root", str(tmp_path / "install")],
        cwd=repo_root,
        env=env,
        text=True,
        capture_output=True,
    )
    assert proc.returncode != 0
    assert "missing_bootstrap_dependency" in proc.stderr
    assert "ssh-keygen" in proc.stderr
    assert "Install OpenSSH client, then re-run this installer." in proc.stderr
    assert "sudo apt-get update && sudo apt-get install -y openssh-client" in proc.stderr
    assert "sudo dnf install -y openssh-clients" in proc.stderr
    assert "sudo apk add openssh-client" in proc.stderr
    assert "sudo pacman -Sy --needed openssh" in proc.stderr
    assert "brew install openssh" in proc.stderr
    assert "openssh-client" in proc.stderr
    assert "openssh-clients" in proc.stderr


@requires_ssh_keygen
@pytest.mark.parametrize("extra_env", [{"CE_TEST_UNAME_S": "Darwin"}, {"CE_TEST_UNAME_M": "sparc64"}])
def test_install_sh_refuses_uname_test_overrides_without_test_mode(
    tmp_path: Path, repo_root: Path, extra_env: dict[str, str]
):
    site = _make_site(tmp_path, repo_root)
    proc = _run_install(tmp_path, repo_root, site=site, extra_env=extra_env)
    assert proc.returncode != 0
    assert "test_override_refused" in proc.stderr
    assert "CE_INSTALLER_TEST_MODE=1" in proc.stderr
    assert _curl_urls(tmp_path / "curl.log") == []


@requires_ssh_keygen
def test_install_sh_unsupported_platform_and_pages_window_are_loud(tmp_path: Path, repo_root: Path):
    site = _make_site(tmp_path, repo_root)
    unsupported = _run_install(
        tmp_path,
        repo_root,
        site=site,
        extra_env={"CE_INSTALLER_TEST_MODE": "1", "CE_TEST_UNAME_S": "Darwin", "CE_TEST_UNAME_M": "arm64"},
    )
    assert unsupported.returncode != 0
    assert "unsupported_platform" in unsupported.stderr
    assert _curl_urls(tmp_path / "curl.log") == [
        "https://creator-engine.dev/llms-install.md",
        "https://creator-engine.dev/keys/ce-root-v1",
        "https://dns.google/resolve?name=_ce-root-v1.creator-engine.dev&type=TXT",
    ]

    fresh = tmp_path / "fresh"
    fresh.mkdir()
    site2 = _make_site(fresh, repo_root)
    pages = _run_install(
        fresh,
        repo_root,
        site=site2,
        extra_env={"FAKE_404_DOWNLOAD": "1"},
    )
    assert pages.returncode != 0
    assert "pages_mirror_not_ready" in pages.stderr


def test_unsigned_install_docs_defer_native_windows_one_liner_until_signed_release(repo_root: Path):
    index = (repo_root / "docs" / "index.html").read_text(encoding="utf-8")
    llms = (repo_root / "docs" / "llms.txt").read_text(encoding="utf-8")
    for text in (index, llms):
        assert "use WSL2/Ubuntu" in text
        assert "run the existing Linux installer inside WSL2" in text
        assert "native Windows one-liner remediation is pending signed installer release if needed" in text
    assert "PowerShell" not in index
    assert "native PowerShell, Git Bash, MSYS, or Cygwin" in llms


@requires_ssh_keygen
def test_install_sh_accepts_linux_aarch64_and_selects_arm_wheelhouse(tmp_path: Path, repo_root: Path):
    site = _make_site(tmp_path, repo_root)
    arm_pyyaml = (
        "pyyaml-6.0.3-cp314-cp314-manylinux2014_aarch64."
        "manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl"
    )
    proc = _run_install(
        tmp_path,
        repo_root,
        site=site,
        extra_env={
            "CE_INSTALLER_TEST_MODE": "1",
            "CE_TEST_UNAME_S": "Linux",
            "CE_TEST_UNAME_M": "aarch64",
            "FAKE_BAD_WHEEL": arm_pyyaml,
        },
    )
    assert proc.returncode != 0
    assert "artifact_hash_mismatch" in proc.stderr
    assert "unsupported_platform" not in proc.stderr
    assert arm_pyyaml in proc.stderr
    urls = _curl_urls(tmp_path / "curl.log")
    assert any(url.endswith(f"/downloads/0.2.0/{arm_pyyaml}") for url in urls)
    assert not any("pyyaml" in url and "x86_64" in url for url in urls)


def test_install_sh_fetch_hardening_and_uv_path_are_declared(repo_root: Path):
    script = (repo_root / "docs" / "install.sh").read_text(encoding="utf-8")
    assert "CURL_FLAGS=(--proto '=https' --tlsv1.2 -fsSL)" in script
    assert "mktemp -d" in script and "chmod 700" in script
    assert "UV_INSTALLER_URL=\"https://astral.sh/uv/install.sh\"" in script
    assert "curl --proto '=https' --tlsv1.2 -LsSf '$UV_INSTALLER_URL' | sh" in script
    assert "official uv installer completed but uv is not discoverable" in script
    assert "uv python install 3.14" in script
    assert "Remediation: uv python find 3.14" in script

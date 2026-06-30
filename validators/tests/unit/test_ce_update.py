from __future__ import annotations

import base64
import hashlib
import io
import json
import sys
import time
import zipfile
from argparse import Namespace
from pathlib import Path

import pytest

from creator_engine_validator import ce_cli
from creator_engine_validator import update as update_runtime
from creator_engine_validator import v3_installer

SITE = "https://mirror.test"
ANCHOR_URL = "https://dns.test/resolve?name=_ce-root-v1.creator-engine.dev&type=TXT"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _app_wheel(*, semver: str, build_sha: str) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as archive:
        archive.writestr(
            "creator_engine_validator/_version.py",
            f'SEMVER = "{semver}"\nBUILD_GIT_SHA = "{build_sha}"\n',
        )
    return out.getvalue()


def _spec_text(
    *,
    semver: str,
    sha256s_sha: str,
    app_wheel_sha: str,
    install_sha: str,
    schema_sha: str,
) -> bytes:
    sig = base64.b64encode(b"fake-sshsig").decode("ascii")
    app_wheel = f"creator_engine_validator-{semver}-py3-none-any.whl"
    text = f"""<!--
signature:
  key_id: ce-root-v1
  algo: ssh-ed25519
  namespace: ce-spec-v1
  value: {sig}
  content_sha256: {"0" * 64}

artifact_manifest:
  artifact_manifest_version: 1
  package_name: creator-engine-validator
  package_version: {semver}
  python_requires: >=3.14
  artifact_base_url: {SITE}/downloads/{semver}
  sha256s_url: {SITE}/downloads/{semver}/SHA256SUMS
  sha256s_sha256: {sha256s_sha}
  install_sh_url: {SITE}/install.sh
  install_sh_sha256s_entry: install.sh
  answers_schema_url: {SITE}/schemas/install-answers.schema.yaml
  answers_schema_sha256: {schema_sha}
  app_wheel: {app_wheel}
  required_wheels:
    - filename: {app_wheel}
      url: {SITE}/downloads/{semver}/{app_wheel}
      sha256: {app_wheel_sha}
      platforms: all
  python_acquisition:
    - platform: linux-x86_64-cp314
      tool: uv
      version: 0.0.0
      url: {SITE}/downloads/{semver}/uv.tar.gz
      sha256: {"1" * 64}
      command: uv python install 3.14
-->
"""
    digest = _sha(v3_installer.canonical_spec_bytes(text))
    return text.replace(f"content_sha256: {'0' * 64}", f"content_sha256: {digest}").encode()


def _fake_release(*, semver: str, build_sha: str) -> tuple[dict[str, bytes], str]:
    install = b"install-sh"
    schema = b"answers-schema"
    wheel = _app_wheel(semver=semver, build_sha=build_sha)
    install_sha = _sha(install)
    schema_sha = _sha(schema)
    wheel_sha = _sha(wheel)
    app_wheel = f"creator_engine_validator-{semver}-py3-none-any.whl"
    sha256s = (
        f"{install_sha}  install.sh\n"
        f"{schema_sha}  install-answers.schema.yaml\n"
        f"{wheel_sha}  {app_wheel}\n"
    ).encode()
    spec = _spec_text(
        semver=semver,
        sha256s_sha=_sha(sha256s),
        app_wheel_sha=wheel_sha,
        install_sha=install_sha,
        schema_sha=schema_sha,
    )
    trust_root = v3_installer.PINNED_KEYS["ce-root-v1"] + "\n"
    fingerprint = v3_installer.public_key_fingerprint(v3_installer.PINNED_KEYS["ce-root-v1"])
    anchor = json.dumps({"Answer": [{"data": f"ce-root-v1={fingerprint}"}]}).encode()
    mapping = {
        f"{SITE}/llms-install.md": spec,
        f"{SITE}/keys/ce-root-v1": trust_root.encode(),
        ANCHOR_URL: anchor,
        f"{SITE}/downloads/{semver}/SHA256SUMS": sha256s,
        f"{SITE}/install.sh": install,
        f"{SITE}/schemas/install-answers.schema.yaml": schema,
        f"{SITE}/downloads/{semver}/{app_wheel}": wheel,
    }
    return mapping, wheel_sha


def _fetcher(mapping: dict[str, bytes]):
    def _fetch(url: str) -> bytes:
        return mapping[url]

    return _fetch


def _accepting_runner(**kwargs) -> bool:
    return True


class FakeSwapper:
    def __init__(self, actions=("build_verified_venv", "promote_verified_venv", "write_install_state")):
        self.calls: list[tuple[Path, update_runtime.VerifiedRelease]] = []
        self.actions = actions

    def apply(self, root: Path, release: update_runtime.VerifiedRelease) -> tuple[str, ...]:
        self.calls.append((root, release))
        return tuple(self.actions)


def test_current_signed_release_is_noop_and_does_not_swap(tmp_path: Path):
    build_sha = "a" * 40
    mapping, _wheel_sha = _fake_release(semver="0.2.0", build_sha=build_sha)
    swapper = FakeSwapper()

    result = update_runtime.apply_update(
        install_root=tmp_path,
        site=SITE,
        trust_anchor_url=ANCHOR_URL,
        fetcher=_fetcher(mapping),
        sshsig_runner=_accepting_runner,
        installed=update_runtime.InstalledIdentity("0.2.0", build_sha),
        os_name="Linux",
        machine="x86_64",
        swapper=swapper,
    )

    assert result.ok is True
    assert result.status == "current"
    assert result.actions == ("noop_current",)
    assert swapper.calls == []


def test_available_signed_release_verifies_and_swaps(tmp_path: Path):
    mapping, wheel_sha = _fake_release(semver="0.3.0", build_sha="b" * 40)
    swapper = FakeSwapper()

    result = update_runtime.apply_update(
        install_root=tmp_path,
        site=SITE,
        trust_anchor_url=ANCHOR_URL,
        fetcher=_fetcher(mapping),
        sshsig_runner=_accepting_runner,
        installed=update_runtime.InstalledIdentity("0.2.0", "a" * 40),
        os_name="Linux",
        machine="x86_64",
        swapper=swapper,
    )

    assert result.ok is True
    assert result.status == "updated"
    assert result.available is not None
    assert result.available.semver == "0.3.0"
    assert result.available.app_wheel_sha256 == wheel_sha
    assert len(swapper.calls) == 1
    assert swapper.calls[0][0] == tmp_path


def test_verification_doubt_fails_closed_before_any_swap(tmp_path: Path):
    mapping, _wheel_sha = _fake_release(semver="0.3.0", build_sha="b" * 40)
    swapper = FakeSwapper()

    with pytest.raises(update_runtime.UpdateRefused):
        update_runtime.apply_update(
            install_root=tmp_path,
            site=SITE,
            trust_anchor_url=ANCHOR_URL,
            fetcher=_fetcher(mapping),
            sshsig_runner=lambda **kwargs: False,
            installed=update_runtime.InstalledIdentity("0.2.0", "a" * 40),
            os_name="Linux",
            machine="x86_64",
            swapper=swapper,
        )

    assert swapper.calls == []


def test_update_sshsig_runner_reports_actionable_missing_ssh_keygen(monkeypatch):
    monkeypatch.setattr(update_runtime.shutil, "which", lambda _name: None)

    with pytest.raises(update_runtime.UpdateRefused) as exc:
        update_runtime._ssh_keygen_verify_runner(
            message=b"message",
            signature=b"signature",
            allowed_signers=v3_installer.PINNED_KEYS["ce-root-v1"],
            identity="ce-root-v1",
            namespace=v3_installer.SSH_SIG_NAMESPACE,
        )

    detail = str(exc.value)
    assert "missing_dependency_ssh_keygen" in detail
    assert "sudo apt-get install -y openssh-client" in detail
    assert "sudo dnf install -y openssh-clients" in detail
    assert "brew install openssh" in detail


def test_update_sshsig_runner_reports_actionable_exec_race(monkeypatch):
    monkeypatch.setattr(update_runtime.shutil, "which", lambda name: f"/usr/bin/{name}")

    def missing_binary(*_args, **_kwargs):
        raise FileNotFoundError("ssh-keygen")

    monkeypatch.setattr(update_runtime.subprocess, "run", missing_binary)

    with pytest.raises(update_runtime.UpdateRefused) as exc:
        update_runtime._ssh_keygen_verify_runner(
            message=b"message",
            signature=b"signature",
            allowed_signers=v3_installer.PINNED_KEYS["ce-root-v1"],
            identity="ce-root-v1",
            namespace=v3_installer.SSH_SIG_NAMESPACE,
        )

    assert "missing_dependency_ssh_keygen" in str(exc.value)
    assert "openssh-clients" in str(exc.value)


def test_check_mode_is_read_only_with_signed_release():
    mapping, _wheel_sha = _fake_release(semver="0.3.0", build_sha="b" * 40)

    result = update_runtime.check_for_update(
        site=SITE,
        trust_anchor_url=ANCHOR_URL,
        fetcher=_fetcher(mapping),
        sshsig_runner=_accepting_runner,
        installed=update_runtime.InstalledIdentity("0.2.0", "a" * 40),
        os_name="Linux",
        machine="x86_64",
    )

    assert result.ok is True
    assert result.status == "available"
    assert result.read_only is True
    assert result.update_available is True
    assert result.available is not None
    assert result.available.token.startswith("0.3.0+")


def test_startup_notice_check_is_spec_only_and_downloads_no_wheels(tmp_path: Path):
    mapping, _wheel_sha = _fake_release(semver="0.3.1", build_sha="b" * 40)
    calls: list[str] = []

    def fetch(url: str) -> bytes:
        calls.append(url)
        return mapping[url]

    result = update_runtime.check_startup_update_notice(
        site=SITE,
        trust_anchor_url=ANCHOR_URL,
        fetcher=fetch,
        sshsig_runner=_accepting_runner,
        installed=update_runtime.InstalledIdentity("0.3.0", "a" * 40),
        cache_path=tmp_path / "update-check.json",
        now=100.0,
    )

    assert result.update_available is True
    assert result.notice_due is True
    assert calls == [
        f"{SITE}/llms-install.md",
        f"{SITE}/keys/ce-root-v1",
        ANCHOR_URL,
    ]
    assert not any(call.endswith(".whl") for call in calls)


def test_startup_notice_check_notice_shown_cache_suppresses_second_notice(tmp_path: Path):
    mapping, _wheel_sha = _fake_release(semver="0.3.1", build_sha="b" * 40)
    cache_path = tmp_path / "update-check.json"

    first = update_runtime.check_startup_update_notice(
        site=SITE,
        trust_anchor_url=ANCHOR_URL,
        fetcher=_fetcher(mapping),
        sshsig_runner=_accepting_runner,
        installed=update_runtime.InstalledIdentity("0.3.0", "a" * 40),
        cache_path=cache_path,
        now=100.0,
    )

    payload = json.loads(cache_path.read_text(encoding="utf-8"))
    payload["notice_shown"] = True
    cache_path.write_text(json.dumps(payload), encoding="utf-8")

    def forbidden_fetch(_url: str) -> bytes:
        raise AssertionError("fresh cache must skip fetch")

    second = update_runtime.check_startup_update_notice(
        site=SITE,
        trust_anchor_url=ANCHOR_URL,
        fetcher=forbidden_fetch,
        sshsig_runner=_accepting_runner,
        installed=update_runtime.InstalledIdentity("0.3.0", "a" * 40),
        cache_path=cache_path,
        now=101.0,
    )

    assert first.notice_due is True
    assert second.from_cache is True
    assert second.update_available is True
    assert second.notice_due is False


def test_startup_notice_check_fails_open_on_error_and_timeout(tmp_path: Path):
    def error_fetch(_url: str) -> bytes:
        raise RuntimeError("network down")

    error_result = update_runtime.check_startup_update_notice(
        fetcher=error_fetch,
        installed=update_runtime.InstalledIdentity("0.3.0", "a" * 40),
        cache_path=tmp_path / "error.json",
    )

    assert error_result.update_available is False
    assert error_result.notice_due is False

    def slow_fetch(_url: str) -> bytes:
        time.sleep(0.2)
        return b""

    start = time.monotonic()
    slow_result = update_runtime.check_startup_update_notice(
        fetcher=slow_fetch,
        installed=update_runtime.InstalledIdentity("0.3.0", "a" * 40),
        cache_path=tmp_path / "slow.json",
        fetch_timeout_seconds=0.01,
    )

    assert time.monotonic() - start < 0.15
    assert slow_result.update_available is False
    assert slow_result.notice_due is False


def test_startup_notice_check_opt_out_skips_fetch(tmp_path: Path):
    def forbidden_fetch(_url: str) -> bytes:
        raise AssertionError("opt-out must skip fetch")

    result = update_runtime.check_startup_update_notice(
        fetcher=forbidden_fetch,
        installed=update_runtime.InstalledIdentity("0.3.0", "a" * 40),
        cache_path=tmp_path / "disabled.json",
        env={update_runtime.STARTUP_UPDATE_DISABLE_ENV: "off"},
    )

    assert result.update_available is False
    assert result.reason == "disabled"


def test_startup_notice_prints_once_for_interactive_solo_stable(monkeypatch, capsys, tmp_path: Path):
    class Tty(io.StringIO):
        def isatty(self):
            return True

    cache_path = tmp_path / "ce-startup-test-cache.json"
    calls: list[str] = []

    def fake_check():
        calls.append("check")
        return update_runtime.StartupUpdateCheck(
            update_available=True,
            available_semver="0.3.1",
            notice_due=True,
            cache_path=cache_path,
        )

    shown: list[Path | None] = []

    monkeypatch.setattr(sys, "stdin", Tty())
    monkeypatch.setattr(sys, "stdout", Tty())
    monkeypatch.setattr(ce_cli.hook_check, "startup_toolchain_self_update_denied", lambda **_kwargs: (False, None))
    monkeypatch.setattr(update_runtime, "check_startup_update_notice", fake_check)
    monkeypatch.setattr(update_runtime, "mark_startup_update_notice_shown", lambda path=None: shown.append(path))

    ce_cli._maybe_print_startup_update_notice(Namespace(json_output=False))

    assert calls == ["check"]
    assert shown == [cache_path]
    assert "ce 0.3.1 available - run 'ce update'" in capsys.readouterr().err


def test_startup_notice_checker_off_for_contained_or_json(monkeypatch):
    class Tty(io.StringIO):
        def isatty(self):
            return True

    calls: list[str] = []

    def forbidden_check():
        calls.append("check")
        raise AssertionError("posture/json gate must skip checker")

    monkeypatch.setattr(sys, "stdin", Tty())
    monkeypatch.setattr(sys, "stdout", Tty())
    monkeypatch.setenv("CE_SEAT_ID", "dev-1")
    monkeypatch.setattr(update_runtime, "check_startup_update_notice", forbidden_check)

    ce_cli._maybe_print_startup_update_notice(Namespace(json_output=False))
    ce_cli._maybe_print_startup_update_notice(Namespace(json_output=True))

    assert calls == []


def test_ce_update_check_cli_uses_read_only_runtime(monkeypatch, capsys):
    calls: list[str] = []
    result = update_runtime.UpdateResult(
        ok=True,
        status="available",
        reason="update available",
        installed=update_runtime.InstalledIdentity("0.2.0", "a" * 40),
        available=update_runtime.ReleaseIdentity("0.3.0", "b" * 40, "app.whl", "c" * 64),
        update_available=True,
        read_only=True,
    )

    def fake_check(**kwargs):
        calls.append("check")
        return result

    def forbidden_apply(**kwargs):
        raise AssertionError("--check must not call apply_update")

    monkeypatch.setattr(update_runtime, "check_for_update", fake_check)
    monkeypatch.setattr(update_runtime, "apply_update", forbidden_apply)

    rc = ce_cli.main(["update", "--check", "--json"])

    assert rc == 0
    assert calls == ["check"]
    payload = json.loads(capsys.readouterr().out)
    assert payload["read_only"] is True
    assert payload["update_available"] is True

"""RV1-060 — Source Option B v1.0 packaging-contract tests (strict TDD).

These assert the locked Option B / 1B packaging contract over the *actual*
tracked packaging artifacts plus the introspection helpers in
``creator_engine_validator.packaging_runtime`` that ``ce doctor`` reuses for the
dependency/wheelhouse-drift guard clause (RV1-061 / RED-G-6).

Locked contract (``docs/governance/V1_PRODUCT_CONTRACT.md`` §6):

* ``requires-python = ">=3.14"`` (floor); tested/target band is **3.14.x**.
* runtime pins ``PyYAML==6.0.3`` and ``jsonschema==4.26.0``.
* cp314-only dual-arch Linux offline wheelhouse — **no** cp311/cp312/cp313 artifacts.
* ``uv.lock`` is the primary lock; ``requirements.txt`` is a lockstep export.
* build backend ``setuptools.build_meta``; both ``creator-engine-validator`` and
  ``ce`` console scripts retained; distribution **not** renamed (DP-1 = A).
"""
from __future__ import annotations

import hashlib
import tomllib
import zipfile
from pathlib import Path

import pytest

from creator_engine_validator import packaging_runtime as pkg


@pytest.fixture()
def validators_dir(repo_root: Path) -> Path:
    return repo_root / "validators"


# ---------------------------------------------------------------------------
# packaging_runtime pure helpers (interpreter target band)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("version_info", [(3, 14, 0), (3, 14, 5), (3, 14, 9)])
def test_interpreter_in_contract_accepts_target_band(version_info):
    assert pkg.interpreter_in_contract(version_info) is True


@pytest.mark.parametrize("version_info", [(3, 13, 13), (3, 12, 8), (3, 11, 15), (3, 15, 0)])
def test_interpreter_in_contract_refuses_out_of_contract(version_info):
    # 3.13/3.15 are the named out-of-contract interpreters (RED-G-1).
    assert pkg.interpreter_in_contract(version_info) is False


def test_normalize_name_pep503():
    assert pkg.normalize_name("PyYAML") == "pyyaml"
    assert pkg.normalize_name("jsonschema-specifications") == "jsonschema-specifications"
    assert pkg.normalize_name("rpds_py") == "rpds-py"


# ---------------------------------------------------------------------------
# pyproject.toml contract
# ---------------------------------------------------------------------------


def test_pyproject_requires_python_floor(validators_dir: Path):
    data = tomllib.loads((validators_dir / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["requires-python"] == ">=3.14"


def test_pyproject_pins_runtime_dependencies(validators_dir: Path):
    data = tomllib.loads((validators_dir / "pyproject.toml").read_text(encoding="utf-8"))
    deps = {pkg.normalize_name(d.split("==")[0]): d.split("==")[1] for d in data["project"]["dependencies"]}
    assert deps["pyyaml"] == "6.0.3"
    assert deps["jsonschema"] == "4.26.0"


def test_pyproject_retains_both_console_scripts(validators_dir: Path):
    data = tomllib.loads((validators_dir / "pyproject.toml").read_text(encoding="utf-8"))
    scripts = data["project"]["scripts"]
    assert scripts["creator-engine-validator"] == "creator_engine_validator.cli:main"
    assert scripts["ce"] == "creator_engine_validator.ce_cli:main"


def test_pyproject_keeps_setuptools_build_meta(validators_dir: Path):
    data = tomllib.loads((validators_dir / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["build-system"]["build-backend"] == "setuptools.build_meta"


def test_pyproject_does_not_rename_distribution(validators_dir: Path):
    data = tomllib.loads((validators_dir / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["name"] == "creator-engine-validator"


# ---------------------------------------------------------------------------
# wheelhouse: cp314-only
# ---------------------------------------------------------------------------


def test_wheelhouse_has_no_stale_non_cp314_abi_wheels(validators_dir: Path):
    wheels = pkg.wheelhouse_wheels(validators_dir / "wheelhouse")
    offenders = [w for w in wheels if any(tag in w for tag in pkg.FORBIDDEN_ABI_TAGS)]
    assert offenders == [], f"non-cp314 ABI wheels must be removed: {offenders}"


def test_wheelhouse_contains_cp314_abi_wheels(validators_dir: Path):
    wheels = pkg.wheelhouse_wheels(validators_dir / "wheelhouse")
    cp314 = [w for w in wheels if "cp314" in w]
    assert cp314, "wheelhouse must contain at least one cp314 ABI wheel (e.g. PyYAML/rpds-py)"


def test_wheelhouse_contains_linux_x86_64_and_aarch64_native_wheels(validators_dir: Path):
    wheels = pkg.wheelhouse_wheels(validators_dir / "wheelhouse")
    expected_fragments = [
        "pyyaml-6.0.3-cp314-cp314-manylinux2014_x86_64",
        "pyyaml-6.0.3-cp314-cp314-manylinux2014_aarch64",
        "rpds_py-0.30.0-cp314-cp314-manylinux_2_17_x86_64",
        "rpds_py-0.30.0-cp314-cp314-manylinux_2_17_aarch64",
        "uv-0.11.21-py3-none-manylinux_2_17_aarch64",
    ]
    for fragment in expected_fragments:
        assert any(fragment in wheel for wheel in wheels), f"wheelhouse missing {fragment}: {wheels}"


def test_wheelhouse_covers_runtime_dependencies(validators_dir: Path):
    names = {pkg.normalize_name(n) for n in pkg.wheelhouse_distribution_names(validators_dir / "wheelhouse")}
    for required in ("pyyaml", "jsonschema", "attrs", "jsonschema-specifications", "referencing", "rpds-py"):
        assert required in names, f"wheelhouse missing offline wheel for {required}: have {sorted(names)}"


# ---------------------------------------------------------------------------
# uv.lock primary + requirements.txt lockstep export
# ---------------------------------------------------------------------------


def test_uv_lock_present_and_pins_contract(validators_dir: Path):
    lock = pkg.parse_uv_lock(validators_dir / "uv.lock")
    assert lock["pyyaml"] == "6.0.3"
    assert lock["jsonschema"] == "4.26.0"


def test_requirements_export_is_lockstep_with_uv_lock(validators_dir: Path):
    violations = pkg.lockstep_violations(
        validators_dir / "requirements.txt", validators_dir / "uv.lock"
    )
    assert violations == [], f"requirements.txt drifted from uv.lock: {violations}"


def test_requirements_has_no_stale_pins(validators_dir: Path):
    reqs = pkg.parse_requirements(validators_dir / "requirements.txt")
    assert reqs.get("pyyaml") == "6.0.3"
    assert reqs.get("jsonschema") == "4.26.0"
    # the old cp311-era transitive pins must be gone
    assert reqs.get("attrs") != "24.2.0"
    assert reqs.get("rpds-py") != "0.22.3"


# ---------------------------------------------------------------------------
# aggregate contract verifier (used by the guard)
# ---------------------------------------------------------------------------


def test_verify_packaging_contract_is_clean_on_repo(repo_root: Path):
    result = pkg.verify_packaging_contract(repo_root)
    assert result.ok, f"packaging contract violations: {result.violations}"


def test_verify_wheel_matches_source_is_clean_on_repo(repo_root: Path):
    violations = pkg.verify_wheel_matches_source(repo_root)
    assert violations == []


def test_verify_wheel_matches_source_flags_synthetic_drift(tmp_path: Path):
    validators_dir = tmp_path / "validators"
    source_dir = validators_dir / "creator_engine_validator"
    wheelhouse = validators_dir / "wheelhouse"
    source_dir.mkdir(parents=True)
    wheelhouse.mkdir()
    (validators_dir / "pyproject.toml").write_text(
        "[project]\nname = \"creator-engine-validator\"\nversion = \"0.2.0\"\n",
        encoding="utf-8",
    )
    (source_dir / "__init__.py").write_text("", encoding="utf-8")
    (source_dir / "version.py").write_text("__version__ = \"0.2.0\"\n", encoding="utf-8")
    (source_dir / "drift.py").write_text("VALUE = 'source'\n", encoding="utf-8")

    wheel = wheelhouse / "creator_engine_validator-0.2.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as zf:
        zf.writestr("creator_engine_validator/__init__.py", "")
        zf.writestr("creator_engine_validator/version.py", "__version__ = \"0.2.0\"\n")
        zf.writestr("creator_engine_validator/drift.py", "VALUE = 'wheel'\n")

    violations = pkg.verify_wheel_matches_source(tmp_path)
    assert any("differs from source file drift.py" in violation for violation in violations)


def test_verify_packaging_contract_flags_missing_wheelhouse(tmp_path: Path):
    # an empty/absent packaging tree must be reported as drift, not crash
    result = pkg.verify_packaging_contract(tmp_path)
    assert not result.ok
    assert result.violations


# ---------------------------------------------------------------------------
# ce-ops#25: generated _version.py parity (semver + baked SHA)
# ---------------------------------------------------------------------------


def test_verify_generated_version_is_clean_on_repo(repo_root: Path):
    violations = pkg.verify_generated_version(repo_root)
    assert violations == [], f"generated _version.py parity violations: {violations}"


def _synthetic_source_tree(tmp_path: Path, *, semver: str, build_sha: str) -> Path:
    validators_dir = tmp_path / "validators"
    source_dir = validators_dir / "creator_engine_validator"
    source_dir.mkdir(parents=True)
    (validators_dir / "pyproject.toml").write_text(
        "[project]\nname = \"creator-engine-validator\"\nversion = \"0.2.0\"\n",
        encoding="utf-8",
    )
    (source_dir / "_version.py").write_text(
        f'SEMVER = "{semver}"\nBUILD_GIT_SHA = "{build_sha}"\n', encoding="utf-8"
    )
    return tmp_path


def test_verify_generated_version_flags_semver_drift(tmp_path: Path):
    root = _synthetic_source_tree(tmp_path, semver="9.9.9", build_sha="0" * 40)
    violations = pkg.verify_generated_version(root)
    assert any("SEMVER" in v and "differs from pyproject" in v for v in violations)


def test_verify_generated_version_flags_malformed_baked_sha(tmp_path: Path):
    root = _synthetic_source_tree(tmp_path, semver="0.2.0", build_sha="not-a-real-sha")
    violations = pkg.verify_generated_version(root)
    assert any("BUILD_GIT_SHA" in v and "40-hex" in v for v in violations)


def test_verify_generated_version_flags_missing_file(tmp_path: Path):
    validators_dir = tmp_path / "validators"
    source_dir = validators_dir / "creator_engine_validator"
    source_dir.mkdir(parents=True)
    (validators_dir / "pyproject.toml").write_text(
        "[project]\nname = \"creator-engine-validator\"\nversion = \"0.2.0\"\n",
        encoding="utf-8",
    )
    violations = pkg.verify_generated_version(tmp_path)
    assert any("missing generated build-identity file" in v for v in violations)


def test_verify_generated_version_noop_without_source_tree(tmp_path: Path):
    # an installed/wheel-only context (no source checkout) must not fabricate drift
    assert pkg.verify_generated_version(tmp_path) == []


def _fake_git_runner(*, shallow: bool, cat_file_ok: bool):
    """A ``_git`` seam stand-in shaped like a depth-1 (or full) clone."""
    import subprocess

    def runner(repo_root, *args):
        sub = args[0]
        if sub == "rev-parse" and "--verify" in args:
            return subprocess.CompletedProcess(args, 0, stdout="deadbeef\n", stderr="")
        if sub == "cat-file":
            return subprocess.CompletedProcess(args, 0 if cat_file_ok else 1, stdout="", stderr="")
        if sub == "rev-parse" and "--is-shallow-repository" in args:
            return subprocess.CompletedProcess(
                args, 0, stdout=("true" if shallow else "false") + "\n", stderr=""
            )
        if sub == "merge-base":  # --is-ancestor: success
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    return runner


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_baked_sha_probe_skips_on_shallow_clone_with_absent_object(monkeypatch, tmp_path: Path):
    # depth-1 CI checkout: the baked merge-parent base is truncated away, not
    # missing — the probe must SKIP (regression: PR #214 review CHANGES_REQUESTED).
    monkeypatch.setattr(pkg, "_git", _fake_git_runner(shallow=True, cat_file_ok=False))
    assert pkg._baked_sha_git_problem(tmp_path, "a" * 40) is None


def test_baked_sha_probe_flags_absent_object_on_full_clone(monkeypatch, tmp_path: Path):
    # a FULL clone CAN distinguish a genuine missing/foreign sha -> still a violation
    monkeypatch.setattr(pkg, "_git", _fake_git_runner(shallow=False, cat_file_ok=False))
    problem = pkg._baked_sha_git_problem(tmp_path, "a" * 40)
    assert problem and "not a commit in this repository" in problem


def _parse_sha256sums(path: Path) -> dict[str, str]:
    """Parse a ``SHA256SUMS`` manifest into ``{filename: digest}``.

    Tolerates the ``*`` binary-mode marker coreutils prefixes onto
    filenames; blank lines are ignored.
    """
    sums: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, filename = line.split(maxsplit=1)
        sums[filename.lstrip("*")] = digest
    return sums


def test_pages_mirror_wheels_match_published_sha256sums(repo_root: Path):
    # ce-ops#69 re-scope: the published 0.2.0 Pages mirror is a FROZEN,
    # self-verifying release artifact. Every wheel under docs/downloads/0.2.0/
    # must hash to the digest recorded in its OWN SHA256SUMS -- we assert the
    # mirror's INTERNAL self-consistency, NOT a byte-match against the live dev
    # validators/wheelhouse/ (which advances to 0.2.0+sha freely; the published
    # wheel only changes at a ratified release + re-sign -> 0.3.0). The dev
    # wheel<->source contract stays covered by verify_wheel_matches_source.
    mirror = repo_root / "docs" / "downloads" / "0.2.0"
    sums = _parse_sha256sums(mirror / "SHA256SUMS")
    wheels = sorted(path.name for path in mirror.glob("*.whl"))
    assert wheels, "published mirror must contain installable wheels"
    for filename in wheels:
        assert filename in sums, f"published wheel missing from SHA256SUMS: {filename}"
        assert sums[filename] == _sha256(mirror / filename), f"published wheel digest drift: {filename}"


def test_pages_mirror_sha256s_publishes_install_sh_and_wheels(repo_root: Path):
    # ce-ops#69 re-scope: SHA256SUMS publishes install.sh + the mirror's OWN
    # wheels, and every published digest matches the actual published artifact
    # in-place (docs/install.sh for the installer, docs/downloads/0.2.0/ for the
    # wheels) -- NOT validators/wheelhouse/. Together with the test above this
    # pins a bijection between the mirror's wheel files and its SHA256SUMS wheel
    # entries, so neither an orphan file nor an unpublished wheel can slip in.
    mirror = repo_root / "docs" / "downloads" / "0.2.0"
    sums = _parse_sha256sums(mirror / "SHA256SUMS")
    assert sums["install.sh"] == _sha256(repo_root / "docs" / "install.sh")
    published_wheels = sorted(name for name in sums if name.endswith(".whl"))
    assert published_wheels, "SHA256SUMS must publish at least one wheel"
    for filename in published_wheels:
        wheel = mirror / filename
        assert wheel.is_file(), f"SHA256SUMS publishes a wheel absent from the mirror: {filename}"
        assert sums[filename] == _sha256(wheel)


def test_pages_mirror_publishes_dual_arch_native_wheels(repo_root: Path):
    mirror = repo_root / "docs" / "downloads" / "0.2.0"
    wheels = sorted(path.name for path in mirror.glob("*.whl"))
    expected_fragments = [
        "pyyaml-6.0.3-cp314-cp314-manylinux2014_x86_64",
        "pyyaml-6.0.3-cp314-cp314-manylinux2014_aarch64",
        "rpds_py-0.30.0-cp314-cp314-manylinux_2_17_x86_64",
        "rpds_py-0.30.0-cp314-cp314-manylinux_2_17_aarch64",
        "uv-0.11.21-py3-none-manylinux_2_17_x86_64",
        "uv-0.11.21-py3-none-manylinux_2_17_aarch64",
    ]
    for fragment in expected_fragments:
        assert any(fragment in wheel for wheel in wheels), f"mirror missing {fragment}: {wheels}"

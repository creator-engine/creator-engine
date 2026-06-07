"""Unit tests for the v3 naming-hygiene fitness function (G-4.1).

A self/structural check: it scans the v3 CODE surface (via the `_versions`
taxonomy) + the declared v3 SCHEMA surface for CE bootstrapping-harness residue
(`.hermes`/`Hermes`/`Nefarious`), green-on-day-one + ratcheting. These tests do
ZERO live IO beyond reading the package + temp files.
"""

from creator_engine_validator import _versions as ver
from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks import v3_naming_hygiene as h


def _fmt(errors) -> str:
    return " ".join(e.format() for e in errors).lower()


# --- registration + green-on-day-one ---------------------------------------
def test_registered():
    assert "v3_naming_hygiene" in registered_checks()


def test_green_on_the_real_v3_surface():
    errors, warnings = h.evaluate()
    assert errors == [], [e.format() for e in errors]
    assert warnings == []


def test_allowlist_empty_on_main():
    assert ver.BASELINE_V3_NAMING_ALLOWLIST == frozenset()


def test_v3_schemas_declared_and_exist():
    root = h._repo_root()
    assert ver.V3_SCHEMAS  # non-empty
    for schema_rel in ver.V3_SCHEMAS:
        assert (root / schema_rel).is_file(), schema_rel


def test_neutral_local_state_root_is_ce_namespaced_never_hermes_or_claude():
    assert ver.V3_LOCAL_STATE_ROOT.startswith(".ce/")
    assert ".hermes" not in ver.V3_LOCAL_STATE_ROOT
    assert ".claude" not in ver.V3_LOCAL_STATE_ROOT


# --- teeth: residue in a v3 CODE module fires ------------------------------
def _as_v3_module(monkeypatch, path, name="fake_v3_mod"):
    monkeypatch.setattr(h, "discover_modules", lambda pkg: {f"creator_engine_validator.{name}": path})
    monkeypatch.setattr(ver, "classify", lambda rel: ver.V3 if rel == name else ver.SHARED)


def test_residue_hermes_path_in_v3_module_fires(tmp_path, monkeypatch):
    f = tmp_path / "fake_v3_mod.py"
    f.write_text("STATE_ROOT = '.hermes/research'\n", encoding="utf-8")
    _as_v3_module(monkeypatch, f)
    errors, _ = h.evaluate()
    assert any(e.code == h.CODE_RESIDUE for e in errors)
    assert "hermes" in _fmt(errors)


def test_residue_hermes_and_nefarious_names_fire(tmp_path, monkeypatch):
    f = tmp_path / "fake_v3_mod.py"
    f.write_text("# the Hermes role runs on the Nefarious machine\n", encoding="utf-8")
    _as_v3_module(monkeypatch, f)
    errors, _ = h.evaluate()
    fmt = _fmt(errors)
    assert "hermes" in fmt and "nefarious" in fmt


# --- scope correctness: residue outside the v3 surface does NOT fire --------
def test_residue_in_non_v3_module_does_not_fire(tmp_path, monkeypatch):
    f = tmp_path / "fake_v1_mod.py"
    f.write_text("ROOT = '.hermes/'\n", encoding="utf-8")
    monkeypatch.setattr(h, "discover_modules", lambda pkg: {"creator_engine_validator.fake_v1_mod": f})
    monkeypatch.setattr(ver, "classify", lambda rel: ver.V1)  # v1, never scanned
    errors, _ = h.evaluate()
    assert errors == []


# --- adapter-name safety: legit transport/runtime names are NOT residue ----
def test_legit_adapter_names_do_not_fire(tmp_path, monkeypatch):
    f = tmp_path / "fake_v3_adapter.py"
    f.write_text(
        "# Claude Code hook adapter; gVisor backend; Codex; ACP transport; OpenShell\n",
        encoding="utf-8",
    )
    _as_v3_module(monkeypatch, f, name="fake_v3_adapter")
    errors, _ = h.evaluate()
    assert errors == []


def test_real_v3_adapters_are_clean():
    # cc_hook_adapter (Claude) + gvisor_proxy_backend (gVisor) are real v3 adapters
    # and MUST NOT trip the check (they are clean on the real surface).
    errors, _ = h.evaluate()
    assert not any(
        ("cc_hook_adapter" in e.format()) or ("gvisor_proxy_backend" in e.format())
        for e in errors
    )


# --- allowlist suppression + stale warning ---------------------------------
def test_allowlist_suppresses_residue(tmp_path, monkeypatch):
    f = tmp_path / "fake_v3_mod.py"
    f.write_text("ROOT = '.hermes/'\n", encoding="utf-8")
    _as_v3_module(monkeypatch, f)
    relp = h._relpath(f, h._repo_root())
    monkeypatch.setattr(ver, "BASELINE_V3_NAMING_ALLOWLIST", frozenset({(relp, "hermes")}))
    errors, warnings = h.evaluate()
    assert errors == []      # suppressed by the baselined entry
    assert warnings == []    # the entry was used, so not stale


def test_stale_allowlist_entry_warns(monkeypatch):
    monkeypatch.setattr(
        ver, "BASELINE_V3_NAMING_ALLOWLIST", frozenset({("validators/x/gone.py", "hermes")})
    )
    errors, warnings = h.evaluate()
    assert any(w.code == h.CODE_STALE for w in warnings)


# --- completeness: a missing declared v3 schema fires ----------------------
def test_missing_declared_schema_fires(monkeypatch):
    monkeypatch.setattr(ver, "V3_SCHEMAS", frozenset({"schemas/does-not-exist.schema.yaml"}))
    errors, _ = h.evaluate()
    assert any(e.code == h.CODE_MISSING_SCHEMA for e in errors)

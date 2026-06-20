"""Unit tests for the cockpit persona preference (ce-ops#45 elevation).

The CEO ↔ Dev face is a small, instance-local UI **preference** — NOT governance
state and NOT part of the L2 snapshot fold. It is owned by the cockpit
composition root (``v3_cli._cmd_cockpit``) and injected into the L3 view, so the
view layer never performs I/O (the L3 source guard stays green). This module is
a pure normalize/fold core plus a narrow, tolerant I/O edge at
``<root>/cockpit/prefs.json`` — the same "pure core + 1 I/O edge" shape as the
read-model.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from creator_engine_validator.runner import cockpit_prefs as prefs

VALIDATORS_DIR = Path(__file__).resolve().parents[2]


def test_personas_and_default():
    # the journey (CEO) face is the DEFAULT; the expert board is the Dev face.
    assert prefs.PERSONAS == ("ceo", "dev")
    assert prefs.DEFAULT_PERSONA == "ceo"
    assert prefs.PERSONA_CEO == "ceo"
    assert prefs.PERSONA_DEV == "dev"


def test_normalize_persona_is_pure_and_tolerant():
    assert prefs.normalize_persona("ceo") == "ceo"
    assert prefs.normalize_persona("dev") == "dev"
    assert prefs.normalize_persona("CEO") == "ceo"        # case-insensitive
    assert prefs.normalize_persona("  Dev ") == "dev"      # whitespace-tolerant
    for junk in (None, "", "nonsense", 7, {"x": 1}, ["dev"]):
        assert prefs.normalize_persona(junk) == prefs.DEFAULT_PERSONA


def test_fold_prefs_is_pure_with_honest_defaults():
    assert prefs.fold_prefs(None)["persona"] == "ceo"
    assert prefs.fold_prefs({})["persona"] == "ceo"
    assert prefs.fold_prefs({"persona": "dev"})["persona"] == "dev"
    assert prefs.fold_prefs({"persona": "bogus"})["persona"] == "ceo"
    # JSON-round-trippable (a plain serializable dict).
    folded = prefs.fold_prefs({"persona": "dev"})
    assert json.loads(json.dumps(folded)) == folded


def test_prefs_path_is_the_documented_instance_local_path(tmp_path):
    assert prefs.prefs_path(tmp_path) == Path(tmp_path) / "cockpit" / "prefs.json"


def test_load_persona_missing_root_is_default(tmp_path):
    # no prefs file yet -> the default face, never an error.
    assert prefs.load_persona(tmp_path) == "ceo"


def test_save_then_load_round_trips(tmp_path):
    returned = prefs.save_persona(tmp_path, "dev")
    assert returned == "dev"
    assert prefs.load_persona(tmp_path) == "dev"
    p = prefs.prefs_path(tmp_path)
    assert p.is_file()
    doc = json.loads(p.read_text(encoding="utf-8"))
    assert doc["persona"] == "dev"


def test_save_persona_normalizes_unknown_to_default(tmp_path):
    assert prefs.save_persona(tmp_path, "nonsense") == "ceo"
    assert prefs.load_persona(tmp_path) == "ceo"


def test_save_persona_overwrites_in_place(tmp_path):
    prefs.save_persona(tmp_path, "dev")
    prefs.save_persona(tmp_path, "ceo")
    assert prefs.load_persona(tmp_path) == "ceo"


def test_load_persona_tolerates_malformed_file(tmp_path):
    p = prefs.prefs_path(tmp_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("{ this is not json", encoding="utf-8")
    # tolerant: a corrupt UI pref must never crash the cockpit launch.
    assert prefs.load_persona(tmp_path) == "ceo"


def test_load_persona_tolerates_non_dict_document(tmp_path):
    p = prefs.prefs_path(tmp_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(["dev"]), encoding="utf-8")
    assert prefs.load_persona(tmp_path) == "ceo"


def test_prefs_imports_no_textual():
    import os
    import subprocess

    code = (
        "import sys\n"
        "from creator_engine_validator.runner import cockpit_prefs\n"
        "assert 'textual' not in sys.modules, 'prefs must not import textual'\n"
        "assert 'watchfiles' not in sys.modules\n"
    )
    env = {**os.environ, "PYTHONPATH": str(VALIDATORS_DIR)}
    proc = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr

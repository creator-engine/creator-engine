"""CE v3.5-B / ce-ops#45 — the cockpit persona preference (CEO ↔ Dev face).

The cockpit elevation makes the solo-founder **journey** the default face and
demotes the expert ops board to a **Dev** face you switch to. Which face you land
on is a small, per-instance UI **preference** — it is NOT governance state, it is
NOT a datum about the fleet, and so it is deliberately **not** part of the L2
``fold_snapshot`` (the snapshot stays a pure read-model of governance state, and
``ce cockpit --json`` is unchanged by it).

The preference is owned by the cockpit **composition root** (``v3_cli._cmd_cockpit``):
it is read here at launch and passed INTO the L3 view as data, and the view calls
an injected callback to persist a toggle — so the Textual view performs no file
I/O of its own (the L3 source guard, which forbids ``open(`` / ``read_text`` /
``safe_load`` in ``v3_cockpit.py``, stays green).

Shape: a pure normalize/fold core (no disk) plus a narrow, tolerant I/O edge at
``<root>/cockpit/prefs.json`` — the same "pure core + 1 I/O edge" pattern as the
read-model. A missing or malformed preference degrades honestly to the default
face and never raises (a corrupt UI pref must never crash a cockpit launch).

Textual-free by construction (imported on every cockpit path, including
``--json``).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping

#: The two cockpit faces. ``ceo`` is the solo-founder journey (the DEFAULT face);
#: ``dev`` is the expert ops board, demoted to a switch-to face (ce-ops#45).
PERSONA_CEO = "ceo"
PERSONA_DEV = "dev"
PERSONAS = (PERSONA_CEO, PERSONA_DEV)

#: The journey face is the default — the cockpit opens in CEO mode unless a
#: persisted preference says otherwise.
DEFAULT_PERSONA = PERSONA_CEO

#: Instance-local layout for the preference (beside the other instance-local
#: cockpit state under the v3 state root). A namespaced subdir keeps a UI
#: preference visibly distinct from governance artifacts (scopes/, escalations/).
PREFS_SUBDIR = "cockpit"
PREFS_FILENAME = "prefs.json"
PREFS_SCHEMA_VERSION = "1"


def normalize_persona(value: Any) -> str:
    """Coerce any value to a known persona, falling back to the default (PURE).

    Case-insensitive and whitespace-tolerant; anything unrecognized (including
    ``None``, non-strings, or junk) becomes :data:`DEFAULT_PERSONA`. Never raises.
    """
    if isinstance(value, str):
        candidate = value.strip().lower()
        if candidate in PERSONAS:
            return candidate
    return DEFAULT_PERSONA


def fold_prefs(doc: Mapping[str, Any] | None) -> dict[str, Any]:
    """Fold a (possibly absent/garbage) prefs document into the normalized prefs (PURE).

    Returns a plain, JSON-serializable dict carrying the resolved persona and the
    schema version. The single source of persona truth for both load and save.
    """
    persona = normalize_persona(doc.get("persona")) if isinstance(doc, Mapping) else DEFAULT_PERSONA
    return {"schema_version": PREFS_SCHEMA_VERSION, "persona": persona}


def prefs_path(state_root: Path | str) -> Path:
    """Return the instance-local prefs path ``<root>/cockpit/prefs.json`` (pure path math)."""
    return Path(state_root) / PREFS_SUBDIR / PREFS_FILENAME


def load_persona(state_root: Path | str) -> str:
    """Read the persisted persona (the I/O edge); degrade honestly to the default.

    A missing file, an unreadable file, non-JSON content, or a non-object document
    all resolve to :data:`DEFAULT_PERSONA` — a corrupt UI preference must never
    crash the cockpit launch.
    """
    path = prefs_path(state_root)
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return DEFAULT_PERSONA
    return fold_prefs(doc if isinstance(doc, Mapping) else None)["persona"]


def save_persona(state_root: Path | str, persona: Any) -> str:
    """Persist the persona to ``<root>/cockpit/prefs.json`` (the I/O edge); return it normalized.

    Normalizes before writing (an unknown value persists as the default), creates
    the namespaced subdir, and writes atomically (temp file + ``os.replace``) so a
    crash mid-write can never leave a half-written preference behind.
    """
    resolved = normalize_persona(persona)
    path = prefs_path(state_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(fold_prefs({"persona": resolved}), indent=2, sort_keys=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(payload, encoding="utf-8")
    os.replace(tmp, path)
    return resolved

"""Mediated brain ledger append intent loader and host worker skeleton."""
from __future__ import annotations
import difflib
import json
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import yaml
from . import brain_runtime
from .reporting import ValidationError, make_error
from .schema import validate_with_schema
SCHEMA_PATH = Path(__file__).with_name("brain_append_intent.schema.yaml")
CONTRACT = SCHEMA_PATH.name
LEDGER_PATH = ".ce/brain/assertions.yaml"
POSITION_OR_HOST_FIELDS = frozenset(
    {
        "content_hash",
        "final_ledger_bytes",
        "host_path",
        "ledger_path",
        "ledger_text",
        "output_path",
        "prev_hash",
        "repo_root",
        "sequence",
        "state_root",
    }
)
GitRunner = Callable[[Sequence[str], Path], tuple[int, str, str]]
class BrainAppendRefusal(Exception):
    def __init__(self, invariant: str, detail: str):
        self.invariant = invariant
        self.detail = detail
        super().__init__(f"{invariant}: {detail}")
@dataclass(frozen=True)
class BrainAppendOutcome:
    outcome: str
    evidence_path: Path
    patch_path: Path | None = None
    invariant: str | None = None
class _CaptureWrite:
    text = ""
    def __call__(self, _path: Path, text: str) -> None:
        self.text = text
def _default_git_runner(args: Sequence[str], cwd: Path) -> tuple[int, str, str]:
    try:
        result = subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True, check=False, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, "", str(exc)
    return result.returncode, result.stdout, result.stderr
def _pointer(parts: Sequence[Any]) -> str:
    return "/" + "/".join(str(p).replace("~", "~0").replace("/", "~1") for p in parts) if parts else "/"
def _position_errors(value: Any, path: Path | str, parts: tuple[Any, ...] = ()) -> list[ValidationError]:
    errors: list[ValidationError] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_parts = (*parts, key)
            if str(key) in POSITION_OR_HOST_FIELDS:
                errors.append(
                    make_error(
                        "brain_append_contained_boundary",
                        path,
                        _pointer(child_parts),
                        f"append intent must not carry host/position field {key!r}",
                        CONTRACT,
                    )
                )
            errors.extend(_position_errors(child, path, child_parts))
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            errors.extend(_position_errors(child, path, (*parts, idx)))
    return errors
def validate_intent_doc(data: Any, path: Path | str = "<brain-append-intent>") -> list[ValidationError]:
    if not isinstance(data, dict):
        return [
            make_error(
                "brain_append_intent_schema",
                path,
                "/",
                "brain append intent must be a mapping",
                CONTRACT,
            )
        ]
    return [
        *validate_with_schema(
            data,
            SCHEMA_PATH,
            path,
            code="brain_append_intent_schema",
            contract=CONTRACT,
        ),
        *_position_errors(data, path),
    ]
def load_intent(path: Path | str) -> tuple[Path, dict[str, Any]]:
    source = Path(path)
    try:
        data = yaml.safe_load(source.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise BrainAppendRefusal(
            "brain_append_intent_schema",
            f"could not read or parse intent file: {exc}",
        ) from exc
    errors = validate_intent_doc(data, source)
    if errors:
        raise BrainAppendRefusal(errors[0].code, errors[0].format())
    return source, data
def _refusal_invariant(exc: Exception) -> str:
    if isinstance(exc, brain_runtime.BrainLedgerInvalid) and getattr(exc, "errors", ()):
        return exc.errors[0].code
    detail = str(exc)
    for needle, invariant in {
        "active assertion already exists for scope and claim": "active_assertion_unique",
        "active assertion id already exists": "active_assertion_id_unique",
        "assertion id is not currently active": "supersede_target_active",
        "new assertion id must differ": "supersede_replacement_id_distinct",
        "another active assertion already exists": "active_assertion_unique",
    }.items():
        if needle in detail:
            return invariant
    return "brain_append_runtime_validation"
def _apply_intent(data: dict[str, Any], records: Sequence[dict[str, Any]], repo_root: Path) -> tuple[str, list[dict[str, Any]]]:
    sink = _CaptureWrite()
    try:
        if data["intent_kind"] == "active_assertion_append":
            item = data["active_assertion"]
            brain_runtime.assert_claim(
                claim=item["claim"],
                scope=item["scope"],
                evidence_ref=item["evidence_ref"],
                statement=item.get("statement"),
                assertion_type=item.get("assertion_type"),
                verification_method=item.get("verification_method"),
                assertion_id=item.get("assertion_id"),
                records=records,
                state_root=repo_root / ".ce" / "state",
                write=sink,
            )
        elif data["intent_kind"] == "ce411_supersede_pair":
            pair = data["supersede_pair"]
            item = pair["replacement"]
            brain_runtime.correct_claim(
                assertion_id=pair["assertion_id"],
                claim=item["claim"],
                scope=item.get("scope"),
                evidence_ref=item["evidence_ref"],
                statement=item.get("statement"),
                assertion_type=item.get("assertion_type"),
                verification_method=item.get("verification_method"),
                new_assertion_id=item.get("new_assertion_id") or item.get("assertion_id"),
                records=records,
                state_root=repo_root / ".ce" / "state",
                write=sink,
            )
        else:
            raise BrainAppendRefusal("brain_append_intent_kind", f"unsupported intent_kind {data['intent_kind']!r}")
    except BrainAppendRefusal:
        raise
    except Exception as exc:
        raise BrainAppendRefusal(_refusal_invariant(exc), str(exc)) from exc
    updated = brain_runtime.load_ledger_text(sink.text)
    errors = brain_runtime.validate_records(updated, repo_root / LEDGER_PATH)
    if errors:
        raise BrainAppendRefusal(errors[0].code, errors[0].format())
    return sink.text, updated
def _load_origin_main_ledger(repo_root: Path, base_ref: str, runner: GitRunner) -> tuple[str, list[dict[str, Any]]]:
    code, stdout, stderr = runner(["show", f"{base_ref}:{LEDGER_PATH}"], repo_root)
    if code != 0:
        raise BrainAppendRefusal("origin_main_ledger_materialized", stderr.strip() or "git show failed")
    try:
        return stdout, brain_runtime.load_ledger_text(stdout)
    except brain_runtime.BrainLedgerInvalid as exc:
        raise BrainAppendRefusal(_refusal_invariant(exc), str(exc)) from exc
def _next_intent(queue_dir: Path) -> Path:
    paths = sorted(p for glob in ("*.yaml", "*.yml", "*.json") for p in queue_dir.glob(glob) if p.is_file())
    if not paths:
        raise BrainAppendRefusal("brain_append_queue_non_empty", "durable queue contains no intent file")
    return paths[0]
def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
def _write_refusal(out_dir: Path, intent_name: str, refusal: BrainAppendRefusal) -> BrainAppendOutcome:
    evidence = out_dir / f"{intent_name}.refusal.json"
    _write_json(evidence, {"outcome": "refused", "invariant": refusal.invariant, "detail": refusal.detail})
    return BrainAppendOutcome("refused", evidence, invariant=refusal.invariant)
def run_once(
    *,
    queue_dir: Path | str,
    repo_root: Path | str,
    out_dir: Path | str,
    base_ref: str = "origin/main",
    git_runner: GitRunner | None = None,
) -> BrainAppendOutcome:
    root = Path(repo_root)
    output = Path(out_dir)
    try:
        intent_path = _next_intent(Path(queue_dir))
        intent_path, data = load_intent(intent_path)
        before_text, before_records = _load_origin_main_ledger(root, base_ref, git_runner or _default_git_runner)
        after_text, after_records = _apply_intent(data, before_records, root)
        stem = intent_path.stem
        patch = output / f"{stem}.ledger.patch"
        evidence = output / f"{stem}.mediation-evidence.json"
        output.mkdir(parents=True, exist_ok=True)
        patch.write_text(
            "".join(
                difflib.unified_diff(
                    before_text.splitlines(keepends=True),
                    after_text.splitlines(keepends=True),
                    fromfile=f"{base_ref}:{LEDGER_PATH}",
                    tofile=LEDGER_PATH,
                )
            ),
            encoding="utf-8",
        )
        appended = after_records[len(before_records) :]
        _write_json(
            evidence,
            {
                "outcome": "committed",
                "base_ref": base_ref,
                "intent": intent_path.name,
                "ledger_path": LEDGER_PATH,
                "patch_path": str(patch),
                "record_count_before": len(before_records),
                "record_count_after": len(after_records),
                "appended_sequences": [r["sequence"] for r in appended],
                "appended_prev_hashes": [r["prev_hash"] for r in appended],
                "head_before": before_records[-1].get(brain_runtime.CONTENT_HASH_FIELD) if before_records else None,
                "head_after": after_records[-1].get(brain_runtime.CONTENT_HASH_FIELD) if after_records else None,
            },
        )
        return BrainAppendOutcome("committed", evidence, patch)
    except BrainAppendRefusal as exc:
        name = intent_path.stem if "intent_path" in locals() else "queue"
        return _write_refusal(output, name, exc)

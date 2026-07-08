"""Dry-run materializer for merge-time brain append intents.

Under multi-instance topology this local lease is not a correctness guard; correctness then requires an external linearizable lock with the same brain-append exclusion scope (Q4 ratified ruling).
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

from . import brain_append_worker, brain_runtime, daemon_lease
from .brain_append_worker import BrainAppendRefusal


ARMING_ENABLED = False
ARMING_DISABLED_MESSAGE = "materializer arming is disabled: slice 1 ships dry-run only"
AUTHORIZED_WRITE_PATHS = frozenset(
    {
        ".ce/brain/assertions.yaml",
        ".ce/brain/append-intents/",
    }
)
LEDGER_PATH = ".ce/brain/assertions.yaml"
ACTOR_VERSION = "ce-491-optiona-slice1"
HELD_REASONS = frozenset(
    {
        "brain_intent_materialization_failed",
        "brain_ledger_tail_unprovable",
        "brain_intent_partial_materialization",
    }
)
DRY_RUN_STATUSES = frozenset({"would_materialize", "held"})
MEDIATION_ORDER = (
    "mode",
    "intent_path",
    "intent_sha256",
    "intent_kind",
    "merge_commit_sha",
    "pr_number",
    "branch_slug",
    "materialization_key",
    "materialization_record_index",
    "materialization_record_count",
)

GitRunner = brain_append_worker.GitRunner


class MaterializerConfigError(ValueError):
    """Materializer configuration is missing a required fail-closed field."""


class HeldError(Exception):
    """Materialization must stop and enter HELD state."""

    def __init__(self, reason: str, detail: str | None = None):
        if reason not in HELD_REASONS:
            raise ValueError(f"unknown held reason: {reason}")
        self.reason = reason
        self.detail = detail or reason
        super().__init__(self.detail)


@dataclass(frozen=True)
class MaterializationKey:
    merge_commit_sha: str
    intent_path: str
    intent_sha256: str
    key_hex: str

    @classmethod
    def compute(cls, merge_commit_sha: str, intent_path: str, intent_sha256: str) -> "MaterializationKey":
        material = f"{merge_commit_sha}\n{intent_path}\n{intent_sha256}\n".encode("utf-8")
        return cls(
            merge_commit_sha=merge_commit_sha,
            intent_path=intent_path,
            intent_sha256=intent_sha256,
            key_hex=hashlib.sha256(material).hexdigest(),
        )


@dataclass(frozen=True)
class DiscoveredIntent:
    path: Path
    data: dict[str, Any]
    intent_sha256: str
    materialization_key: MaterializationKey


@dataclass(frozen=True)
class LedgerTail:
    records: list[dict[str, Any]]
    ledger_text: str
    tail_record: dict[str, Any]
    content_hash: str
    main_parent_sha: str


@dataclass(frozen=True)
class RecordBuildResult:
    ledger_text: str
    records: list[dict[str, Any]]
    appended_records: list[dict[str, Any]]
    ledger_tail_before: str
    ledger_tail_after: str
    generated_patch_sha256: str


@dataclass(frozen=True)
class DryRunOutput:
    """Dry-run artifact; materialization-time outcomes are would_materialize or held."""

    mode: str
    status: str
    intent_path: str
    intent_sha256: str | None
    merge_commit_sha: str
    would_append_records: list[dict[str, Any]]
    would_remove_intent_path: str | None
    materialization_key: str
    ledger_tail_before: str | None
    ledger_tail_after: str | None
    refusal_reason: str | None
    generated_patch_sha256: str | None

    def __post_init__(self) -> None:
        if self.mode != "dry_run":
            raise ValueError("DryRunOutput.mode must be dry_run")
        if self.status not in DRY_RUN_STATUSES:
            raise ValueError(f"unsupported dry-run status: {self.status}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def write(self, state_root: Path | str) -> Path:
        path = Path(state_root) / "dry-run" / f"{self.materialization_key}.json"
        _require_state_subtree(path)
        _write_json(path, self.to_dict())
        return path


@dataclass(frozen=True)
class CloseoutStatus:
    is_advisory: bool
    is_hard_failure: bool
    deadline_utc: str
    held_reason: str
    materialization_key: str


@dataclass(frozen=True)
class MaterializerConfig:
    state_root: Path
    quarantine_root: Path
    repo_root: Path
    private_key_env: str
    app_id: int = 4_244_593
    installation_id: int = 145_152_358

    def __post_init__(self) -> None:
        for field in ("state_root", "quarantine_root", "repo_root", "private_key_env"):
            value = getattr(self, field)
            if value in (None, ""):
                raise MaterializerConfigError(f"missing required field: {field}")
        object.__setattr__(self, "state_root", Path(self.state_root))
        object.__setattr__(self, "quarantine_root", Path(self.quarantine_root))
        object.__setattr__(self, "repo_root", Path(self.repo_root))

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "MaterializerConfig":
        missing = [field for field in ("state_root", "quarantine_root", "repo_root", "private_key_env") if not value.get(field)]
        if missing:
            raise MaterializerConfigError(f"missing required field: {missing[0]}")
        return cls(
            state_root=Path(value["state_root"]),
            quarantine_root=Path(value["quarantine_root"]),
            repo_root=Path(value["repo_root"]),
            private_key_env=str(value["private_key_env"]),
            app_id=int(value.get("app_id", 4_244_593)),
            installation_id=int(value.get("installation_id", 145_152_358)),
        )


class _NoAliasSafeDumper(yaml.SafeDumper):
    def ignore_aliases(self, data: Any) -> bool:  # type: ignore[override]
        return True


def assert_arming_enabled() -> None:
    if not ARMING_ENABLED:
        raise RuntimeError(ARMING_DISABLED_MESSAGE)


def _assert_armed_write_target(path: Path | str) -> None:
    """Enforce the Operator-bounded armed write surface before any write attempt."""
    rendered = str(path).replace("\\", "/")
    for authorized in AUTHORIZED_WRITE_PATHS:
        if authorized.endswith("/"):
            if rendered.startswith(authorized):
                return
        elif rendered == authorized:
            return
    raise RuntimeError(f"materializer armed write target is outside authorized paths: {path}")


def construct_materialization_commit(*_args: Any, write_paths: Sequence[Path | str] | None = None, **_kwargs: Any) -> None:
    for target in write_paths or (LEDGER_PATH, ".ce/brain/append-intents/"):
        _assert_armed_write_target(target)
    assert_arming_enabled()


def _utc_now(now: Callable[[], datetime] | None = None) -> datetime:
    value = now() if now is not None else datetime.now(UTC)
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _rfc3339_z(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _require_state_subtree(path: Path) -> None:
    parts = path.parts
    for index, part in enumerate(parts[:-1]):
        # The prior index-bound check was always true here: iterating parts[:-1]
        # guarantees one following part whenever ".ce" is visited.
        if part == ".ce" and parts[index + 1] == "state":
            return
    raise RuntimeError(f"materializer evidence path escapes .ce/state: {path}")


def _parse_utc_z_naive(value: Any) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("held_at_utc must be a non-empty ISO-8601 string")
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(UTC).replace(tzinfo=None)
    return parsed


def _now_naive_utc(now_fn: Callable[[], datetime] | None) -> datetime:
    value = now_fn() if now_fn is not None else datetime.utcnow()
    if value.tzinfo is not None:
        value = value.astimezone(UTC).replace(tzinfo=None)
    return value


def _iso_utc_z_naive(value: datetime) -> str:
    if value.tzinfo is not None:
        value = value.astimezone(UTC).replace(tzinfo=None)
    return value.isoformat(timespec="seconds") + "Z"


def _canonical_intent_sha256(path: Path | str) -> str:
    text = Path(path).read_text(encoding="utf-8")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _safe_intent_sha256(path: Path | str) -> str:
    try:
        return _canonical_intent_sha256(path)
    except OSError:
        return hashlib.sha256(b"").hexdigest()
    except UnicodeDecodeError:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _position_field_present(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key) in brain_append_worker.POSITION_OR_HOST_FIELDS or str(key) in {"prev_hash", "content_hash"}:
                return str(key)
            found = _position_field_present(child)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _position_field_present(child)
            if found is not None:
                return found
    return None


class IntentDiscovery:
    def discover(
        self,
        *,
        merge_commit_sha: str,
        intent_path: Path | str,
        branch_slug: str,
    ) -> DiscoveredIntent:
        source, data = brain_append_worker.load_intent(intent_path)
        if source.stem != branch_slug:
            raise BrainAppendRefusal(
                "brain_append_intent_path_binding",
                f"intent path stem {source.stem!r} does not match branch_slug {branch_slug!r}",
            )
        position_field = _position_field_present(data)
        if position_field is not None:
            raise BrainAppendRefusal(
                "brain_append_contained_boundary",
                f"append intent must not carry host/position field {position_field!r}",
            )
        intent_sha256 = _canonical_intent_sha256(source)
        key = MaterializationKey.compute(merge_commit_sha, str(intent_path), intent_sha256)
        return DiscoveredIntent(source, data, intent_sha256, key)


class HistoryScanner:
    """Discovers unconsumed append intents by walking origin/main first-parent history."""

    INTENT_ROOT = ".ce/brain/append-intents/"

    def __init__(
        self,
        repo_root: Path | str,
        *,
        git_runner: GitRunner | None = None,
        main_ref: str = "origin/main",
    ):
        self.repo_root = Path(repo_root)
        self.git_runner = git_runner or brain_append_worker._default_git_runner
        self.main_ref = main_ref

    def _git(self, args: Sequence[str]) -> str:
        code, stdout, stderr = self.git_runner(args, self.repo_root)
        if code != 0:
            detail = stderr.strip() or stdout.strip() or f"git {' '.join(args)} failed"
            raise RuntimeError(detail)
        return stdout

    def _intent_paths_at(self, git_ref: str) -> list[str]:
        stdout = self._git(["ls-tree", "-r", "--name-only", git_ref, self.INTENT_ROOT])
        return sorted(line.strip() for line in stdout.splitlines() if line.strip())

    def scan(self) -> list[tuple[str, str]]:
        log = self._git(["log", "--first-parent", "--format=%H", self.main_ref])
        newest_first = [line.strip() for line in log.splitlines() if line.strip()]
        if not newest_first:
            return []

        pending_current = set(self._intent_paths_at(self.main_ref))
        if not pending_current:
            return []

        discovered: list[tuple[str, str]] = []
        seen_paths: set[str] = set()
        for sha in reversed(newest_first):
            for intent_path in self._intent_paths_at(sha):
                if intent_path in pending_current and intent_path not in seen_paths:
                    discovered.append((sha, intent_path))
                    seen_paths.add(intent_path)
        return discovered

    def __iter__(self):
        return iter(self.scan())


class CloseoutWindowPolicy:
    """Evaluates HELD closeout status; gate registration is deferred until arming scope."""

    WINDOW = timedelta(minutes=30)

    @classmethod
    def evaluate(
        cls,
        held_record: dict[str, Any],
        now_fn: Callable[[], datetime] | None = None,
    ) -> CloseoutStatus:
        held_at = _parse_utc_z_naive(held_record.get("held_at_utc"))
        deadline = held_at + cls.WINDOW
        now = _now_naive_utc(now_fn)
        is_hard_failure = now >= deadline
        return CloseoutStatus(
            is_advisory=not is_hard_failure,
            is_hard_failure=is_hard_failure,
            deadline_utc=_iso_utc_z_naive(deadline),
            held_reason=str(held_record.get("held_reason", "")),
            materialization_key=str(held_record.get("materialization_key", "")),
        )


class LedgerTailProof:
    def __init__(self, git_runner: GitRunner | None = None):
        self.git_runner = git_runner or brain_append_worker._default_git_runner

    def prove(self, *, repo_root: Path | str, git_ref: str = "main") -> LedgerTail:
        root = Path(repo_root)
        code, stdout, stderr = self.git_runner(["rev-parse", git_ref], root)
        if code != 0:
            raise HeldError("brain_ledger_tail_unprovable", stderr.strip() or f"could not resolve {git_ref}")
        main_parent_sha = stdout.strip()
        if not main_parent_sha:
            raise HeldError("brain_ledger_tail_unprovable", f"empty git ref resolution for {git_ref}")
        code, ledger_text, stderr = self.git_runner(["show", f"{main_parent_sha}:{LEDGER_PATH}"], root)
        if code != 0:
            raise HeldError("brain_ledger_tail_unprovable", stderr.strip() or "git show failed")
        try:
            records = brain_runtime.load_ledger_text(ledger_text)
        except (brain_runtime.BrainLedgerInvalid, yaml.YAMLError) as exc:
            raise HeldError("brain_ledger_tail_unprovable", str(exc)) from exc
        if not records:
            raise HeldError("brain_ledger_tail_unprovable", "current ledger tail could not be proven")
        tail = records[-1]
        content_hash = tail.get(brain_runtime.CONTENT_HASH_FIELD)
        if not isinstance(content_hash, str) or len(content_hash) != 64:
            raise HeldError("brain_ledger_tail_unprovable", "current ledger tail could not be proven")
        return LedgerTail(records=records, ledger_text=ledger_text, tail_record=tail, content_hash=content_hash, main_parent_sha=main_parent_sha)


def _mediation_block(
    *,
    intent_path: str,
    intent_sha256: str,
    intent_kind: str,
    merge_commit_sha: str,
    pr_number: int,
    branch_slug: str,
    materialization_key: str,
    index: int,
    count: int,
) -> dict[str, Any]:
    values = {
        "mode": "merge_time_intent",
        "intent_path": intent_path,
        "intent_sha256": intent_sha256,
        "intent_kind": intent_kind,
        "merge_commit_sha": merge_commit_sha,
        "pr_number": pr_number,
        "branch_slug": branch_slug,
        "materialization_key": materialization_key,
        "materialization_record_index": index,
        "materialization_record_count": count,
    }
    return {key: values[key] for key in MEDIATION_ORDER}


def _body_with_mediation(record: Mapping[str, Any], mediation: Mapping[str, Any]) -> dict[str, Any]:
    body: dict[str, Any] = {}
    for key, value in record.items():
        if key in {"sequence", "prev_hash", brain_runtime.CONTENT_HASH_FIELD}:
            continue
        body[key] = copy.deepcopy(value)
    body["mediation"] = dict(mediation)
    return body


def _serialize_ledger(records: Sequence[dict[str, Any]]) -> str:
    doc = {
        "kind": brain_runtime.LEDGER_KIND,
        "record_type": brain_runtime.LEDGER_RECORD_TYPE,
        "schema_version": brain_runtime.SCHEMA_VERSION,
        "records": [copy.deepcopy(record) for record in records],
    }
    return yaml.dump(
        doc,
        Dumper=_NoAliasSafeDumper,
        sort_keys=False,
        allow_unicode=False,
        default_flow_style=False,
    )


class RecordBuilder:
    """Builds deterministic dry-run ledger bytes; same inputs must produce identical bytes."""

    def build(
        self,
        *,
        intent_data: dict[str, Any],
        live_records: Sequence[dict[str, Any]],
        live_tail_content_hash: str,
        repo_root: Path | str,
        merge_commit_sha: str,
        pr_number: int,
        branch_slug: str,
        intent_path: str,
        intent_sha256: str,
        materialization_key: str,
    ) -> RecordBuildResult:
        if live_records and live_records[-1].get(brain_runtime.CONTENT_HASH_FIELD) != live_tail_content_hash:
            raise HeldError("brain_ledger_tail_unprovable", "live tail content_hash does not match proof")
        _text, normalized_records = brain_append_worker._apply_intent(intent_data, live_records, Path(repo_root))
        normalized_appended = normalized_records[len(live_records) :]
        rebuilt_records = [copy.deepcopy(record) for record in live_records]
        appended: list[dict[str, Any]] = []
        count = len(normalized_appended)
        for index, record in enumerate(normalized_appended):
            mediation = _mediation_block(
                intent_path=intent_path,
                intent_sha256=intent_sha256,
                intent_kind=str(intent_data["intent_kind"]),
                merge_commit_sha=merge_commit_sha,
                pr_number=pr_number,
                branch_slug=branch_slug,
                materialization_key=materialization_key,
                index=index,
                count=count,
            )
            body = _body_with_mediation(record, mediation)
            rebuilt = brain_runtime._append_record(rebuilt_records, body)
            rebuilt_records.append(rebuilt)
            appended.append(rebuilt)
        ledger_text = _serialize_ledger(rebuilt_records)
        return RecordBuildResult(
            ledger_text=ledger_text,
            records=rebuilt_records,
            appended_records=appended,
            ledger_tail_before=live_tail_content_hash,
            ledger_tail_after=str(rebuilt_records[-1][brain_runtime.CONTENT_HASH_FIELD]),
            generated_patch_sha256=hashlib.sha256(ledger_text.encode("utf-8")).hexdigest(),
        )


class QuarantineWriter:
    def __init__(self, root: Path | str, *, now: Callable[[], datetime] | None = None):
        self.root = Path(root)
        self.now = now

    def write(
        self,
        *,
        materialization_key: str,
        intent_path: str,
        intent_sha256: str | None,
        merge_commit_sha: str,
        validation_error: str,
    ) -> Path:
        path = self.root / f"{materialization_key}.json"
        _require_state_subtree(path)
        _write_json(
            path,
            {
                "intent_path": intent_path,
                "intent_sha256": intent_sha256,
                "merge_commit_sha": merge_commit_sha,
                "validation_error": validation_error,
                "actor_version": ACTOR_VERSION,
                "timestamp": _rfc3339_z(_utc_now(self.now)),
            },
        )
        return path


class HeldStateStore:
    def __init__(self, state_root: Path | str, *, now: Callable[[], datetime] | None = None):
        self.root = Path(state_root) / "held"
        self.now = now

    def write(
        self,
        *,
        held_reason: str,
        materialization_key: str,
        intent_path: str,
        intent_sha256: str | None,
        merge_commit_sha: str,
    ) -> Path:
        if held_reason not in HELD_REASONS:
            raise ValueError(f"unknown held reason: {held_reason}")
        path = self.root / f"{materialization_key}.json"
        _require_state_subtree(path)
        _write_json(
            path,
            {
                "held_reason": held_reason,
                "materialization_key": materialization_key,
                "intent_path": intent_path,
                "intent_sha256": intent_sha256,
                "merge_commit_sha": merge_commit_sha,
                "held_at_utc": _rfc3339_z(_utc_now(self.now)),
            },
        )
        return path

    def load(self, materialization_key: str) -> dict[str, Any]:
        path = self.root / f"{materialization_key}.json"
        return json.loads(path.read_text(encoding="utf-8"))


class MaterializerLease:
    """Local singleton lease wrapper for the brain-append exclusion scope."""

    def __init__(
        self,
        state_root: Path | str,
        *,
        holder_id: str = "brain-intent-materializer",
        acquire_func: Callable[..., daemon_lease.DaemonLease] = daemon_lease.acquire,
    ):
        self.lease_root = Path(state_root) / "leases"
        self.holder_id = holder_id
        self.acquire_func = acquire_func
        self._lease: daemon_lease.DaemonLease | None = None

    def acquire(self) -> "MaterializerLease":
        self.lease_root.mkdir(parents=True, exist_ok=True)
        self._lease = self.acquire_func("brain-append", self.holder_id, state_root=self.lease_root)
        return self

    def release(self) -> None:
        if self._lease is not None:
            self._lease.release()
            self._lease = None

    def __enter__(self) -> "MaterializerLease":
        return self.acquire()

    def __exit__(self, _exc_type: Any, _exc: Any, _tb: Any) -> None:
        self.release()


class MaterializerRunLoop:
    """Run one materializer poll/process cycle.

    Under multi-instance topology, multiple run-loop invocations against the same repo state would produce competing leases; correctness requires an external linearizable lock with the same brain-append exclusion scope (Q4 ratified ruling).
    """

    def __init__(
        self,
        config: MaterializerConfig,
        *,
        poll_source: Callable[[], list[tuple[str, str]]] | None = None,
        git_runner: GitRunner | None = None,
        pr_number: int = 0,
        now: Callable[[], datetime] | None = None,
    ):
        if not isinstance(config, MaterializerConfig):
            raise MaterializerConfigError("config must be a MaterializerConfig")
        self.config = config
        self.poll_source = poll_source
        self.git_runner = git_runner
        self.pr_number = pr_number
        self.now = now

    def _default_poll_source(self) -> list[tuple[str, str]]:
        return HistoryScanner(self.config.repo_root, git_runner=self.git_runner).scan()

    def run_once(self, *, pr_number: int | None = None) -> list[DryRunOutput]:
        source = self.poll_source or self._default_poll_source
        outputs: list[DryRunOutput] = []
        for merge_commit_sha, intent_path in source():
            path = Path(intent_path)
            outputs.append(
                Materializer.run_dry(
                    merge_commit_sha=merge_commit_sha,
                    intent_path=intent_path,
                    branch_slug=path.stem,
                    pr_number=self.pr_number if pr_number is None else pr_number,
                    config=self.config,
                    git_runner=self.git_runner,
                    now=self.now,
                )
            )
        return outputs


def _append_event(
    *,
    state_root: Path,
    materialization_key: str,
    intent_sha256: str | None,
    merge_commit_sha: str,
    main_parent_sha: str | None,
    result_status: str,
    now: Callable[[], datetime] | None = None,
) -> Path:
    path = state_root / "materializer.jsonl"
    _require_state_subtree(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "started_at": _rfc3339_z(_utc_now(now)),
        "materialization_key": materialization_key,
        "intent_sha256": intent_sha256,
        "merge_commit_sha": merge_commit_sha,
        "main_parent_sha": main_parent_sha,
        "result_status": result_status,
    }
    digest_material = json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    event["event_sha256"] = hashlib.sha256(digest_material).hexdigest()
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")
    return path


def event_sha256_for_line(line: str) -> str:
    event = json.loads(line)
    event.pop("event_sha256", None)
    material = json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


class Materializer:
    @staticmethod
    def run_dry(
        *,
        merge_commit_sha: str,
        intent_path: Path | str,
        branch_slug: str,
        pr_number: int,
        config: MaterializerConfig,
        git_ref: str = "main",
        git_runner: GitRunner | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> DryRunOutput:
        if not isinstance(config, MaterializerConfig):
            raise MaterializerConfigError("config must be a MaterializerConfig")
        fallback_sha = _safe_intent_sha256(intent_path)
        fallback_key = MaterializationKey.compute(merge_commit_sha, str(intent_path), fallback_sha)
        main_parent_sha: str | None = None
        with MaterializerLease(config.state_root):
            try:
                discovered = IntentDiscovery().discover(
                    merge_commit_sha=merge_commit_sha,
                    intent_path=intent_path,
                    branch_slug=branch_slug,
                )
                tail = LedgerTailProof(git_runner).prove(repo_root=config.repo_root, git_ref=git_ref)
                main_parent_sha = tail.main_parent_sha
                built = RecordBuilder().build(
                    intent_data=discovered.data,
                    live_records=tail.records,
                    live_tail_content_hash=tail.content_hash,
                    repo_root=config.repo_root,
                    merge_commit_sha=merge_commit_sha,
                    pr_number=pr_number,
                    branch_slug=branch_slug,
                    intent_path=str(intent_path),
                    intent_sha256=discovered.intent_sha256,
                    materialization_key=discovered.materialization_key.key_hex,
                )
                output = DryRunOutput(
                    mode="dry_run",
                    status="would_materialize",
                    intent_path=str(intent_path),
                    intent_sha256=discovered.intent_sha256,
                    merge_commit_sha=merge_commit_sha,
                    would_append_records=built.appended_records,
                    would_remove_intent_path=str(intent_path),
                    materialization_key=discovered.materialization_key.key_hex,
                    ledger_tail_before=built.ledger_tail_before,
                    ledger_tail_after=built.ledger_tail_after,
                    refusal_reason=None,
                    generated_patch_sha256=built.generated_patch_sha256,
                )
                output.write(config.state_root)
                _append_event(
                    state_root=config.state_root,
                    materialization_key=output.materialization_key,
                    intent_sha256=output.intent_sha256,
                    merge_commit_sha=merge_commit_sha,
                    main_parent_sha=main_parent_sha,
                    result_status=output.status,
                    now=now,
                )
                return output
            except BrainAppendRefusal as exc:
                # Artifact asymmetry: BrainAppendRefusal writes quarantine,
                # HELD state, dry-run artifact, and JSONL event; HeldError
                # writes HELD state and JSONL event only.
                key = fallback_key
                reason = "brain_intent_materialization_failed"
                detail = f"{exc.invariant}: {exc.detail}"
                QuarantineWriter(config.quarantine_root, now=now).write(
                    materialization_key=key.key_hex,
                    intent_path=str(intent_path),
                    intent_sha256=fallback_sha,
                    merge_commit_sha=merge_commit_sha,
                    validation_error=detail,
                )
                HeldStateStore(config.state_root, now=now).write(
                    held_reason=reason,
                    materialization_key=key.key_hex,
                    intent_path=str(intent_path),
                    intent_sha256=fallback_sha,
                    merge_commit_sha=merge_commit_sha,
                )
                output = DryRunOutput(
                    mode="dry_run",
                    status="held",
                    intent_path=str(intent_path),
                    intent_sha256=fallback_sha,
                    merge_commit_sha=merge_commit_sha,
                    would_append_records=[],
                    would_remove_intent_path=None,
                    materialization_key=key.key_hex,
                    ledger_tail_before=None,
                    ledger_tail_after=None,
                    refusal_reason=detail,
                    generated_patch_sha256=None,
                )
                output.write(config.state_root)
                _append_event(
                    state_root=config.state_root,
                    materialization_key=key.key_hex,
                    intent_sha256=fallback_sha,
                    merge_commit_sha=merge_commit_sha,
                    main_parent_sha=main_parent_sha,
                    result_status=output.status,
                    now=now,
                )
                return output
            except HeldError as exc:
                key = fallback_key
                HeldStateStore(config.state_root, now=now).write(
                    held_reason=exc.reason,
                    materialization_key=key.key_hex,
                    intent_path=str(intent_path),
                    intent_sha256=fallback_sha,
                    merge_commit_sha=merge_commit_sha,
                )
                output = DryRunOutput(
                    mode="dry_run",
                    status="held",
                    intent_path=str(intent_path),
                    intent_sha256=fallback_sha,
                    merge_commit_sha=merge_commit_sha,
                    would_append_records=[],
                    would_remove_intent_path=None,
                    materialization_key=key.key_hex,
                    ledger_tail_before=None,
                    ledger_tail_after=None,
                    refusal_reason=exc.reason,
                    generated_patch_sha256=None,
                )
                _append_event(
                    state_root=config.state_root,
                    materialization_key=key.key_hex,
                    intent_sha256=fallback_sha,
                    merge_commit_sha=merge_commit_sha,
                    main_parent_sha=main_parent_sha,
                    result_status=output.status,
                    now=now,
                )
                return output

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import socket
import stat
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import Iterable


_VALIDATORS_ROOT = Path(__file__).resolve().parents[2] / "validators"
if _VALIDATORS_ROOT.is_dir() and str(_VALIDATORS_ROOT) not in sys.path:
    sys.path.insert(0, str(_VALIDATORS_ROOT))

from creator_engine_validator.secret_paths import is_secret_path  # noqa: E402


DEFAULT_OUTPUT_DIR = Path("./ce-controller-snapshot")
DENYLIST_SUFFIXES = {".pat", ".pem", ".pass", ".key", ".p8", ".pfx", ".pkcs12"}
DENYLIST_NAME_FRAGMENTS = {"_token", "secret", "password", "credentials"}
DENYLIST_PATH_SEGMENTS = {".ce-keys", "ce-keys"}

SNAPSHOT_SOURCES = (
    ("arc_state", Path(".ce/state/research"), Path("arc_state")),
    ("dispatch_briefs", Path(".ce/briefs"), Path("dispatch_briefs")),
    ("dispatch_claims", Path(".ce/claims"), Path("dispatch_claims")),
)


class SnapshotError(RuntimeError):
    """The snapshot cannot be published without weakening its guarantees."""


def find_source_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    raise RuntimeError("could not auto-detect source root: no .git found")


def _hash_regular_file(path: Path) -> tuple[int, str]:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise SnapshotError(f"refused unreadable or symlinked source file: {path}") from exc

    digest = hashlib.sha256()
    with os.fdopen(descriptor, "rb") as handle:
        before = os.fstat(handle.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise SnapshotError(f"refused non-regular source file: {path}")
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
        after = os.fstat(handle.fileno())

    identity_before = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    identity_after = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    if identity_before != identity_after:
        raise SnapshotError(f"source changed while it was being hashed: {path}")
    return after.st_size, digest.hexdigest()


def sha256_file(path: Path) -> str:
    return _hash_regular_file(path)[1]


def relative_posix(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def is_denied_path(path: Path, root: Path | None = None) -> bool:
    candidate = path
    if root is not None:
        try:
            candidate = path.relative_to(root)
        except ValueError:
            candidate = path

    if is_secret_path(candidate.as_posix()) is not None:
        return True

    parts = candidate.parts
    lowered_parts = [part.lower() for part in parts]
    if any(part in DENYLIST_PATH_SEGMENTS for part in lowered_parts):
        return True

    name = path.name.lower()
    if any(fragment in name for fragment in DENYLIST_NAME_FRAGMENTS):
        return True

    return path.suffix.lower() in DENYLIST_SUFFIXES


def iter_entries(root: Path) -> Iterable[Path]:
    """Yield files and symlinks lexically below root without following links."""
    if root.is_symlink():
        yield root
        return
    if not root.exists():
        return

    for current, directory_names, file_names in os.walk(root, followlinks=False):
        directory_names.sort()
        file_names.sort()
        current_path = Path(current)

        for directory_name in list(directory_names):
            path = current_path / directory_name
            if directory_name == ".git":
                directory_names.remove(directory_name)
            elif path.is_symlink():
                directory_names.remove(directory_name)
                yield path

        for file_name in file_names:
            yield current_path / file_name


def iter_files(root: Path) -> Iterable[Path]:
    for path in iter_entries(root):
        if not path.is_symlink() and stat.S_ISREG(path.stat(follow_symlinks=False).st_mode):
            yield path


def _file_record(path: Path, source_root: Path, rel_path: str | None = None) -> dict[str, object]:
    size, digest = _hash_regular_file(path)
    return {
        "path": rel_path or relative_posix(path, source_root),
        "size": size,
        "sha256": digest,
    }


def default_memory_root(repo_root: Path, *, home: Path | None = None) -> Path:
    resolved_repo = repo_root.expanduser().resolve()
    project_slug = resolved_repo.as_posix().replace("/", "-")
    return (home or Path.home()) / ".claude" / "projects" / project_slug / "memory"


def restore_steps(target_branch: str) -> list[str]:
    return [
        "1. Clone or fetch the target repo to the replacement host.",
        f"2. Check out branch {target_branch}.",
        "3. Copy arc_state/ to <replacement-repo-root>/.ce/state/research/.",
        "4. Copy dispatch_briefs/ to <replacement-repo-root>/.ce/briefs/.",
        "5. Copy dispatch_claims/ to <replacement-repo-root>/.ce/claims/.",
        "6. If memory archive is present: tar -xf memory.tar.gz -C <replacement-memory-root>/.",
    ]


def collect_manifest(
    source_root: Path,
    *,
    include_memory: bool = False,
    memory_root: Path | None = None,
    target_branch: str | None = None,
) -> dict[str, object]:
    source_root = source_root.resolve()
    memory_root_source = "override" if memory_root is not None else "derived-from-repo-root"
    memory_root = (
        memory_root.expanduser().resolve()
        if memory_root is not None
        else default_memory_root(source_root).resolve()
    )
    target_branch = target_branch or f"ce-controller-state/{socket.gethostname()}"

    files: list[dict[str, object]] = []
    denied_paths: set[str] = set()
    missing_sources: list[str] = []

    for path in iter_entries(source_root):
        if is_denied_path(path, source_root):
            denied_paths.add(relative_posix(path, source_root))

    for missing_name, relative_source, _output_relative in SNAPSHOT_SOURCES:
        source = source_root / relative_source
        if not source.exists():
            print(f"warning: missing source for {missing_name}: {source}", file=sys.stderr)
            missing_sources.append(missing_name)
            continue

        for path in iter_entries(source):
            rel_path = relative_posix(path, source_root)
            if path.is_symlink() or is_denied_path(path, source_root):
                denied_paths.add(rel_path)
                continue
            if not stat.S_ISREG(path.stat(follow_symlinks=False).st_mode):
                denied_paths.add(rel_path)
                continue
            files.append(_file_record(path, source_root, rel_path))

    data_classes = ["arc_state", "dispatch_state"]
    if include_memory:
        data_classes.append("memory")
        if not memory_root.exists():
            print(f"warning: missing source for memory: {memory_root}", file=sys.stderr)
            missing_sources.append("memory")
        else:
            for path in iter_entries(memory_root):
                memory_rel = relative_posix(path, memory_root)
                manifest_path = f"memory/{memory_rel}"
                if path.is_symlink() or is_denied_path(path, memory_root):
                    denied_paths.add(manifest_path)
                    continue
                if not stat.S_ISREG(path.stat(follow_symlinks=False).st_mode):
                    denied_paths.add(manifest_path)
                    continue
                files.append(_file_record(path, memory_root, manifest_path))

    manifest: dict[str, object] = {
        "schema_version": "1",
        "snapshot_at": dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat(),
        "source_host": socket.gethostname(),
        "source_root": str(source_root),
        "memory_root": str(memory_root),
        "memory_root_source": memory_root_source,
        "target_branch": target_branch,
        "data_classes": data_classes,
        "files": sorted(files, key=lambda item: str(item["path"])),
        "denied_paths": sorted(denied_paths),
        "restore_instructions": "See RESTORE section below.",
        "restore_steps": restore_steps(target_branch),
    }
    if missing_sources:
        manifest["missing_sources"] = sorted(set(missing_sources))
    return manifest


def _manifest_source_and_destination(
    manifest_path: str,
    source_root: Path,
    memory_root: Path,
) -> tuple[Path, Path | None]:
    relative = Path(manifest_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise SnapshotError(f"invalid path in manifest: {manifest_path}")

    if relative.parts and relative.parts[0] == "memory":
        memory_relative = Path(*relative.parts[1:])
        return memory_root / memory_relative, None

    for _name, relative_source, output_relative in SNAPSHOT_SOURCES:
        try:
            payload_relative = relative.relative_to(relative_source)
        except ValueError:
            continue
        return source_root / relative, output_relative / payload_relative
    raise SnapshotError(f"manifest path is outside snapshot sources: {manifest_path}")


def _copy_verified(source: Path, destination: Path, record: dict[str, object]) -> None:
    expected_size = int(record["size"])
    expected_digest = str(record["sha256"])
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(source, flags)
    except OSError as exc:
        raise SnapshotError(f"source disappeared or became a symlink: {source}") from exc

    destination.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    copied_size = 0
    with os.fdopen(descriptor, "rb") as source_handle, destination.open("xb") as output_handle:
        before = os.fstat(source_handle.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise SnapshotError(f"refused non-regular source file: {source}")
        for chunk in iter(lambda: source_handle.read(1024 * 1024), b""):
            output_handle.write(chunk)
            digest.update(chunk)
            copied_size += len(chunk)
        after = os.fstat(source_handle.fileno())

    identity_before = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    identity_after = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    if identity_before != identity_after:
        raise SnapshotError(f"source changed during publication: {source}")
    if copied_size != expected_size or digest.hexdigest() != expected_digest:
        raise SnapshotError(f"source changed between collection and publication: {source}")


def write_snapshot(
    manifest: dict[str, object],
    output_dir: Path,
    source_root: Path,
    *,
    include_memory: bool = False,
    memory_root: Path | None = None,
) -> None:
    output_dir = output_dir.expanduser().absolute()
    source_root = source_root.resolve()
    memory_root = (
        memory_root.expanduser().resolve()
        if memory_root is not None
        else default_memory_root(source_root).resolve()
    )

    if output_dir.is_symlink():
        raise SnapshotError(f"refused symlink output directory: {output_dir}")
    if output_dir.exists():
        if not output_dir.is_dir() or any(output_dir.iterdir()):
            raise SnapshotError(f"refused non-empty output directory: {output_dir}")

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging_dir = Path(
        tempfile.mkdtemp(prefix=f".{output_dir.name}.staging-", dir=output_dir.parent)
    )
    memory_staging = staging_dir / ".memory-staging"

    try:
        records = manifest.get("files")
        if not isinstance(records, list):
            raise SnapshotError("manifest.files must be a list")

        memory_records: list[tuple[dict[str, object], Path]] = []
        for record in records:
            if not isinstance(record, dict) or not isinstance(record.get("path"), str):
                raise SnapshotError("manifest contains an invalid file record")
            source, payload_relative = _manifest_source_and_destination(
                str(record["path"]), source_root, memory_root
            )
            if payload_relative is None:
                memory_relative = Path(*Path(str(record["path"])).parts[1:])
                _copy_verified(source, memory_staging / memory_relative, record)
                memory_records.append((record, memory_relative))
            else:
                _copy_verified(source, staging_dir / payload_relative, record)

        if memory_records:
            if not include_memory:
                raise SnapshotError("manifest contains memory files but memory inclusion is disabled")
            with tarfile.open(staging_dir / "memory.tar.gz", "w:gz") as archive:
                for _record, memory_relative in memory_records:
                    archive.add(memory_staging / memory_relative, arcname=memory_relative)
            shutil.rmtree(memory_staging)
        elif include_memory and "memory" in manifest.get("data_classes", []):
            # An included-but-empty memory source has no archive payload to restore.
            pass

        (staging_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        if output_dir.exists():
            if output_dir.is_symlink() or not output_dir.is_dir() or any(output_dir.iterdir()):
                raise SnapshotError(f"output directory changed during publication: {output_dir}")
            output_dir.rmdir()
        os.replace(staging_dir, output_dir)
    except Exception:
        if staging_dir.exists():
            shutil.rmtree(staging_dir)
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Snapshot governed controller state.")
    parser.add_argument("--dry-run", action="store_true", help="print manifest and write nothing")
    parser.add_argument("--commit", action="store_true", help="write snapshot tree to --output-dir")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="destination root for the snapshot tree",
    )
    parser.add_argument(
        "--repo-root",
        "--source-root",
        dest="repo_root",
        type=Path,
        help="repo working tree root to collect from",
    )
    parser.add_argument(
        "--memory-root",
        type=Path,
        help="override the controller memory directory derived from --repo-root",
    )
    parser.add_argument(
        "--include-memory",
        action="store_true",
        help="include controller memory as a tar archive",
    )
    parser.add_argument(
        "--manifest-only",
        action="store_true",
        help="compute and print manifest JSON without copying files",
    )
    parser.add_argument(
        "--target-branch",
        default=f"ce-controller-state/{socket.gethostname()}",
        help="label written into manifest.target_branch",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        source_root = args.repo_root.resolve() if args.repo_root else find_source_root()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    manifest = collect_manifest(
        source_root,
        include_memory=args.include_memory,
        memory_root=args.memory_root,
        target_branch=args.target_branch,
    )

    should_write = args.commit and not args.dry_run and not args.manifest_only
    if should_write:
        try:
            write_snapshot(
                manifest,
                args.output_dir,
                source_root,
                include_memory=args.include_memory,
                memory_root=args.memory_root,
            )
        except (OSError, SnapshotError) as exc:
            print(f"snapshot refused: {exc}", file=sys.stderr)
            return 1
    else:
        if args.output_dir != DEFAULT_OUTPUT_DIR:
            print(f"[DRY-RUN] Would write to {args.output_dir}", file=sys.stderr)
        print(json.dumps(manifest, indent=2, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

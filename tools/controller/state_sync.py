#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import shutil
import socket
import sys
import tarfile
from pathlib import Path
from typing import Iterable


DEFAULT_OUTPUT_DIR = Path("./ce-controller-snapshot")
DEFAULT_MEMORY_ROOT = Path(
    "~/.claude/projects/-home-cedev2-creator-engine/memory/"
).expanduser()
DENYLIST_SUFFIXES = {".pat", ".pem", ".pass", ".key", ".p8", ".pfx", ".pkcs12"}
DENYLIST_NAME_FRAGMENTS = {"_token", "secret", "password", "credentials"}
DENYLIST_PATH_SEGMENTS = {".ce-keys", "ce-keys"}

SNAPSHOT_SOURCES = (
    ("arc_state", Path(".ce/state/research"), Path("arc_state")),
    ("dispatch_briefs", Path(".ce/briefs"), Path("dispatch_briefs")),
    ("dispatch_claims", Path(".ce/claims"), Path("dispatch_claims")),
)


def find_source_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    raise RuntimeError("could not auto-detect source root: no .git found")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative_posix(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def is_denied_path(path: Path, root: Path | None = None) -> bool:
    parts = path.parts
    if root is not None:
        try:
            parts = path.resolve().relative_to(root.resolve()).parts
        except ValueError:
            parts = path.parts

    lowered_parts = [part.lower() for part in parts]
    if any(part in DENYLIST_PATH_SEGMENTS for part in lowered_parts):
        return True

    name = path.name.lower()
    if any(fragment in name for fragment in DENYLIST_NAME_FRAGMENTS):
        return True

    return path.suffix.lower() in DENYLIST_SUFFIXES


def iter_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        return
    for path in sorted(root.rglob("*")):
        if ".git" in path.parts:
            continue
        if path.is_file():
            yield path


def _file_record(path: Path, source_root: Path, rel_path: str | None = None) -> dict[str, object]:
    return {
        "path": rel_path or relative_posix(path, source_root),
        "size": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def restore_steps(target_branch: str) -> list[str]:
    return [
        "1. Clone or fetch the target repo to the replacement host.",
        f"2. Check out branch {target_branch}.",
        "3. Copy arc_state/ to {replacement_repo_root}/.ce/state/research/.",
        "4. Copy dispatch_briefs/ to {replacement_repo_root}/.ce/briefs/.",
        "5. Copy dispatch_claims/ to {replacement_repo_root}/.ce/claims/.",
        "6. If memory archive present: tar -xf memory.tar.gz -C ~/.claude/projects/-home-cedev2-creator-engine/memory/.",
    ]


def collect_manifest(
    source_root: Path,
    *,
    include_memory: bool = False,
    memory_root: Path = DEFAULT_MEMORY_ROOT,
    target_branch: str | None = None,
) -> dict[str, object]:
    source_root = source_root.resolve()
    memory_root = memory_root.expanduser().resolve()
    target_branch = target_branch or f"ce-controller-state/{socket.gethostname()}"

    files: list[dict[str, object]] = []
    denied_paths: set[str] = set()
    missing_sources: list[str] = []

    for path in iter_files(source_root):
        if is_denied_path(path, source_root):
            denied_paths.add(relative_posix(path, source_root))

    for missing_name, relative_source, _output_relative in SNAPSHOT_SOURCES:
        source = source_root / relative_source
        if not source.exists():
            print(f"warning: missing source for {missing_name}: {source}", file=sys.stderr)
            missing_sources.append(missing_name)
            continue

        for path in iter_files(source):
            rel_path = relative_posix(path, source_root)
            if is_denied_path(path, source_root):
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
            for path in iter_files(memory_root):
                memory_rel = path.resolve().relative_to(memory_root).as_posix()
                manifest_path = f"memory/{memory_rel}"
                if is_denied_path(path, memory_root):
                    denied_paths.add(manifest_path)
                    continue
                files.append(_file_record(path, memory_root, manifest_path))

    manifest: dict[str, object] = {
        "schema_version": "1",
        "snapshot_at": dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat(),
        "source_host": socket.gethostname(),
        "source_root": str(source_root),
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


def write_snapshot(
    manifest: dict[str, object],
    output_dir: Path,
    source_root: Path,
    *,
    include_memory: bool = False,
    memory_root: Path = DEFAULT_MEMORY_ROOT,
) -> None:
    output_dir = output_dir.resolve()
    source_root = source_root.resolve()
    memory_root = memory_root.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    for _name, relative_source, output_relative in SNAPSHOT_SOURCES:
        source = source_root / relative_source
        if not source.exists():
            continue
        for path in iter_files(source):
            if is_denied_path(path, source_root):
                continue
            destination = output_dir / output_relative / path.relative_to(source)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)

    if include_memory and memory_root.exists():
        with tarfile.open(output_dir / "memory.tar.gz", "w:gz") as archive:
            for path in iter_files(memory_root):
                if is_denied_path(path, memory_root):
                    continue
                archive.add(path, arcname=path.relative_to(memory_root))

    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


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
        "--source-root",
        type=Path,
        help="repo working tree root to collect from",
    )
    parser.add_argument(
        "--memory-root",
        type=Path,
        default=DEFAULT_MEMORY_ROOT,
        help="controller memory directory",
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
        source_root = args.source_root.resolve() if args.source_root else find_source_root()
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
        write_snapshot(
            manifest,
            args.output_dir,
            source_root,
            include_memory=args.include_memory,
            memory_root=args.memory_root,
        )
    else:
        if args.output_dir != DEFAULT_OUTPUT_DIR:
            print(f"[DRY-RUN] Would write to {args.output_dir}", file=sys.stderr)
        print(json.dumps(manifest, indent=2, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

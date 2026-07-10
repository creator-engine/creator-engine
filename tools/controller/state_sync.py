#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import socket
import stat
import sys
import tarfile
import uuid
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

_REQUIRED_DIR_FD_CALLABLES = {
    "open": os.open,
    "stat": os.stat,
    "mkdir": os.mkdir,
    "rename": os.rename,
    "unlink": os.unlink,
    "rmdir": os.rmdir,
}
_UNSUPPORTED_DESCRIPTOR_PRIMITIVES = tuple(
    name
    for name, function in _REQUIRED_DIR_FD_CALLABLES.items()
    if function not in os.supports_dir_fd
)
if os.listdir not in os.supports_fd:
    _UNSUPPORTED_DESCRIPTOR_PRIMITIVES += ("listdir(fd)",)
if not hasattr(os, "O_DIRECTORY") or not hasattr(os, "O_NOFOLLOW"):
    _UNSUPPORTED_DESCRIPTOR_PRIMITIVES += ("O_DIRECTORY/O_NOFOLLOW",)


class SnapshotError(RuntimeError):
    """The snapshot cannot be published without weakening its guarantees."""


def _require_descriptor_primitives() -> None:
    if _UNSUPPORTED_DESCRIPTOR_PRIMITIVES:
        names = ", ".join(sorted(_UNSUPPORTED_DESCRIPTOR_PRIMITIVES))
        raise SnapshotError(f"descriptor-relative no-follow filesystem operations unsupported: {names}")


def _lexical_absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path.expanduser())))


def _directory_flags() -> int:
    return os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW


def _validate_relative(path: Path) -> Path:
    if path.is_absolute() or not path.parts or ".." in path.parts:
        raise SnapshotError(f"invalid relative snapshot path: {path}")
    return path


def _open_directory_path(path: Path, *, create: bool = False) -> int:
    """Open a directory by walking every absolute component without following links."""
    _require_descriptor_primitives()
    absolute = _lexical_absolute(path)
    descriptor = os.open(absolute.anchor, _directory_flags())
    try:
        for component in absolute.parts[1:]:
            try:
                child = os.open(component, _directory_flags(), dir_fd=descriptor)
            except FileNotFoundError:
                if not create:
                    raise
                try:
                    os.mkdir(component, mode=0o700, dir_fd=descriptor)
                except FileExistsError:
                    pass
                child = os.open(component, _directory_flags(), dir_fd=descriptor)
            except OSError as exc:
                raise SnapshotError(
                    f"refused symlinked or non-directory path component {component!r} in {absolute}"
                ) from exc
            os.close(descriptor)
            descriptor = child
        return descriptor
    except Exception:
        os.close(descriptor)
        raise


def _open_directory_at(root_descriptor: int, relative: Path, *, create: bool = False) -> int:
    relative = _validate_relative(relative)
    descriptor = os.dup(root_descriptor)
    try:
        for component in relative.parts:
            try:
                child = os.open(component, _directory_flags(), dir_fd=descriptor)
            except FileNotFoundError:
                if not create:
                    raise
                try:
                    os.mkdir(component, mode=0o700, dir_fd=descriptor)
                except FileExistsError:
                    pass
                child = os.open(component, _directory_flags(), dir_fd=descriptor)
            except OSError as exc:
                raise SnapshotError(
                    f"refused symlinked or non-directory ancestor in relative path {relative}"
                ) from exc
            os.close(descriptor)
            descriptor = child
        return descriptor
    except Exception:
        os.close(descriptor)
        raise


def _open_parent_at(root_descriptor: int, relative: Path, *, create: bool = False) -> tuple[int, str]:
    relative = _validate_relative(relative)
    if len(relative.parts) == 1:
        return os.dup(root_descriptor), relative.name
    parent = Path(*relative.parts[:-1])
    return _open_directory_at(root_descriptor, parent, create=create), relative.name


def _open_regular_file_at(root_descriptor: int, relative: Path) -> int:
    parent_descriptor, leaf = _open_parent_at(root_descriptor, relative)
    try:
        try:
            descriptor = os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent_descriptor)
        except OSError as exc:
            raise SnapshotError(f"refused unreadable or symlinked source file: {relative}") from exc
    finally:
        os.close(parent_descriptor)

    if not stat.S_ISREG(os.fstat(descriptor).st_mode):
        os.close(descriptor)
        raise SnapshotError(f"refused non-regular source file: {relative}")
    return descriptor


def _hash_descriptor(descriptor: int, display_path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    with os.fdopen(descriptor, "rb") as handle:
        before = os.fstat(handle.fileno())
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
        after = os.fstat(handle.fileno())

    identity_before = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    identity_after = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    if identity_before != identity_after:
        raise SnapshotError(f"source changed while it was being hashed: {display_path}")
    return after.st_size, digest.hexdigest()


def find_source_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    raise RuntimeError("could not auto-detect source root: no .git found")


def sha256_file(path: Path) -> str:
    absolute = _lexical_absolute(path)
    parent_descriptor = _open_directory_path(absolute.parent)
    try:
        descriptor = _open_regular_file_at(parent_descriptor, Path(absolute.name))
        return _hash_descriptor(descriptor, absolute)[1]
    finally:
        os.close(parent_descriptor)


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


def _walk_entries_at(root_descriptor: int, prefix: Path | None = None) -> Iterable[tuple[Path, os.stat_result]]:
    prefix = prefix or Path()
    try:
        names = sorted(os.listdir(root_descriptor))
    except OSError as exc:
        raise SnapshotError("source directory changed during traversal") from exc

    for name in names:
        if name == ".git":
            continue
        relative = prefix / name
        try:
            entry_stat = os.stat(name, dir_fd=root_descriptor, follow_symlinks=False)
        except OSError as exc:
            raise SnapshotError(f"source entry changed during traversal: {relative}") from exc
        if stat.S_ISDIR(entry_stat.st_mode):
            child_descriptor = _open_directory_at(root_descriptor, Path(name))
            try:
                yield from _walk_entries_at(child_descriptor, relative)
            finally:
                os.close(child_descriptor)
        else:
            yield relative, entry_stat


def iter_entries(root: Path) -> Iterable[Path]:
    absolute = _lexical_absolute(root)
    descriptor = _open_directory_path(absolute)
    try:
        for relative, _entry_stat in _walk_entries_at(descriptor):
            yield absolute / relative
    finally:
        os.close(descriptor)


def iter_files(root: Path) -> Iterable[Path]:
    absolute = _lexical_absolute(root)
    descriptor = _open_directory_path(absolute)
    try:
        for relative, entry_stat in _walk_entries_at(descriptor):
            if stat.S_ISREG(entry_stat.st_mode):
                yield absolute / relative
    finally:
        os.close(descriptor)


def _file_record_at(
    root_descriptor: int,
    source_relative: Path,
    manifest_path: str,
) -> dict[str, object]:
    descriptor = _open_regular_file_at(root_descriptor, source_relative)
    size, digest = _hash_descriptor(descriptor, source_relative)
    return {
        "path": manifest_path,
        "size": size,
        "sha256": digest,
    }


def default_memory_root(repo_root: Path, *, home: Path | None = None) -> Path:
    absolute_repo = _lexical_absolute(repo_root)
    project_slug = absolute_repo.as_posix().replace("/", "-")
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
    _require_descriptor_primitives()
    source_root = _lexical_absolute(source_root)
    memory_root_source = "override" if memory_root is not None else "derived-from-repo-root"
    memory_root = (
        _lexical_absolute(memory_root)
        if memory_root is not None
        else _lexical_absolute(default_memory_root(source_root))
    )
    target_branch = target_branch or f"ce-controller-state/{socket.gethostname()}"

    files: list[dict[str, object]] = []
    denied_paths: set[str] = set()
    missing_sources: list[str] = []

    source_root_descriptor = _open_directory_path(source_root)
    try:
        for relative, _entry_stat in _walk_entries_at(source_root_descriptor):
            if is_denied_path(relative):
                denied_paths.add(relative.as_posix())

        for missing_name, relative_source, _output_relative in SNAPSHOT_SOURCES:
            try:
                source_descriptor = _open_directory_at(source_root_descriptor, relative_source)
            except FileNotFoundError:
                print(
                    f"warning: missing source for {missing_name}: {source_root / relative_source}",
                    file=sys.stderr,
                )
                missing_sources.append(missing_name)
                continue

            try:
                for source_relative, entry_stat in _walk_entries_at(source_descriptor):
                    repo_relative = relative_source / source_relative
                    rel_path = repo_relative.as_posix()
                    if stat.S_ISLNK(entry_stat.st_mode) or is_denied_path(repo_relative):
                        denied_paths.add(rel_path)
                        continue
                    if not stat.S_ISREG(entry_stat.st_mode):
                        denied_paths.add(rel_path)
                        continue
                    files.append(
                        _file_record_at(source_root_descriptor, repo_relative, rel_path)
                    )
            finally:
                os.close(source_descriptor)
    finally:
        os.close(source_root_descriptor)

    data_classes = ["arc_state", "dispatch_state"]
    if include_memory:
        data_classes.append("memory")
        try:
            memory_root_descriptor = _open_directory_path(memory_root)
        except FileNotFoundError:
            print(f"warning: missing source for memory: {memory_root}", file=sys.stderr)
            missing_sources.append("memory")
        else:
            try:
                for memory_relative, entry_stat in _walk_entries_at(memory_root_descriptor):
                    manifest_path = f"memory/{memory_relative.as_posix()}"
                    if stat.S_ISLNK(entry_stat.st_mode) or is_denied_path(memory_relative):
                        denied_paths.add(manifest_path)
                        continue
                    if not stat.S_ISREG(entry_stat.st_mode):
                        denied_paths.add(manifest_path)
                        continue
                    files.append(
                        _file_record_at(memory_root_descriptor, memory_relative, manifest_path)
                    )
            finally:
                os.close(memory_root_descriptor)

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


def _manifest_source_and_destination(manifest_path: str) -> tuple[str, Path, Path | None]:
    relative = Path(manifest_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise SnapshotError(f"invalid path in manifest: {manifest_path}")

    if relative.parts and relative.parts[0] == "memory":
        memory_relative = Path(*relative.parts[1:])
        return "memory", _validate_relative(memory_relative), None

    for _name, relative_source, output_relative in SNAPSHOT_SOURCES:
        try:
            payload_relative = relative.relative_to(relative_source)
        except ValueError:
            continue
        return "repo", relative, output_relative / payload_relative
    raise SnapshotError(f"manifest path is outside snapshot sources: {manifest_path}")


def _create_file_at(root_descriptor: int, relative: Path) -> int:
    parent_descriptor, leaf = _open_parent_at(root_descriptor, relative, create=True)
    try:
        return os.open(
            leaf,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=parent_descriptor,
        )
    finally:
        os.close(parent_descriptor)


def _copy_verified_at(
    source_root_descriptor: int,
    source_relative: Path,
    destination_root_descriptor: int,
    destination_relative: Path,
    record: dict[str, object],
) -> None:
    expected_size = int(record["size"])
    expected_digest = str(record["sha256"])
    source_descriptor = _open_regular_file_at(source_root_descriptor, source_relative)
    destination_descriptor = _create_file_at(destination_root_descriptor, destination_relative)
    digest = hashlib.sha256()
    copied_size = 0
    with os.fdopen(source_descriptor, "rb") as source_handle, os.fdopen(
        destination_descriptor, "wb"
    ) as output_handle:
        before = os.fstat(source_handle.fileno())
        for chunk in iter(lambda: source_handle.read(1024 * 1024), b""):
            output_handle.write(chunk)
            digest.update(chunk)
            copied_size += len(chunk)
        after = os.fstat(source_handle.fileno())

    identity_before = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    identity_after = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    if identity_before != identity_after:
        raise SnapshotError(f"source changed during publication: {source_relative}")
    if copied_size != expected_size or digest.hexdigest() != expected_digest:
        raise SnapshotError(
            f"source changed between collection and publication: {source_relative}"
        )


def _write_bytes_at(root_descriptor: int, relative: Path, payload: bytes) -> None:
    descriptor = _create_file_at(root_descriptor, relative)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(payload)


def _clear_directory(descriptor: int) -> None:
    for name in os.listdir(descriptor):
        entry_stat = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
        if stat.S_ISDIR(entry_stat.st_mode):
            child_descriptor = _open_directory_at(descriptor, Path(name))
            try:
                _clear_directory(child_descriptor)
            finally:
                os.close(child_descriptor)
            os.rmdir(name, dir_fd=descriptor)
        else:
            os.unlink(name, dir_fd=descriptor)


def _remove_tree_at(parent_descriptor: int, name: str) -> None:
    try:
        descriptor = _open_directory_at(parent_descriptor, Path(name))
    except FileNotFoundError:
        return
    try:
        _clear_directory(descriptor)
    finally:
        os.close(descriptor)
    os.rmdir(name, dir_fd=parent_descriptor)


def _create_staging_directory(parent_descriptor: int, output_name: str) -> tuple[str, int]:
    for _attempt in range(32):
        name = f".{output_name}.staging-{uuid.uuid4().hex}"
        try:
            os.mkdir(name, mode=0o700, dir_fd=parent_descriptor)
        except FileExistsError:
            continue
        return name, _open_directory_at(parent_descriptor, Path(name))
    raise SnapshotError("could not allocate a unique staging directory")


def _assert_empty_output_or_absent(parent_descriptor: int, output_name: str) -> None:
    try:
        entry_stat = os.stat(output_name, dir_fd=parent_descriptor, follow_symlinks=False)
    except FileNotFoundError:
        return
    if not stat.S_ISDIR(entry_stat.st_mode):
        raise SnapshotError(f"refused non-empty or symlink output entry: {output_name}")
    descriptor = _open_directory_at(parent_descriptor, Path(output_name))
    try:
        if os.listdir(descriptor):
            raise SnapshotError(f"refused non-empty output directory: {output_name}")
    finally:
        os.close(descriptor)


def _verify_pinned_directory(path: Path, pinned_descriptor: int) -> None:
    """Refuse if the lexical parent path no longer names the pinned directory."""
    try:
        check_descriptor = _open_directory_path(path)
    except (FileNotFoundError, SnapshotError) as exc:
        raise SnapshotError(f"output parent changed before publication: {path}") from exc
    try:
        pinned = os.fstat(pinned_descriptor)
        current = os.fstat(check_descriptor)
        if (pinned.st_dev, pinned.st_ino) != (current.st_dev, current.st_ino):
            raise SnapshotError(f"output parent changed before publication: {path}")
    finally:
        os.close(check_descriptor)


def _write_memory_archive(
    staging_descriptor: int,
    memory_staging_descriptor: int,
    records: list[tuple[dict[str, object], Path]],
) -> None:
    archive_descriptor = _create_file_at(staging_descriptor, Path("memory.tar.gz"))
    with os.fdopen(archive_descriptor, "wb") as archive_handle:
        with tarfile.open(fileobj=archive_handle, mode="w:gz") as archive:
            for record, memory_relative in records:
                source_descriptor = _open_regular_file_at(
                    memory_staging_descriptor, memory_relative
                )
                with os.fdopen(source_descriptor, "rb") as source_handle:
                    info = tarfile.TarInfo(memory_relative.as_posix())
                    info.size = int(record["size"])
                    info.mode = 0o600
                    archive.addfile(info, source_handle)


def write_snapshot(
    manifest: dict[str, object],
    output_dir: Path,
    source_root: Path,
    *,
    include_memory: bool = False,
    memory_root: Path | None = None,
) -> None:
    _require_descriptor_primitives()
    output_dir = _lexical_absolute(output_dir)
    source_root = _lexical_absolute(source_root)
    memory_root = (
        _lexical_absolute(memory_root)
        if memory_root is not None
        else _lexical_absolute(default_memory_root(source_root))
    )
    if not output_dir.name:
        raise SnapshotError("output directory must have a final path component")

    records = manifest.get("files")
    if not isinstance(records, list):
        raise SnapshotError("manifest.files must be a list")
    parsed_records: list[tuple[dict[str, object], str, Path, Path | None]] = []
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("path"), str):
            raise SnapshotError("manifest contains an invalid file record")
        source_kind, source_relative, payload_relative = _manifest_source_and_destination(
            str(record["path"])
        )
        if source_kind == "memory" and not include_memory:
            raise SnapshotError("manifest contains memory files but memory inclusion is disabled")
        parsed_records.append((record, source_kind, source_relative, payload_relative))

    source_root_descriptor = _open_directory_path(source_root)
    memory_root_descriptor: int | None = None
    parent_descriptor: int | None = None
    staging_descriptor: int | None = None
    memory_staging_descriptor: int | None = None
    staging_name: str | None = None
    published = False
    try:
        if any(source_kind == "memory" for _r, source_kind, _s, _d in parsed_records):
            memory_root_descriptor = _open_directory_path(memory_root)

        parent_descriptor = _open_directory_path(output_dir.parent, create=True)
        _assert_empty_output_or_absent(parent_descriptor, output_dir.name)
        staging_name, staging_descriptor = _create_staging_directory(
            parent_descriptor, output_dir.name
        )

        memory_records: list[tuple[dict[str, object], Path]] = []
        for record, source_kind, source_relative, payload_relative in parsed_records:
            if source_kind == "memory":
                if memory_root_descriptor is None:
                    raise SnapshotError("memory root was not pinned")
                if memory_staging_descriptor is None:
                    memory_staging_descriptor = _open_directory_at(
                        staging_descriptor, Path(".memory-staging"), create=True
                    )
                _copy_verified_at(
                    memory_root_descriptor,
                    source_relative,
                    memory_staging_descriptor,
                    source_relative,
                    record,
                )
                memory_records.append((record, source_relative))
            else:
                if payload_relative is None:
                    raise SnapshotError("repository record has no payload destination")
                _copy_verified_at(
                    source_root_descriptor,
                    source_relative,
                    staging_descriptor,
                    payload_relative,
                    record,
                )

        if memory_records:
            if memory_staging_descriptor is None:
                raise SnapshotError("memory staging directory was not pinned")
            _write_memory_archive(
                staging_descriptor, memory_staging_descriptor, memory_records
            )
            os.close(memory_staging_descriptor)
            memory_staging_descriptor = None
            _remove_tree_at(staging_descriptor, ".memory-staging")

        manifest_payload = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
        _write_bytes_at(staging_descriptor, Path("manifest.json"), manifest_payload)

        _verify_pinned_directory(output_dir.parent, parent_descriptor)
        _assert_empty_output_or_absent(parent_descriptor, output_dir.name)
        try:
            os.rmdir(output_dir.name, dir_fd=parent_descriptor)
        except FileNotFoundError:
            pass
        os.rename(
            staging_name,
            output_dir.name,
            src_dir_fd=parent_descriptor,
            dst_dir_fd=parent_descriptor,
        )
        published = True
    finally:
        if memory_staging_descriptor is not None:
            os.close(memory_staging_descriptor)
        if staging_descriptor is not None:
            if not published:
                try:
                    _clear_directory(staging_descriptor)
                except (OSError, SnapshotError):
                    pass
            os.close(staging_descriptor)
        if not published and staging_name is not None and parent_descriptor is not None:
            try:
                os.rmdir(staging_name, dir_fd=parent_descriptor)
            except OSError:
                pass
        if parent_descriptor is not None:
            os.close(parent_descriptor)
        if memory_root_descriptor is not None:
            os.close(memory_root_descriptor)
        os.close(source_root_descriptor)


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
        source_root = _lexical_absolute(args.repo_root) if args.repo_root else find_source_root()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    try:
        manifest = collect_manifest(
            source_root,
            include_memory=args.include_memory,
            memory_root=args.memory_root,
            target_branch=args.target_branch,
        )
    except (OSError, SnapshotError) as exc:
        print(f"snapshot refused: {exc}", file=sys.stderr)
        return 1

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

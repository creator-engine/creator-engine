"""Read-only upstream update detection for ``surfaces/manifest.yaml``."""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.error import HTTPError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen as _stdlib_urlopen

import yaml

UrlFetcher = Callable[[str], bytes]

NPM_REGISTRY = "https://registry.npmjs.org"
PYPI_API = "https://pypi.org/pypi"
ZIG_DOWNLOAD_INDEX = "https://ziglang.org/download/index.json"
GITHUB_API = "https://api.github.com"


class SurfaceUpdateError(Exception):
    """Raised when the manifest or an upstream response cannot be read."""


@dataclass(frozen=True)
class SurfaceUpdate:
    name: str
    source: str
    current_version: str | None
    current_ref: str | None
    available_version: str | None
    available_ref: str | None = None
    adapter: str = "unsupported"
    update_available: bool | None = None
    status: str = "ok"
    detail: str | None = None
    upstream_url: str | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "source": self.source,
            "adapter": self.adapter,
            "current_version": self.current_version,
            "current_ref": self.current_ref,
            "available_version": self.available_version,
            "available_ref": self.available_ref,
            "update_available": self.update_available,
            "status": self.status,
            "detail": self.detail,
            "upstream_url": self.upstream_url,
        }


@dataclass(frozen=True)
class SurfaceUpdateReport:
    manifest_path: str
    read_only: bool = True
    ok: bool = True
    updates_available: bool = False
    surfaces: tuple[SurfaceUpdate, ...] = ()
    problems: tuple[str, ...] = field(default_factory=tuple)

    def to_json(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "read_only": self.read_only,
            "updates_available": self.updates_available,
            "manifest_path": self.manifest_path,
            "problems": list(self.problems),
            "surfaces": [surface.to_json() for surface in self.surfaces],
        }


def default_fetcher(url: str) -> bytes:
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "creator-engine-validator/surfaces-check-updates",
        },
    )
    with _stdlib_urlopen(request, timeout=20) as response:
        return response.read()


def check_manifest_updates(
    repo_root: Path | str = ".",
    *,
    manifest_path: Path | str | None = None,
    fetcher: UrlFetcher | None = None,
) -> SurfaceUpdateReport:
    root = Path(repo_root)
    manifest = Path(manifest_path) if manifest_path is not None else root / "surfaces" / "manifest.yaml"
    fetch = fetcher or default_fetcher
    try:
        surfaces = _load_manifest_surfaces(manifest)
    except SurfaceUpdateError as exc:
        return SurfaceUpdateReport(
            manifest_path=str(manifest),
            ok=False,
            updates_available=False,
            problems=(str(exc),),
        )

    rows: list[SurfaceUpdate] = []
    problems: list[str] = []
    for surface in surfaces:
        try:
            row = _check_surface(surface, fetcher=fetch)
        except SurfaceUpdateError as exc:
            name = str(surface.get("name", "<unnamed>"))
            source = str(surface.get("source", ""))
            row = SurfaceUpdate(
                name=name,
                source=source,
                current_version=_optional_str(surface.get("version")),
                current_ref=_commit_ref(surface.get("commit_or_digest")),
                available_version=None,
                adapter=_adapter_name(source),
                update_available=None,
                status="error",
                detail=str(exc),
            )
            problems.append(f"{name}: {exc}")
        rows.append(row)

    return SurfaceUpdateReport(
        manifest_path=str(manifest),
        ok=not problems,
        updates_available=any(row.update_available is True for row in rows),
        surfaces=tuple(rows),
        problems=tuple(problems),
    )


def run_cli(args: argparse.Namespace) -> int:
    manifest = getattr(args, "manifest", None)
    repo_root = getattr(args, "repo_root", ".")
    report = check_manifest_updates(repo_root=repo_root, manifest_path=manifest)
    if getattr(args, "json_output", False):
        print(json.dumps(report.to_json(), indent=2, sort_keys=True))
    else:
        _print_report(report)
    return 0 if report.ok else 1


def _load_manifest_surfaces(path: Path) -> list[Mapping[str, Any]]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SurfaceUpdateError(f"manifest_read_failed: {exc}") from exc
    try:
        doc = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise SurfaceUpdateError(f"manifest_parse_failed: {exc}") from exc
    if not isinstance(doc, Mapping):
        raise SurfaceUpdateError("manifest_shape_invalid: top-level document must be a mapping")
    surfaces = doc.get("surfaces")
    if not isinstance(surfaces, list):
        raise SurfaceUpdateError("manifest_shape_invalid: surfaces must be a list")
    typed: list[Mapping[str, Any]] = []
    for index, surface in enumerate(surfaces):
        if not isinstance(surface, Mapping):
            raise SurfaceUpdateError(f"manifest_shape_invalid: surfaces[{index}] must be a mapping")
        typed.append(surface)
    return typed


def _check_surface(surface: Mapping[str, Any], *, fetcher: UrlFetcher) -> SurfaceUpdate:
    source = str(surface.get("source", ""))
    if source.startswith("npm:"):
        return _check_npm(surface, fetcher=fetcher)
    if source.startswith("pypi:"):
        return _check_pypi(surface, fetcher=fetcher)
    if source.startswith("https://ziglang.org/download/"):
        return _check_zig(surface, fetcher=fetcher)
    github_repo = _github_repo_from_source(source)
    if github_repo is not None:
        return _check_github_release(surface, owner_repo=github_repo, fetcher=fetcher)
    return _skipped(surface, "unsupported source")


def _check_npm(surface: Mapping[str, Any], *, fetcher: UrlFetcher) -> SurfaceUpdate:
    package = str(surface.get("source", "")).removeprefix("npm:")
    url = f"{NPM_REGISTRY}/{quote(package, safe='@')}"
    payload = _fetch_json(url, fetcher=fetcher)
    dist_tags = payload.get("dist-tags")
    if not isinstance(dist_tags, Mapping):
        raise SurfaceUpdateError("npm_response_invalid: missing dist-tags")
    latest = _optional_str(dist_tags.get("latest"))
    if latest is None:
        raise SurfaceUpdateError("npm_response_invalid: missing dist-tags.latest")
    current = _optional_str(surface.get("version"))
    return _row(
        surface,
        adapter="npm",
        available_version=latest,
        update_available=_is_newer(latest, current),
        upstream_url=url,
    )


def _check_pypi(surface: Mapping[str, Any], *, fetcher: UrlFetcher) -> SurfaceUpdate:
    package = str(surface.get("source", "")).removeprefix("pypi:")
    url = f"{PYPI_API}/{quote(package, safe='')}/json"
    payload = _fetch_json(url, fetcher=fetcher)
    info = payload.get("info")
    if not isinstance(info, Mapping):
        raise SurfaceUpdateError("pypi_response_invalid: missing info")
    latest = _optional_str(info.get("version"))
    if latest is None:
        raise SurfaceUpdateError("pypi_response_invalid: missing info.version")
    current = _optional_str(surface.get("version"))
    return _row(
        surface,
        adapter="pypi",
        available_version=latest,
        update_available=_is_newer(latest, current),
        upstream_url=url,
    )


def _check_zig(surface: Mapping[str, Any], *, fetcher: UrlFetcher) -> SurfaceUpdate:
    payload = _fetch_json(ZIG_DOWNLOAD_INDEX, fetcher=fetcher)
    versions = [key for key in payload if isinstance(key, str) and _SEMVER_RE.fullmatch(key)]
    latest = _latest_version(versions)
    if latest is None:
        raise SurfaceUpdateError("zig_response_invalid: no stable semver versions")
    current = _optional_str(surface.get("version"))
    return _row(
        surface,
        adapter="zig-download-index",
        available_version=latest,
        update_available=_is_newer(latest, current),
        upstream_url=ZIG_DOWNLOAD_INDEX,
    )


def _check_github_release(
    surface: Mapping[str, Any],
    *,
    owner_repo: str,
    fetcher: UrlFetcher,
) -> SurfaceUpdate:
    url = f"{GITHUB_API}/repos/{owner_repo}/releases/latest"
    try:
        raw = fetcher(url)
    except HTTPError as exc:
        if exc.code == 404:
            return _row(
                surface,
                adapter="github-releases",
                available_version=None,
                update_available=None,
                status="skipped",
                detail="github_latest_release_unavailable: no latest release found (HTTP 404)",
                upstream_url=url,
            )
        raise SurfaceUpdateError(f"fetch_failed: {url}: {exc}") from exc
    except Exception as exc:  # pragma: no cover - exact transport exceptions vary
        raise SurfaceUpdateError(f"fetch_failed: {url}: {exc}") from exc
    payload = _json_payload(raw, url)
    tag = _optional_str(payload.get("tag_name")) or _optional_str(payload.get("name"))
    if tag is None:
        raise SurfaceUpdateError("github_response_invalid: missing tag_name")
    target = _optional_str(payload.get("target_commitish"))
    current_ref = _commit_ref(surface.get("commit_or_digest"))
    update_available = None
    if current_ref and target:
        update_available = not _refs_match(current_ref, target)
    elif _optional_str(surface.get("version")):
        update_available = _is_newer(_strip_v_prefix(tag), _optional_str(surface.get("version")))
    return _row(
        surface,
        adapter="github-releases",
        available_version=tag,
        available_ref=target,
        update_available=update_available,
        upstream_url=url,
    )


def _fetch_json(url: str, *, fetcher: UrlFetcher) -> Mapping[str, Any]:
    try:
        raw = fetcher(url)
    except Exception as exc:  # pragma: no cover - exact transport exceptions vary
        raise SurfaceUpdateError(f"fetch_failed: {url}: {exc}") from exc
    return _json_payload(raw, url)


def _json_payload(raw: bytes, url: str) -> Mapping[str, Any]:
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SurfaceUpdateError(f"json_parse_failed: {url}: {exc}") from exc
    if not isinstance(payload, Mapping):
        raise SurfaceUpdateError(f"json_shape_invalid: {url}: top-level JSON must be an object")
    return payload


def _row(
    surface: Mapping[str, Any],
    *,
    adapter: str,
    available_version: str | None,
    available_ref: str | None = None,
    update_available: bool | None,
    status: str = "ok",
    detail: str | None = None,
    upstream_url: str | None = None,
) -> SurfaceUpdate:
    return SurfaceUpdate(
        name=str(surface.get("name", "<unnamed>")),
        source=str(surface.get("source", "")),
        current_version=_optional_str(surface.get("version")),
        current_ref=_commit_ref(surface.get("commit_or_digest")),
        available_version=available_version,
        available_ref=available_ref,
        adapter=adapter,
        update_available=update_available,
        status=status,
        detail=detail,
        upstream_url=upstream_url,
    )


def _skipped(surface: Mapping[str, Any], detail: str) -> SurfaceUpdate:
    return _row(
        surface,
        adapter=_adapter_name(str(surface.get("source", ""))),
        available_version=None,
        update_available=None,
        status="skipped",
        detail=detail,
    )


def _print_report(report: SurfaceUpdateReport) -> None:
    print(f"surfaces manifest: {report.manifest_path}")
    print("mode: read-only")
    for row in report.surfaces:
        available = row.available_version or "unknown"
        if row.available_ref:
            available = f"{available} ({row.available_ref})"
        current = row.current_version or row.current_ref or "unknown"
        marker = "update" if row.update_available is True else row.status
        print(f"- {row.name}: current={current} available={available} status={marker}")
        if row.detail:
            print(f"  detail: {row.detail}")
    if report.problems:
        print("problems:")
        for problem in report.problems:
            print(f"- {problem}")


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _commit_ref(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    return None


def _adapter_name(source: str) -> str:
    if source.startswith("npm:"):
        return "npm"
    if source.startswith("pypi:"):
        return "pypi"
    if source.startswith("https://ziglang.org/download/"):
        return "zig-download-index"
    if _github_repo_from_source(source) is not None:
        return "github-releases"
    return "unsupported"


def _github_repo_from_source(source: str) -> str | None:
    parsed = urlparse(source)
    if parsed.netloc != "github.com":
        return None
    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if len(parts) < 2:
        return None
    repo = parts[1]
    if repo.endswith(".git"):
        repo = repo[:-4]
    if not parts[0] or not repo:
        return None
    return f"{parts[0]}/{repo}"


def _refs_match(current: str, available: str) -> bool:
    return available.startswith(current) or current.startswith(available)


_SEMVER_RE = re.compile(r"v?(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:[-+][0-9A-Za-z.-]+)?")


def _strip_v_prefix(version: str) -> str:
    return version[1:] if version.startswith("v") else version


def _version_key(version: str) -> tuple[int, ...]:
    match = _SEMVER_RE.fullmatch(version)
    if match is None:
        return ()
    return tuple(int(part) for part in match.groups(default="0")[:3])


def _latest_version(versions: list[str]) -> str | None:
    if not versions:
        return None
    return max(versions, key=_version_key)


def _is_newer(available: str | None, current: str | None) -> bool | None:
    if available is None or current is None:
        return None
    available_key = _version_key(_strip_v_prefix(available))
    current_key = _version_key(_strip_v_prefix(current))
    if available_key and current_key:
        return available_key > current_key
    return available != current

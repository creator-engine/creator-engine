from __future__ import annotations

import json
from pathlib import Path
from urllib.error import HTTPError

import yaml

from creator_engine_validator import ce_cli
from creator_engine_validator.surfaces import check_updates


def _manifest_doc() -> dict[str, object]:
    return {
        "surfaces": [
            {
                "name": "codex",
                "version": "0.141.0",
                "commit_or_digest": None,
                "source": "npm:@openai/codex",
                "custody": "rented",
                "update_policy": "downstream digest capture pending",
                "last_evaluated": "2026-06-26",
            },
            {
                "name": "herdr",
                "version": None,
                "commit_or_digest": "ff924966",
                "source": "https://github.com/creator-engine/herdr-ce.git",
                "custody": "fork",
                "update_policy": "pinned fork commit; update only by reviewed manifest change",
                "last_evaluated": "2026-06-26",
            },
            {
                "name": "Zig toolchain",
                "version": "0.15.2",
                "commit_or_digest": {"linux-x86_64": {"sha256": "0" * 64}},
                "source": "https://ziglang.org/download/0.15.2/",
                "custody": "upstream binary toolchain",
                "update_policy": "per-architecture sha256 required before use",
                "last_evaluated": "2026-06-26",
            },
            {
                "name": "PyYAML",
                "version": "6.0.3",
                "commit_or_digest": None,
                "source": "pypi:PyYAML",
                "custody": "pypi",
                "update_policy": "requirements pin; digest capture pending",
                "last_evaluated": "2026-06-26",
            },
            {
                "name": "OpenBao",
                "version": None,
                "commit_or_digest": None,
                "source": "host:openbao",
                "custody": "host-only",
                "update_policy": "host inventory required before pinning",
                "last_evaluated": "2026-06-26",
            },
        ]
    }


def _write_manifest(root: Path, doc: dict[str, object] | None = None) -> Path:
    manifest = root / "surfaces" / "manifest.yaml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(yaml.safe_dump(doc or _manifest_doc(), sort_keys=False), encoding="utf-8")
    return manifest


def _json_bytes(payload: object) -> bytes:
    return json.dumps(payload).encode("utf-8")


def _upstreams() -> dict[str, bytes]:
    return {
        "https://registry.npmjs.org/@openai%2Fcodex": _json_bytes({"dist-tags": {"latest": "0.142.0"}}),
        "https://api.github.com/repos/creator-engine/herdr-ce/releases/latest": _json_bytes(
            {"tag_name": "v0.2.0", "target_commitish": "deadbeef"}
        ),
        "https://ziglang.org/download/index.json": _json_bytes(
            {"master": {}, "0.15.2": {}, "0.16.0": {}, "0.14.1": {}}
        ),
        "https://pypi.org/pypi/PyYAML/json": _json_bytes({"info": {"version": "6.0.3"}}),
    }


def _fetcher(mapping: dict[str, bytes], calls: list[str] | None = None):
    def fetch(url: str) -> bytes:
        if calls is not None:
            calls.append(url)
        return mapping[url]

    return fetch


def _github_404_fetcher(mapping: dict[str, bytes]):
    def fetch(url: str) -> bytes:
        if url == "https://api.github.com/repos/creator-engine/herdr-ce/releases/latest":
            raise HTTPError(url, 404, "Not Found", hdrs=None, fp=None)
        return mapping[url]

    return fetch


def test_check_manifest_updates_reports_current_vs_available_without_mutating(tmp_path: Path):
    manifest = _write_manifest(tmp_path)
    before = manifest.read_bytes()

    report = check_updates.check_manifest_updates(tmp_path, fetcher=_fetcher(_upstreams()))

    assert report.ok is True
    assert report.read_only is True
    assert report.updates_available is True
    assert manifest.read_bytes() == before

    rows = {row.name: row for row in report.surfaces}
    assert rows["codex"].adapter == "npm"
    assert rows["codex"].current_version == "0.141.0"
    assert rows["codex"].available_version == "0.142.0"
    assert rows["codex"].update_available is True

    assert rows["herdr"].adapter == "github-releases"
    assert rows["herdr"].current_ref == "ff924966"
    assert rows["herdr"].available_version == "v0.2.0"
    assert rows["herdr"].available_ref == "deadbeef"
    assert rows["herdr"].update_available is True

    assert rows["Zig toolchain"].adapter == "zig-download-index"
    assert rows["Zig toolchain"].available_version == "0.16.0"
    assert rows["Zig toolchain"].update_available is True

    assert rows["PyYAML"].adapter == "pypi"
    assert rows["PyYAML"].available_version == "6.0.3"
    assert rows["PyYAML"].update_available is False

    assert rows["OpenBao"].status == "skipped"
    assert rows["OpenBao"].update_available is None


def test_github_latest_release_404_is_nonfatal_skipped_row(tmp_path: Path):
    manifest = _write_manifest(tmp_path)
    before = manifest.read_bytes()
    mapping = _upstreams()
    del mapping["https://api.github.com/repos/creator-engine/herdr-ce/releases/latest"]

    report = check_updates.check_manifest_updates(tmp_path, fetcher=_github_404_fetcher(mapping))

    assert report.ok is True
    assert report.problems == ()
    assert manifest.read_bytes() == before
    rows = {row.name: row for row in report.surfaces}
    assert rows["herdr"].adapter == "github-releases"
    assert rows["herdr"].current_ref == "ff924966"
    assert rows["herdr"].available_version is None
    assert rows["herdr"].available_ref is None
    assert rows["herdr"].update_available is None
    assert rows["herdr"].status == "skipped"
    assert rows["herdr"].detail == "github_latest_release_unavailable: no latest release found (HTTP 404)"


def test_github_successful_malformed_json_is_error(tmp_path: Path):
    _write_manifest(tmp_path)
    mapping = _upstreams()
    mapping["https://api.github.com/repos/creator-engine/herdr-ce/releases/latest"] = _json_bytes(
        {"target_commitish": "deadbeef"}
    )

    report = check_updates.check_manifest_updates(tmp_path, fetcher=_fetcher(mapping))

    assert report.ok is False
    assert any(problem == "herdr: github_response_invalid: missing tag_name" for problem in report.problems)
    rows = {row.name: row for row in report.surfaces}
    assert rows["herdr"].status == "error"
    assert rows["herdr"].current_ref == "ff924966"


def test_host_only_surfaces_do_not_fetch_network(tmp_path: Path):
    _write_manifest(
        tmp_path,
        {
            "surfaces": [
                {
                    "name": "host-only",
                    "version": None,
                    "commit_or_digest": None,
                    "source": "host:tool",
                    "custody": "host-only",
                    "update_policy": "host inventory required before pinning",
                    "last_evaluated": "2026-06-26",
                }
            ]
        },
    )
    calls: list[str] = []

    report = check_updates.check_manifest_updates(tmp_path, fetcher=_fetcher({}, calls))

    assert report.ok is True
    assert calls == []
    assert report.surfaces[0].status == "skipped"


def test_fetch_failure_is_reported_as_problem(tmp_path: Path):
    _write_manifest(tmp_path)
    mapping = _upstreams()
    del mapping["https://pypi.org/pypi/PyYAML/json"]

    report = check_updates.check_manifest_updates(tmp_path, fetcher=_fetcher(mapping))

    assert report.ok is False
    assert any(problem.startswith("PyYAML: fetch_failed:") for problem in report.problems)
    rows = {row.name: row for row in report.surfaces}
    assert rows["PyYAML"].status == "error"


def test_ce_surfaces_check_updates_cli_json_uses_read_only_runtime(monkeypatch, tmp_path: Path, capsys):
    _write_manifest(tmp_path)
    monkeypatch.setattr(check_updates, "default_fetcher", _fetcher(_upstreams()))

    rc = ce_cli.main(["surfaces", "check-updates", "--repo-root", str(tmp_path), "--json"])

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["read_only"] is True
    assert payload["updates_available"] is True
    assert {row["name"] for row in payload["surfaces"]} >= {"codex", "herdr", "Zig toolchain", "PyYAML"}

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

import pytest


pytestmark = pytest.mark.fast


REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = REPO_ROOT / "tools" / "controller" / "state_sync.py"

spec = importlib.util.spec_from_file_location("controller_state_sync", MODULE_PATH)
assert spec is not None
controller_state_sync = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(controller_state_sync)


def _seed(path: Path, content: str = "content\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _commit_manifest(tmp_path: Path, *extra_args: str) -> dict[str, object]:
    out = tmp_path / "out"
    rc = controller_state_sync.main(
        ["--source-root", str(tmp_path), "--commit", "--output-dir", str(out), *extra_args]
    )
    assert rc == 0
    return json.loads((out / "manifest.json").read_text(encoding="utf-8"))


def _forbid_descriptor_opens_below(monkeypatch, forbidden_root: Path) -> None:
    """Fail the test if production code ever opens the external tree."""
    real_open = os.open
    forbidden_root = forbidden_root.resolve()

    def guarded_open(path, flags, mode=0o777, *, dir_fd=None):
        if dir_fd is None:
            descriptor = real_open(path, flags, mode)
        else:
            descriptor = real_open(path, flags, mode, dir_fd=dir_fd)
        try:
            opened_path = Path(os.readlink(f"/proc/self/fd/{descriptor}"))
            opened_path.relative_to(forbidden_root)
        except (OSError, ValueError):
            return descriptor
        os.close(descriptor)
        raise AssertionError(f"opened forbidden external path: {opened_path}")

    monkeypatch.setattr(controller_state_sync.os, "open", guarded_open)


def test_denylist_excludes_pat_files(tmp_path):
    _seed(tmp_path / ".ce/state/research/leaky.pat")

    manifest = controller_state_sync.collect_manifest(tmp_path)

    assert any("leaky.pat" in path for path in manifest["denied_paths"])
    assert not any(str(item["path"]).endswith(".pat") for item in manifest["files"])


def test_denylist_excludes_pem_files(tmp_path):
    _seed(tmp_path / ".ce/state/research/leaky.pem")

    manifest = controller_state_sync.collect_manifest(tmp_path)

    assert any("leaky.pem" in path for path in manifest["denied_paths"])
    assert not any(str(item["path"]).endswith(".pem") for item in manifest["files"])


def test_denylist_excludes_pass_files(tmp_path):
    _seed(tmp_path / ".ce/state/research/leaky.pass")

    manifest = controller_state_sync.collect_manifest(tmp_path)

    assert any("leaky.pass" in path for path in manifest["denied_paths"])
    assert not any(str(item["path"]).endswith(".pass") for item in manifest["files"])


def test_denylist_excludes_ce_keys_dir(tmp_path):
    _seed(tmp_path / ".ce-keys/auth.json")

    manifest = controller_state_sync.collect_manifest(tmp_path)

    assert any(".ce-keys/auth.json" in path for path in manifest["denied_paths"])
    assert not any(".ce-keys" in str(item["path"]) for item in manifest["files"])


def test_denylist_excludes_key_files(tmp_path):
    _seed(tmp_path / ".ce/briefs/auth.key")

    manifest = controller_state_sync.collect_manifest(tmp_path)

    assert any("auth.key" in path for path in manifest["denied_paths"])
    assert not any(str(item["path"]).endswith(".key") for item in manifest["files"])


def test_denylist_excludes_name_fragments(tmp_path):
    _seed(tmp_path / ".ce/claims/service_credentials.json")
    _seed(tmp_path / ".ce/claims/api_token.txt")

    manifest = controller_state_sync.collect_manifest(tmp_path)

    assert any("service_credentials.json" in path for path in manifest["denied_paths"])
    assert any("api_token.txt" in path for path in manifest["denied_paths"])
    assert not any("credentials" in str(item["path"]) for item in manifest["files"])
    assert not any("_token" in str(item["path"]) for item in manifest["files"])


@pytest.mark.parametrize(
    "relative_path",
    [
        ".ce/briefs/.env.production",
        ".ce/briefs/secrets/api.json",
        ".ce/briefs/.ssh/config",
        ".ce/briefs/id_ed25519",
        ".ce/briefs/.netrc",
        ".ce/briefs/client.p12",
    ],
)
def test_shared_secret_path_shapes_are_denied(tmp_path, relative_path):
    _seed(tmp_path / relative_path)

    manifest = controller_state_sync.collect_manifest(tmp_path)

    assert relative_path in manifest["denied_paths"]
    assert relative_path not in {str(item["path"]) for item in manifest["files"]}


@pytest.mark.parametrize(
    "relative_path",
    [
        ".ce/briefs/.envrc",
        ".ce/briefs/id_ed25519.pub",
        ".ce/briefs/client.p12.txt",
        ".ce/briefs/.ssh-guide.md",
    ],
)
def test_secret_path_safe_neighbors_remain_collectable(tmp_path, relative_path):
    _seed(tmp_path / relative_path)

    manifest = controller_state_sync.collect_manifest(tmp_path)

    assert relative_path not in manifest["denied_paths"]
    assert relative_path in {str(item["path"]) for item in manifest["files"]}


def test_in_repo_file_symlink_is_denied(tmp_path):
    target = _seed(tmp_path / "private/controller-notes.md")
    link = tmp_path / ".ce/briefs/controller-notes.md"
    link.parent.mkdir(parents=True)
    link.symlink_to(target)

    manifest = _commit_manifest(tmp_path)

    assert ".ce/briefs/controller-notes.md" in manifest["denied_paths"]
    assert not (tmp_path / "out/dispatch_briefs/controller-notes.md").exists()


def test_external_file_symlink_is_denied(tmp_path, tmp_path_factory):
    external = _seed(tmp_path_factory.mktemp("external") / "notes.md")
    link = tmp_path / ".ce/claims/notes.md"
    link.parent.mkdir(parents=True)
    link.symlink_to(external)

    manifest = _commit_manifest(tmp_path)

    assert ".ce/claims/notes.md" in manifest["denied_paths"]
    assert not (tmp_path / "out/dispatch_claims/notes.md").exists()


def test_directory_symlink_is_denied_without_traversal(tmp_path, tmp_path_factory):
    external = tmp_path_factory.mktemp("external-directory")
    _seed(external / "nested.md")
    link = tmp_path / ".ce/briefs/linked"
    link.parent.mkdir(parents=True)
    link.symlink_to(external, target_is_directory=True)

    manifest = _commit_manifest(tmp_path)

    assert ".ce/briefs/linked" in manifest["denied_paths"]
    assert not (tmp_path / "out/dispatch_briefs/linked").exists()


def test_dry_run_default_writes_nothing(tmp_path):
    _seed(tmp_path / ".ce/state/research/foo.md")
    out = tmp_path / "out"

    rc = controller_state_sync.main(
        ["--source-root", str(tmp_path), "--output-dir", str(out)]
    )

    assert rc == 0
    assert not out.exists() or not any(out.iterdir())


def test_manifest_fields_present(tmp_path):
    _seed(tmp_path / ".ce/state/research/foo.md")

    manifest = _commit_manifest(tmp_path)

    assert set(manifest) >= {
        "schema_version",
        "snapshot_at",
        "source_host",
        "source_root",
        "files",
        "denied_paths",
        "restore_steps",
    }


def test_restore_steps_is_nonempty_list(tmp_path):
    manifest = _commit_manifest(tmp_path)

    assert isinstance(manifest["restore_steps"], list)
    assert len(manifest["restore_steps"]) >= 3


def test_arc_state_collected(tmp_path):
    _seed(tmp_path / ".ce/state/research/RESUME_STATE_foo.md")

    manifest = _commit_manifest(tmp_path)

    assert any(
        item["path"] == ".ce/state/research/RESUME_STATE_foo.md"
        for item in manifest["files"]
    )
    assert (tmp_path / "out/arc_state/RESUME_STATE_foo.md").is_file()


def test_briefs_collected(tmp_path):
    _seed(tmp_path / ".ce/briefs/BRIEF_foo.md")

    manifest = _commit_manifest(tmp_path)

    assert any(item["path"] == ".ce/briefs/BRIEF_foo.md" for item in manifest["files"])
    assert (tmp_path / "out/dispatch_briefs/BRIEF_foo.md").is_file()


def test_claims_collected(tmp_path):
    _seed(tmp_path / ".ce/claims/claim.md")

    manifest = _commit_manifest(tmp_path)

    assert any(item["path"] == ".ce/claims/claim.md" for item in manifest["files"])
    assert (tmp_path / "out/dispatch_claims/claim.md").is_file()


def test_claude_agents_collected(tmp_path):
    _seed(tmp_path / ".claude/agents/implementer.md", "role\n")

    manifest = _commit_manifest(tmp_path)

    assert "claude_agents" in manifest["data_classes"]
    assert any(
        item["path"] == ".claude/agents/implementer.md"
        for item in manifest["files"]
    )
    assert (tmp_path / "out/claude_agents/implementer.md").is_file()


def test_missing_claude_agents_dir_yields_warning_not_error(tmp_path, capsys):
    out = tmp_path / "out"

    rc = controller_state_sync.main(
        ["--source-root", str(tmp_path), "--commit", "--output-dir", str(out)]
    )

    captured = capsys.readouterr()
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert rc == 0
    assert "warning: missing source for claude_agents" in captured.err
    assert "claude_agents" in manifest["missing_sources"]
    assert not (out / "claude_agents").exists()


def test_missing_source_dir_yields_warning_not_error(tmp_path, capsys):
    out = tmp_path / "out"

    rc = controller_state_sync.main(
        ["--source-root", str(tmp_path), "--commit", "--output-dir", str(out)]
    )

    captured = capsys.readouterr()
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert rc == 0
    assert "warning: missing source" in captured.err
    assert "missing_sources" in manifest


def test_sha256_in_manifest_per_file(tmp_path):
    _seed(tmp_path / ".ce/state/research/foo.md", "known\n")

    manifest = _commit_manifest(tmp_path)

    sha = manifest["files"][0]["sha256"]
    assert len(sha) == 64
    assert all(char in "0123456789abcdef" for char in sha)


def test_include_memory_flag_adds_memory_class(tmp_path):
    memory_root = tmp_path / "memory"
    _seed(memory_root / "MEMORY.md")

    manifest = _commit_manifest(
        tmp_path,
        "--include-memory",
        "--memory-root",
        str(memory_root),
    )

    assert "memory" in manifest["data_classes"]
    assert any(item["path"] == "memory/MEMORY.md" for item in manifest["files"])
    assert (tmp_path / "out/memory.tar.gz").is_file()


def test_nonempty_output_is_refused_without_reusing_stale_payload(tmp_path, capsys):
    _seed(tmp_path / ".ce/state/research/current.md")
    stale = _seed(tmp_path / "out/memory.tar.gz", "stale\n")

    rc = controller_state_sync.main(
        ["--repo-root", str(tmp_path), "--commit", "--output-dir", str(tmp_path / "out")]
    )

    assert rc == 1
    assert "refused non-empty output directory" in capsys.readouterr().err
    assert stale.read_text(encoding="utf-8") == "stale\n"
    assert not (tmp_path / "out/manifest.json").exists()


def test_source_mutation_after_collection_refuses_publication(tmp_path):
    source = _seed(tmp_path / ".ce/state/research/state.md", "before\n")
    manifest = controller_state_sync.collect_manifest(tmp_path)
    source.write_text("after\n", encoding="utf-8")
    out = tmp_path / "out"

    with pytest.raises(
        controller_state_sync.SnapshotError,
        match="changed between collection and publication",
    ):
        controller_state_sync.write_snapshot(manifest, out, tmp_path)

    assert not out.exists()


def test_source_ancestor_swap_refuses_without_external_read(
    tmp_path, tmp_path_factory, monkeypatch
):
    source = tmp_path / ".ce/state"
    _seed(source / "research/state.md", "trusted\n")
    manifest = controller_state_sync.collect_manifest(tmp_path)

    pinned_source = tmp_path / ".ce/state-pinned"
    source.rename(pinned_source)
    external = tmp_path_factory.mktemp("external-source")
    external_file = _seed(external / "research/state.md", "external-secret\n")
    source.symlink_to(external, target_is_directory=True)
    _forbid_descriptor_opens_below(monkeypatch, external)

    out = tmp_path / "out"
    with pytest.raises(controller_state_sync.SnapshotError, match="ancestor"):
        controller_state_sync.write_snapshot(manifest, out, tmp_path)

    assert external_file.read_text(encoding="utf-8") == "external-secret\n"
    assert not out.exists()
    assert not any(path.name == "manifest.json" for path in pinned_source.rglob("*"))


def test_memory_ancestor_swap_refuses_without_external_read(
    tmp_path, tmp_path_factory, monkeypatch
):
    memory_root = tmp_path / "memory"
    memory_parent = memory_root / "project"
    _seed(memory_parent / "MEMORY.md", "trusted-memory\n")
    manifest = controller_state_sync.collect_manifest(
        tmp_path, include_memory=True, memory_root=memory_root
    )

    pinned_memory = memory_root / "project-pinned"
    memory_parent.rename(pinned_memory)
    external = tmp_path_factory.mktemp("external-memory")
    external_file = _seed(external / "MEMORY.md", "external-memory-secret\n")
    memory_parent.symlink_to(external, target_is_directory=True)
    _forbid_descriptor_opens_below(monkeypatch, external)

    out = tmp_path / "out"
    with pytest.raises(controller_state_sync.SnapshotError, match="ancestor"):
        controller_state_sync.write_snapshot(
            manifest,
            out,
            tmp_path,
            include_memory=True,
            memory_root=memory_root,
        )

    assert external_file.read_text(encoding="utf-8") == "external-memory-secret\n"
    assert not out.exists()


def test_static_output_parent_symlink_refuses_without_external_write(
    tmp_path, tmp_path_factory, monkeypatch
):
    _seed(tmp_path / ".ce/state/research/state.md")
    manifest = controller_state_sync.collect_manifest(tmp_path)
    external = tmp_path_factory.mktemp("external-output")
    output_parent = tmp_path / "linked-output"
    output_parent.symlink_to(external, target_is_directory=True)
    _forbid_descriptor_opens_below(monkeypatch, external)

    with pytest.raises(controller_state_sync.SnapshotError, match="path component"):
        controller_state_sync.write_snapshot(
            manifest, output_parent / "snapshot", tmp_path
        )

    assert not any(external.iterdir())
    assert not (external / "snapshot/manifest.json").exists()


def test_output_parent_swap_before_rename_refuses_without_external_write(
    tmp_path, tmp_path_factory, monkeypatch
):
    _seed(tmp_path / ".ce/state/research/state.md")
    manifest = controller_state_sync.collect_manifest(tmp_path)
    output_parent = tmp_path / "output-parent"
    output_parent.mkdir()
    pinned_parent = tmp_path / "output-parent-pinned"
    external = tmp_path_factory.mktemp("external-output-swap")
    original_verify = controller_state_sync._verify_pinned_directory
    swapped = False

    def swap_then_verify(path, descriptor):
        nonlocal swapped
        assert not swapped
        swapped = True
        output_parent.rename(pinned_parent)
        output_parent.symlink_to(external, target_is_directory=True)
        return original_verify(path, descriptor)

    monkeypatch.setattr(
        controller_state_sync, "_verify_pinned_directory", swap_then_verify
    )

    with pytest.raises(controller_state_sync.SnapshotError, match="parent changed"):
        controller_state_sync.write_snapshot(
            manifest, output_parent / "snapshot", tmp_path
        )

    assert swapped
    assert not any(external.iterdir())
    assert not (external / "snapshot/manifest.json").exists()
    assert not any(pinned_parent.iterdir())


def test_publication_copies_only_files_recorded_in_manifest(tmp_path):
    _seed(tmp_path / ".ce/state/research/recorded.md")
    manifest = controller_state_sync.collect_manifest(tmp_path)
    _seed(tmp_path / ".ce/state/research/late.md")

    controller_state_sync.write_snapshot(manifest, tmp_path / "out", tmp_path)

    assert (tmp_path / "out/arc_state/recorded.md").is_file()
    assert not (tmp_path / "out/arc_state/late.md").exists()


def test_repo_derived_memory_root_and_portable_restore_steps(tmp_path):
    repo_root = tmp_path / "non-default-repo"
    home = tmp_path / "non-default-home"

    derived = controller_state_sync.default_memory_root(repo_root, home=home)

    assert derived == (
        home
        / ".claude"
        / "projects"
        / repo_root.resolve().as_posix().replace("/", "-")
        / "memory"
    )

    memory_root = tmp_path / "custom-memory"
    _seed(repo_root / ".ce/state/research/state.md")
    _seed(memory_root / "MEMORY.md")
    out = tmp_path / "portable-out"
    rc = controller_state_sync.main(
        [
            "--repo-root",
            str(repo_root),
            "--memory-root",
            str(memory_root),
            "--include-memory",
            "--commit",
            "--output-dir",
            str(out),
        ]
    )
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    restore_text = "\n".join(manifest["restore_steps"])

    assert rc == 0
    assert manifest["memory_root"] == str(memory_root.resolve())
    assert manifest["memory_root_source"] == "override"
    assert "<replacement-repo-root>" in restore_text
    assert "<replacement-memory-root>" in restore_text
    assert str(repo_root) not in restore_text
    assert str(memory_root) not in restore_text


def test_manifest_only_writes_nothing(tmp_path):
    _seed(tmp_path / ".ce/state/research/foo.md")
    out = tmp_path / "out"

    rc = controller_state_sync.main(
        [
            "--source-root",
            str(tmp_path),
            "--commit",
            "--manifest-only",
            "--output-dir",
            str(out),
        ]
    )

    assert rc == 0
    assert not out.exists()

"""Hermetic contracts for the policy-bound Codex one-shot launcher."""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import replace
from pathlib import Path
import shutil
import subprocess
import tomllib

import pytest
import yaml

from creator_engine_validator import codex_worker_launcher as launcher
from creator_engine_validator import ce_cli


REPO_ROOT = Path(__file__).resolve().parents[3]
POLICY_PATH = REPO_ROOT / "governance" / "policies" / "codex-one-shot-launch-v1.yaml"
RUNTIME_POLICY_PATH = REPO_ROOT / "governance" / "policies" / "runtime" / "default-controller-v1.yaml"
PINNED_BINARY = "/opt/creator-engine/codex/0.145.0-alpha.9/bin/codex"
NON_IMPLEMENTER_MATRIX_MUTATIONS = [
    (venue, role, "workspace-write" if sandbox == "read-only" else "read-only")
    for venue, values in {
        "dgx-relay": {
            "architect_research": "read-only",
            "reviewer": "read-only",
            "verification": "read-only",
        },
        "dev1-local": {
            "architect_research": "read-only",
            "reviewer": "read-only",
            "verification": "read-only",
        },
        "vps-tmux": {"architect_research": None, "reviewer": None, "verification": None},
        "in-seat": {"architect_research": None, "reviewer": None, "verification": None},
    }.items()
    for role, sandbox in values.items()
]
MALFORMED_BINARY_TEMPLATES = [
    "/opt/creator-engine/codex/{version}/{0}/codex",
    "/opt/creator-engine/codex/{version.real}/bin/codex",
    "/opt/creator-engine/codex/{version[0]}/bin/codex",
    "/opt/creator-engine/codex/{version!r}/bin/codex",
    "/opt/creator-engine/codex/{version:>20}/bin/codex",
    "/opt/creator-engine/codex/{version}/{other}/codex",
]
NON_STRING_BINARY_TEMPLATES = [None, 17, False, ["{version}"], {"field": "version"}]
EXACT_ONLY_SENSITIVE_ENV_NAMES = [
    "AWS_ACCESS_KEY_ID",
    "GITHUB_API_URL",
    "GH_HOST",
    "GH_CONFIG_DIR",
    "GH_DEBUG",
    "GIT_ASKPASS",
    "SSH_ASKPASS",
    "GPG_AGENT_INFO",
]
PREFIXED_EXACT_ONLY_SENSITIVE_ENV_NAMES = [
    f"{prefix}{name}"
    for name in EXACT_ONLY_SENSITIVE_ENV_NAMES
    for prefix in ("LC_", "LC_LC_", "LC_LC_LC_")
]
CANONICAL_ADD_DIR_ALIASES = ["./governance", "governance/.", "governance//"]
AMBIENT_FOREMAN_BOOTSTRAP = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")


class HermeticFilesystem(launcher.RealLauncherFilesystem):
    def __init__(
        self,
        *,
        binary_exists: bool = True,
        binary_executable: bool = True,
        binary_realpath: str = PINNED_BINARY,
    ) -> None:
        self.binary_exists = binary_exists
        self.binary_executable = binary_executable
        self.binary_realpath = binary_realpath

    def realpath(self, path: str) -> str:
        if os.path.normpath(path) == PINNED_BINARY:
            return self.binary_realpath
        return super().realpath(path)

    def is_file(self, path: str) -> bool:
        if os.path.normpath(path) in {PINNED_BINARY, self.binary_realpath}:
            return self.binary_exists
        return super().is_file(path)

    def is_executable(self, path: str) -> bool:
        if os.path.normpath(path) in {PINNED_BINARY, self.binary_realpath}:
            return self.binary_executable
        return super().is_executable(path)


class FixedVersionProbe:
    def __init__(self, version: str = "0.145.0-alpha.9") -> None:
        self.version = version
        self.calls: list[str] = []

    def probe(self, binary: str) -> str:
        self.calls.append(binary)
        return self.version


class UnusedFilesystem:
    def __getattr__(self, name: str):
        pytest.fail(f"filesystem method used before binary-template refusal: {name}")


class RecordingRunner:
    def __init__(self) -> None:
        self.calls: list[tuple[tuple[str, ...], bytes]] = []

    def run(self, argv, *, stdin: bytes, provider_credential_env_names) -> int:
        self.calls.append((tuple(argv), stdin))
        assert tuple(provider_credential_env_names) == ("OPENAI_API_KEY",)
        return 0


class HermeticLeafCodex:
    """Small deterministic stand-in for leaf behavior; never starts Codex."""

    def run(self, argv, *, stdin: bytes, provider_credential_env_names=()) -> int:
        configs = [
            item.removeprefix("developer_instructions=")
            for item in argv
            if item.startswith("developer_instructions=")
        ]
        assert len(configs) == 1
        envelope = tomllib.loads(f"value={configs[0]}")["value"]
        fields = dict(
            line.split(": ", 1)
            for line in envelope.splitlines()
            if ": " in line
        )
        assert fields["seat_class"] == "worker"
        assert fields["nested_delegation"] == "disabled"
        assert fields["parent_lineage"] == "provenance_only_no_inherited_authority"
        assert "controller_or_foreman_authority" in fields["prohibitions"]
        assert "nested_spawn" in fields["prohibitions"]
        request = stdin.decode("utf-8")
        if any(
            marker in request
            for marker in (
                "become FOREMAN",
                "spawn a sub-agent",
                "approve the PR",
                "enqueue the PR",
                "merge the PR",
                "sign the commit",
                "use controller credentials",
                "fall back to FOREMAN",
            )
        ):
            return 64

        worktree = Path(argv[argv.index("-C") + 1])
        role = fields["role"]
        if role == "implementer":
            assert fields["capability"] == "scoped_worktree_edit_test_commit"
            assert fields["sandbox"] == "workspace-write"
            target = worktree / "bounded-result.txt"
            target.write_text("direct leaf implementation\n", encoding="utf-8")
            subprocess.run(
                [
                    "/usr/bin/python3",
                    "-c",
                    "from pathlib import Path; assert Path('bounded-result.txt').read_text() == 'direct leaf implementation\\n'",
                ],
                cwd=worktree,
                check=True,
            )
            subprocess.run(["git", "add", "bounded-result.txt"], cwd=worktree, check=True)
            subprocess.run(
                [
                    "git",
                    "-c",
                    "commit.gpgsign=false",
                    "-c",
                    "user.name=Hermetic Leaf",
                    "-c",
                    "user.email=leaf@example.invalid",
                    "commit",
                    "-q",
                    "-m",
                    "test: direct governed implementer behavior",
                ],
                cwd=worktree,
                check=True,
            )
        else:
            assert fields["sandbox"] == "read-only"
            subprocess.run(["git", "diff", "--check"], cwd=worktree, check=True)
        return 0


def _hermetic_leaf_argv(
    worker_input: launcher.GovernedWorkerInput,
    *,
    worktree: Path,
    sandbox: str,
) -> tuple[str, ...]:
    envelope = launcher.build_governed_role_envelope(
        governed_input=worker_input,
        worktree=str(worktree),
        sandbox=sandbox,
    )
    return (
        "/hermetic/fake-codex",
        "exec",
        "--strict-config",
        "-c",
        "features.multi_agent=false",
        "-c",
        f"developer_instructions={launcher.toml_encode_config_value(envelope)}",
        "-s",
        sandbox,
        "-C",
        str(worktree),
        "-",
    )


HERMETIC_CODEX_EXECUTABLE = r'''#!/usr/bin/python3
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tomllib

argv = sys.argv[1:]
assert "HOSTILE_AMBIENT" not in os.environ
assert Path(os.environ["HOME"]).parent == Path(os.environ["CODEX_HOME"]).parent
assert argv[:5] == ["exec", "--strict-config", "--ephemeral", "-m", "gpt-5.6-terra"]
index = 5
configs = []
while argv[index] == "-c":
    configs.append(argv[index + 1])
    index += 2
assert len(configs) == 4
assert configs[:3] == [
    "model_reasoning_effort=high",
    "features.multi_agent=false",
    "features.multi_agent_v2=false",
]
assert configs[3].startswith("developer_instructions=")
envelope = tomllib.loads("value=" + configs[3].split("=", 1)[1])["value"]
fields = dict(line.split(": ", 1) for line in envelope.splitlines() if ": " in line)
assert argv[index] == "-s"
sandbox = argv[index + 1]
index += 2
assert argv[index] == "-C"
worktree = Path(argv[index + 1])
index += 2
add_dirs = []
while argv[index] == "--add-dir":
    add_dirs.append(argv[index + 1])
    index += 2
assert add_dirs == [str(worktree / "governance"), str(worktree / "validators")]
assert argv[index] == "-o"
output = Path(argv[index + 1])
assert argv[index + 2:] == ["-"]
brief = sys.stdin.buffer.read()
role_policy = worktree / fields["role_policy_path"]
assert hashlib.sha256(role_policy.read_bytes()).hexdigest() == fields["role_policy_sha256"]
assert hashlib.sha256(brief).hexdigest() == fields["brief_sha256"]
assert fields["seat_class"] == "worker"
assert fields["nested_delegation"] == "disabled"
assert fields["parent_lineage"] == "provenance_only_no_inherited_authority"
assert "controller_or_foreman_authority" in fields["prohibitions"]
assert "nested_spawn" in fields["prohibitions"]
request = brief.decode("utf-8")
refused = any(marker in request for marker in (
    "become FOREMAN",
    "spawn a sub-agent",
    "approve the PR",
    "enqueue the PR",
    "merge the PR",
    "sign the commit",
    "use controller credentials",
    "fall back to FOREMAN",
))
before = subprocess.run(
    ["git", "rev-parse", "HEAD"], cwd=worktree, check=True,
    capture_output=True, text=True,
).stdout.strip()
if not refused and fields["role"] == "implementer":
    assert sandbox == "workspace-write"
    target = worktree / "bounded-result.txt"
    target.write_text("direct leaf implementation\n", encoding="utf-8")
    assert target.read_text(encoding="utf-8") == "direct leaf implementation\n"
    subprocess.run(["git", "add", "bounded-result.txt"], cwd=worktree, check=True)
    subprocess.run([
        "git", "-c", "commit.gpgsign=false", "-c", "user.name=Hermetic Leaf",
        "-c", "user.email=leaf@example.invalid", "commit", "-q", "-m",
        "test: direct governed implementer behavior",
    ], cwd=worktree, check=True)
elif not refused:
    assert sandbox == "read-only"
after = subprocess.run(
    ["git", "rev-parse", "HEAD"], cwd=worktree, check=True,
    capture_output=True, text=True,
).stdout.strip()
output.write_text(json.dumps({
    "role": fields["role"],
    "sandbox": sandbox,
    "stdin_sha256": hashlib.sha256(brief).hexdigest(),
    "strict_config": True,
    "multi_agent_disabled": configs[1:3] == [
        "features.multi_agent=false", "features.multi_agent_v2=false"
    ],
    "refused": refused,
    "head_changed": before != after,
    "write_denied": not refused and fields["role"] != "implementer",
}), encoding="utf-8")
raise SystemExit(64 if refused else 0)
'''


def _write_hermetic_codex_executable(worktree: Path) -> Path:
    binary = worktree.parent / "hermetic-codex" / "0.145.0-alpha.9" / "bin" / "codex"
    binary.parent.mkdir(parents=True)
    binary.write_text(HERMETIC_CODEX_EXECUTABLE, encoding="utf-8")
    binary.chmod(0o755)
    return binary


def _hermetic_subprocess_policy(
    worktree: Path,
    *,
    binary: Path,
    role: str,
    monkeypatch,
) -> launcher.CodexOneShotPolicy:
    loaded = policy(worktree)
    template = str(binary).replace(loaded.version, "{version}")

    def stage_hermetic_policy(raw) -> None:
        for venue_policy in raw["venues"].values():
            venue_policy["codex_binary_template"] = template
        if role == "implementer":
            raw["venues"]["dev1-local"]["outer_isolation_attestation"] = (
                "hermetic disposable worktree"
            )
            raw["venues"]["dev1-local"]["role_sandboxes"]["implementer"] = (
                "workspace-write"
            )

    rewrite_policy(worktree, stage_hermetic_policy)
    if role == "implementer":
        trusted_matrix = tuple(
            (
                venue,
                tuple(
                    (
                        candidate,
                        "workspace-write"
                        if venue == "dev1-local" and candidate == "implementer"
                        else sandbox,
                    )
                    for candidate, sandbox in cells
                ),
            )
            for venue, cells in launcher.V1_ROLE_SANDBOX_MATRIX
        )
        monkeypatch.setattr(launcher, "V1_ROLE_SANDBOX_MATRIX", trusted_matrix)
    return policy(worktree)


@pytest.fixture
def worktree(tmp_path: Path, request, monkeypatch) -> Path:
    root = tmp_path / "allocated-worker"
    (root / "governance" / "policies").mkdir(parents=True)
    shutil.copy2(POLICY_PATH, root / "governance" / "policies" / POLICY_PATH.name)
    (root / "governance" / "policies" / "runtime").mkdir()
    shutil.copy2(
        RUNTIME_POLICY_PATH,
        root / "governance" / "policies" / "runtime" / RUNTIME_POLICY_PATH.name,
    )
    (root / "validators").mkdir()
    (root / ".claude" / "agents").mkdir(parents=True)
    for role in ("architect_research", "implementer", "reviewer", "verification"):
        (root / ".claude" / "agents" / f"{role}.md").write_bytes(
            f"# Canonical {role}\nexact policy bytes\n".encode()
        )
    (root / ".ce" / "briefs").mkdir(parents=True)
    (root / ".ce" / "state").mkdir()
    if getattr(request.node, "originalname", request.node.name) != (
        "test_canonical_runtime_floor_refuses_every_role_venue_before_probe"
    ):
        # Legacy argv/TOCTOU tests need a reachable baseline to exercise their
        # downstream mechanics. Create an unmistakably non-production,
        # tmp-root-only post-migration fixture; tracked policy bytes and the
        # production venue floor remain exact and are tested separately.
        registry = root / "governance" / "policies" / POLICY_PATH.name
        raw = yaml.safe_load(registry.read_text(encoding="utf-8"))
        raw["runtime_policy_binding"]["allowed_venues"] = [
            "vps-tmux",
            "in-seat",
            "dev1-local",
        ]
        registry.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
        monkeypatch.setattr(
            launcher,
            "V1_RUNTIME_POLICY_ALLOWED_VENUES",
            ("vps-tmux", "in-seat", "dev1-local"),
        )
    stage_runtime_policy(root)
    return root


def stage_runtime_policy(worktree: Path) -> None:
    raw = yaml.safe_load(
        (worktree / "governance" / "policies" / POLICY_PATH.name).read_text(encoding="utf-8")
    )
    binding = raw["runtime_policy_binding"]
    source = worktree / binding["source_path"]
    runtime_dir = worktree / ".ce" / "state" / "onboard" / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    local = worktree / binding["local_policy_relative_path"]
    local.write_bytes(source.read_bytes())
    local.chmod(0o600)
    registry = worktree / launcher.CANONICAL_POLICY_RELATIVE_PATH
    receipt = {
        "canonical_source_path": binding["source_path"],
        "canonical_source_sha256": binding["source_sha256"],
        "kind": launcher.RUNTIME_RECEIPT_KIND,
        "local_policy_relative_path": binding["local_policy_relative_path"],
        "policy_id": binding["policy_id"],
        "policy_sha": binding["policy_sha"],
        "registry_path": launcher.CANONICAL_POLICY_RELATIVE_PATH,
        "registry_sha256": hashlib.sha256(registry.read_bytes()).hexdigest(),
        "rendered_sha256": binding["source_sha256"],
        "schema_version": "1",
    }
    receipt_path = worktree / binding["local_receipt_relative_path"]
    receipt_path.write_text(
        json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    receipt_path.chmod(0o600)


def policy(worktree: Path) -> launcher.CodexOneShotPolicy:
    return launcher.load_canonical_policy(worktree, filesystem=HermeticFilesystem())


def rewrite_policy(worktree: Path, mutate) -> None:
    path = worktree / "governance" / "policies" / POLICY_PATH.name
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    mutate(raw)
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    stage_runtime_policy(worktree)


def governed_input(
    worktree: Path,
    *,
    role: str = "implementer",
    brief_path: Path | None = None,
    brief_sha256: str | None = None,
) -> launcher.GovernedWorkerInput:
    brief = brief_path or (worktree / ".ce" / "briefs" / "task.md")
    if brief_path is None:
        brief.write_bytes(b"perform the bounded task\n")
    digest = brief_sha256 or hashlib.sha256(brief.read_bytes()).hexdigest()
    return launcher.load_governed_worker_input(
        worktree=str(worktree),
        role=role,
        brief_path=str(brief),
        brief_sha256=digest,
        filesystem=HermeticFilesystem(),
    )


def plan(worktree: Path, **overrides) -> launcher.CodexWorkerLaunchPlan:
    values = {
        "policy": policy(worktree),
        "governed_input": governed_input(worktree, role="architect_research"),
        "role": "architect_research",
        "venue": "dev1-local",
        "worktree": str(worktree),
        "run_id": "test-run",
        "filesystem": HermeticFilesystem(),
        "version_probe": FixedVersionProbe(),
    }
    values.update(overrides)
    request = launcher.build_launch_request(
        policy=values["policy"],
        governed_input=values["governed_input"],
        role=values.pop("role"),
        venue=values.pop("venue"),
        worktree=values.pop("worktree"),
        run_id=values.pop("run_id"),
        filesystem=values["filesystem"],
    )
    return launcher.build_launch_plan(request=request, **values)


def launch_request_from_plan(
    built: launcher.CodexWorkerLaunchPlan,
) -> launcher.CodexWorkerLaunchRequest:
    """Recover the separately held immutable request used by test callers."""
    return launcher.CodexWorkerLaunchRequest(
        role=built.role,
        venue=built.venue,
        worktree=built.worktree,
        seat_repo_root=built.seat_repo_root,
        run_id=built.run_id,
    )


def test_canonical_policy_pins_deployment_version_and_actual_venues(worktree: Path) -> None:
    loaded = policy(worktree)
    assert loaded.version == "0.145.0-alpha.9"
    assert set(loaded.venue_names) == {"dgx-relay", "vps-tmux", "dev1-local", "in-seat"}
    assert loaded.provider_credentials_for("architect_research") == ("OPENAI_API_KEY",)
    assert loaded.provider_credentials_for("implementer") == ("OPENAI_API_KEY",)
    assert loaded.provider_credentials_for("reviewer") == ()
    assert loaded.provider_credentials_for("verification") == ()


@pytest.mark.parametrize("venue", launcher.V1_VENUES)
@pytest.mark.parametrize("role", launcher.V1_SUPPORTED_ROLES)
def test_canonical_runtime_floor_refuses_every_role_venue_before_probe(
    worktree: Path, venue: str, role: str
) -> None:
    loaded = policy(worktree)
    worker_input = governed_input(worktree, role=role)
    probe = FixedVersionProbe()
    runner = RecordingRunner()
    with pytest.raises(launcher.CodexWorkerLaunchError):
        built = launcher.build_launch_plan(
            policy=loaded,
            governed_input=worker_input,
            role=role,
            venue=venue,
            worktree=str(worktree),
            run_id=f"strict-floor-{venue}-{role}",
            filesystem=HermeticFilesystem(),
            version_probe=probe,
        )
        launcher.launch(
            built,
            request=launch_request_from_plan(built),
            governed_input=worker_input,
            runner=runner,
            filesystem=HermeticFilesystem(),
        )
    assert probe.calls == []
    assert runner.calls == []


@pytest.mark.parametrize(
    ("venue", "role", "sandbox"),
    [
        (venue, role, sandbox)
        for venue, values in {
            "dgx-relay": {
                "architect_research": "read-only",
                "implementer": None,
                "reviewer": "read-only",
                "verification": "read-only",
            },
            "dev1-local": {
                "architect_research": "read-only",
                "implementer": None,
                "reviewer": "read-only",
                "verification": "read-only",
            },
            "vps-tmux": {
                "architect_research": None,
                "implementer": None,
                "reviewer": None,
                "verification": None,
            },
            "in-seat": {
                "architect_research": None,
                "implementer": None,
                "reviewer": None,
                "verification": None,
            },
        }.items()
        for role, sandbox in values.items()
    ],
)
def test_role_venue_matrix_is_complete_and_fail_closed(
    worktree: Path, venue: str, role: str, sandbox: str | None
) -> None:
    loaded = policy(worktree)
    if sandbox is None:
        with pytest.raises(launcher.CodexWorkerLaunchError, match="not attested"):
            loaded.sandbox_for(role=role, venue=venue)
    else:
        assert loaded.sandbox_for(role=role, venue=venue) == sandbox


@pytest.mark.parametrize("venue", ["dgx-relay", "vps-tmux", "dev1-local", "in-seat"])
@pytest.mark.parametrize("sandbox", ["workspace-write", "danger-full-access"])
def test_policy_parser_refuses_every_non_null_v1_implementer_sandbox(
    worktree: Path, venue: str, sandbox: str
) -> None:
    def mutate(raw) -> None:
        raw["venues"][venue]["role_sandboxes"]["implementer"] = sandbox
        if sandbox == "danger-full-access":
            raw["venues"][venue]["outer_isolation_attestation"] = "caller-claimed"

    rewrite_policy(worktree, mutate)
    with pytest.raises(launcher.CodexWorkerLaunchError, match="v1 implementer.*must be null"):
        policy(worktree)


@pytest.mark.parametrize(("venue", "role", "sandbox"), NON_IMPLEMENTER_MATRIX_MUTATIONS)
def test_policy_parser_refuses_every_mutated_non_implementer_v1_matrix_cell(
    worktree: Path, venue: str, role: str, sandbox: str
) -> None:
    rewrite_policy(
        worktree,
        lambda raw: raw["venues"][venue]["role_sandboxes"].__setitem__(role, sandbox),
    )
    with pytest.raises(launcher.CodexWorkerLaunchError, match="exact trusted matrix"):
        policy(worktree)


@pytest.mark.parametrize("mutation", ["add", "replace", "remove"])
def test_policy_parser_refuses_mutated_v1_venue_set(worktree: Path, mutation: str) -> None:
    def mutate(raw) -> None:
        if mutation == "add":
            raw["venues"]["caller-relay"] = dict(raw["venues"]["dgx-relay"])
        elif mutation == "replace":
            raw["venues"]["caller-relay"] = raw["venues"].pop("dgx-relay")
        else:
            raw["venues"].pop("dgx-relay")

    rewrite_policy(worktree, mutate)
    with pytest.raises(launcher.CodexWorkerLaunchError, match="exact v1 venue"):
        policy(worktree)


@pytest.mark.parametrize("mutation", ["add", "replace", "remove"])
def test_policy_parser_refuses_mutated_v1_supported_role_set(
    worktree: Path, mutation: str
) -> None:
    def mutate(raw) -> None:
        roles = raw["supported_roles"]
        if mutation == "add":
            roles.append("operator")
        elif mutation == "replace":
            roles[roles.index("reviewer")] = "operator"
        else:
            roles.remove("reviewer")

    rewrite_policy(worktree, mutate)
    with pytest.raises(launcher.CodexWorkerLaunchError, match="exact v1 supported-role"):
        policy(worktree)


@pytest.mark.parametrize("template", MALFORMED_BINARY_TEMPLATES)
def test_policy_parser_refuses_structurally_malformed_binary_template(
    worktree: Path, template: str
) -> None:
    rewrite_policy(
        worktree,
        lambda raw: raw["venues"]["dev1-local"].__setitem__(
            "codex_binary_template", template
        ),
    )
    with pytest.raises(launcher.CodexWorkerLaunchError, match="binary template"):
        policy(worktree)


@pytest.mark.parametrize("sandbox", ["workspace-write", "danger-full-access"])
def test_planner_revalidates_trusted_v1_implementer_refusal_before_version_probe(
    worktree: Path, sandbox: str
) -> None:
    loaded = policy(worktree)
    venue = loaded.venue("dev1-local")
    unsafe_matrix = tuple(
        (role, sandbox if role == "implementer" else value)
        for role, value in venue.role_sandboxes
    )
    unsafe_venue = replace(
        venue,
        outer_isolation_attestation=("caller-claimed" if sandbox == "danger-full-access" else None),
        role_sandboxes=unsafe_matrix,
    )
    unsafe_policy = replace(
        loaded,
        venues=tuple(unsafe_venue if item.name == venue.name else item for item in loaded.venues),
    )
    probe = FixedVersionProbe()
    with pytest.raises(launcher.CodexWorkerLaunchError, match="exact trusted matrix"):
        launcher.build_launch_plan(
            policy=unsafe_policy,
            governed_input=governed_input(worktree, role="implementer"),
            role="implementer",
            venue="dev1-local",
            worktree=str(worktree),
            filesystem=HermeticFilesystem(),
            version_probe=probe,
        )
    assert probe.calls == []


@pytest.mark.parametrize(("venue_name", "role", "sandbox"), NON_IMPLEMENTER_MATRIX_MUTATIONS)
def test_planner_revalidates_every_non_implementer_v1_matrix_cell_before_version_probe(
    worktree: Path, venue_name: str, role: str, sandbox: str
) -> None:
    loaded = policy(worktree)
    venue = loaded.venue(venue_name)
    unsafe_venue = replace(
        venue,
        role_sandboxes=tuple(
            (candidate, sandbox if candidate == role else value)
            for candidate, value in venue.role_sandboxes
        ),
    )
    unsafe_policy = replace(
        loaded,
        venues=tuple(unsafe_venue if item.name == venue.name else item for item in loaded.venues),
    )
    probe = FixedVersionProbe()
    with pytest.raises(launcher.CodexWorkerLaunchError, match="exact trusted matrix"):
        launcher.build_launch_plan(
            policy=unsafe_policy,
            governed_input=governed_input(worktree, role=role),
            role=role,
            venue=venue_name,
            worktree=str(worktree),
            filesystem=HermeticFilesystem(),
            version_probe=probe,
        )
    assert probe.calls == []


@pytest.mark.parametrize(
    ("venue_name", "role", "unsafe_sandbox"),
    [
        ("dev1-local", "architect_research", "workspace-write"),
        ("vps-tmux", "reviewer", "read-only"),
    ],
)
def test_planner_refuses_unsafe_first_duplicate_role_cell_before_version_probe(
    worktree: Path, venue_name: str, role: str, unsafe_sandbox: str
) -> None:
    loaded = policy(worktree)
    venue = loaded.venue(venue_name)
    unsafe_venue = replace(
        venue,
        role_sandboxes=((role, unsafe_sandbox), *venue.role_sandboxes),
    )
    unsafe_policy = replace(
        loaded,
        venues=tuple(unsafe_venue if item.name == venue.name else item for item in loaded.venues),
    )
    probe = FixedVersionProbe()
    with pytest.raises(launcher.CodexWorkerLaunchError, match="exactly one cell"):
        launcher.build_launch_plan(
            policy=unsafe_policy,
            governed_input=governed_input(worktree, role=role),
            role=role,
            venue=venue_name,
            worktree=str(worktree),
            filesystem=HermeticFilesystem(),
            version_probe=probe,
        )
    assert probe.calls == []


@pytest.mark.parametrize("template", MALFORMED_BINARY_TEMPLATES)
def test_planner_refuses_structurally_malformed_binary_template_before_version_probe(
    worktree: Path, template: str
) -> None:
    loaded = policy(worktree)
    venue = loaded.venue("dev1-local")
    unsafe_venue = replace(venue, codex_binary_template=template)
    unsafe_policy = replace(
        loaded,
        venues=tuple(unsafe_venue if item.name == venue.name else item for item in loaded.venues),
    )
    probe = FixedVersionProbe()
    with pytest.raises(launcher.CodexWorkerLaunchError, match="binary template"):
        launcher.build_launch_plan(
            policy=unsafe_policy,
            governed_input=governed_input(worktree, role="architect_research"),
            role="architect_research",
            venue="dev1-local",
            worktree=str(worktree),
            filesystem=UnusedFilesystem(),
            version_probe=probe,
        )
    assert probe.calls == []


@pytest.mark.parametrize("template", NON_STRING_BINARY_TEMPLATES)
def test_planner_refuses_non_string_binary_template_before_filesystem_or_version_probe(
    worktree: Path, template: object
) -> None:
    loaded = policy(worktree)
    venue = loaded.venue("dev1-local")
    unsafe_venue = replace(venue, codex_binary_template=template)
    unsafe_policy = replace(
        loaded,
        venues=tuple(unsafe_venue if item.name == venue.name else item for item in loaded.venues),
    )
    probe = FixedVersionProbe()
    with pytest.raises(launcher.CodexWorkerLaunchError, match="binary template"):
        launcher.build_launch_plan(
            policy=unsafe_policy,
            governed_input=governed_input(worktree, role="architect_research"),
            role="architect_research",
            venue="dev1-local",
            worktree=str(worktree),
            filesystem=UnusedFilesystem(),
            version_probe=probe,
        )
    assert probe.calls == []


def test_plan_has_exact_real_codex_argv_and_digest_only_metadata(worktree: Path) -> None:
    built = plan(worktree)
    config = launcher.toml_encode_config_value(built.developer_instructions)
    assert built.model == "gpt-5.6-terra"
    assert built.effort == "high"
    assert built.argv == (
        PINNED_BINARY,
        "exec",
        "--strict-config",
        "--ephemeral",
        "-m",
        "gpt-5.6-terra",
        "-c",
        "model_reasoning_effort=high",
        "-c",
        "features.multi_agent=false",
        "-c",
        "features.multi_agent_v2=false",
        "-c",
        f"developer_instructions={config}",
        "-s",
        "read-only",
        "-C",
        str(worktree),
        "--add-dir",
        f"{worktree}/governance",
        "--add-dir",
        f"{worktree}/validators",
        "-o",
        f"{worktree}/.ce/state/test-run.json",
        "-",
    )
    serialized = str(built.to_dict())
    assert "perform the bounded task" not in serialized
    assert built.brief_sha256 in serialized
    assert built.role_policy_sha256 in serialized
    assert AMBIENT_FOREMAN_BOOTSTRAP not in serialized

    parsed = tomllib.loads(f"value={config}")["value"]
    assert parsed == built.developer_instructions
    assert "\n" not in config
    assert all(ord(character) >= 0x20 for character in config)
    assert "schema: CE-GOVERNED-ROLE-ENVELOPE-V1" in parsed
    assert "version: 1" in parsed
    assert "role: architect_research" in parsed
    assert "role_kind: closed_leaf" in parsed
    assert "seat_class: worker" in parsed
    assert "nested_delegation: disabled" in parsed
    assert "capability: read_only_research" in parsed
    assert "sandbox: read-only" in parsed
    assert "role_policy_path: .claude/agents/architect_research.md" in parsed
    assert "brief_path: .ce/briefs/task.md" in parsed
    assert "parent_lineage: provenance_only_no_inherited_authority" in parsed
    assert "controller_or_foreman_authority" in parsed
    assert "nested_spawn" in parsed
    assert "credential_expansion" in parsed
    assert "approve" in parsed
    assert "enqueue" in parsed
    assert "merge" in parsed
    assert "sign" in parsed
    assert "reserved_act" in parsed


def test_governed_input_keeps_role_policy_out_of_brief_only_stdin(worktree: Path) -> None:
    loaded = governed_input(worktree)
    role_bytes = (worktree / ".claude" / "agents" / "implementer.md").read_bytes()
    brief_bytes = (worktree / ".ce" / "briefs" / "task.md").read_bytes()
    assert loaded.stdin == brief_bytes
    assert loaded.role_policy == role_bytes
    assert role_bytes not in loaded.stdin
    assert loaded.role_policy_sha256 == hashlib.sha256(role_bytes).hexdigest()
    assert loaded.brief_sha256 == hashlib.sha256(brief_bytes).hexdigest()


@pytest.mark.parametrize(
    ("role", "sandbox", "capability"),
    [
        ("architect_research", "read-only", "read_only_research"),
        ("implementer", "workspace-write", "scoped_worktree_edit_test_commit"),
        ("reviewer", "read-only", "read_only_review"),
        ("verification", "read-only", "read_only_test_execution"),
    ],
)
def test_exact_foreman_ambient_is_overridden_by_closed_leaf_envelope_matrix(
    worktree: Path, role: str, sandbox: str, capability: str
) -> None:
    worker_input = governed_input(worktree, role=role)
    envelope = launcher.build_governed_role_envelope(
        governed_input=worker_input,
        worktree=str(worktree),
        sandbox=sandbox,
    )
    encoded = launcher.toml_encode_config_value(envelope)
    parsed = tomllib.loads(f"developer_instructions={encoded}")[
        "developer_instructions"
    ]
    assert parsed == envelope
    assert f"role: {role}" in parsed
    assert f"capability: {capability}" in parsed
    assert "seat_class: worker" in parsed
    assert "Do not inherit controller or foreman authority" in parsed
    assert AMBIENT_FOREMAN_BOOTSTRAP not in parsed
    assert worker_input.stdin == b"perform the bounded task\n"


def _initialize_disposable_foreman_repo(worktree: Path) -> str:
    (worktree / "AGENTS.md").write_text(AMBIENT_FOREMAN_BOOTSTRAP, encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=worktree, check=True)
    subprocess.run(["git", "add", "."], cwd=worktree, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "commit.gpgsign=false",
            "-c",
            "user.name=Hermetic Parent",
            "-c",
            "user.email=parent@example.invalid",
            "commit",
            "-q",
            "-m",
            "test: ambient foreman baseline",
        ],
        cwd=worktree,
        check=True,
    )
    return hashlib.sha256((worktree / "AGENTS.md").read_bytes()).hexdigest()


@pytest.mark.parametrize(
    ("role", "sandbox", "writes"),
    [
        ("architect_research", "read-only", False),
        ("implementer", "workspace-write", True),
        ("reviewer", "read-only", False),
        ("verification", "read-only", False),
    ],
)
def test_hermetic_leaf_behavior_is_direct_for_implementer_and_read_only_otherwise(
    worktree: Path, role: str, sandbox: str, writes: bool
) -> None:
    worker_input = governed_input(worktree, role=role)
    foreman_digest = _initialize_disposable_foreman_repo(worktree)
    before = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=worktree,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    argv = _hermetic_leaf_argv(worker_input, worktree=worktree, sandbox=sandbox)
    assert HermeticLeafCodex().run(argv, stdin=worker_input.stdin) == 0
    after = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=worktree,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert (after != before) is writes
    assert (worktree / "bounded-result.txt").exists() is writes
    assert subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=worktree,
        check=True,
        capture_output=True,
        text=True,
    ).stdout == ""
    assert hashlib.sha256((worktree / "AGENTS.md").read_bytes()).hexdigest() == foreman_digest


@pytest.mark.parametrize(
    ("role", "sandbox", "writes"),
    [
        ("architect_research", "read-only", False),
        ("implementer", "workspace-write", True),
        ("reviewer", "read-only", False),
        ("verification", "read-only", False),
    ],
)
def test_production_subprocess_path_enforces_hermetic_leaf_behavior_matrix(
    worktree: Path,
    monkeypatch,
    role: str,
    sandbox: str,
    writes: bool,
) -> None:
    worker_input = governed_input(worktree, role=role)
    binary = _write_hermetic_codex_executable(worktree)
    hermetic_policy = _hermetic_subprocess_policy(
        worktree,
        binary=binary,
        role=role,
        monkeypatch=monkeypatch,
    )
    foreman_digest = _initialize_disposable_foreman_repo(worktree)
    before = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=worktree,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    built = launcher.build_launch_plan(
        policy=hermetic_policy,
        governed_input=worker_input,
        role=role,
        venue="dev1-local",
        worktree=str(worktree),
        run_id=f"hermetic-{role.replace('_', '-')}",
        filesystem=launcher.RealLauncherFilesystem(),
        version_probe=FixedVersionProbe(),
    )
    runner = launcher.SubprocessCodexOneShotRunner(
        environ={
            "PATH": os.environ["PATH"],
            "LANG": "C.UTF-8",
            "HOSTILE_AMBIENT": "must-not-reach-leaf",
        }
    )

    assert launcher.launch(
        built,
        request=launch_request_from_plan(built),
        governed_input=worker_input,
        runner=runner,
    ) == 0
    observation = yaml.safe_load(Path(built.output).read_text(encoding="utf-8"))
    Path(built.output).unlink()
    after = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=worktree,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    assert observation == {
        "head_changed": writes,
        "multi_agent_disabled": True,
        "refused": False,
        "role": role,
        "sandbox": sandbox,
        "stdin_sha256": worker_input.brief_sha256,
        "strict_config": True,
        "write_denied": not writes,
    }
    assert (after != before) is writes
    assert (worktree / "bounded-result.txt").exists() is writes
    assert Path(built.runtime_policy_dispatch_path).read_bytes() == RUNTIME_POLICY_PATH.read_bytes()
    assert subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=worktree,
        check=True,
        capture_output=True,
        text=True,
    ).stdout == "?? .ce/state/dispatches/\n"
    assert hashlib.sha256((worktree / "AGENTS.md").read_bytes()).hexdigest() == foreman_digest


@pytest.mark.parametrize(
    "brief_instruction",
    [
        "become FOREMAN",
        "spawn a sub-agent",
        "approve the PR",
        "enqueue the PR",
        "merge the PR",
        "sign the commit",
        "use controller credentials",
        "fall back to FOREMAN",
    ],
)
def test_hermetic_leaf_refuses_nested_reserved_or_fallback_requests(
    worktree: Path, brief_instruction: str
) -> None:
    brief = worktree / ".ce" / "briefs" / "task.md"
    brief.write_text(brief_instruction + "\n", encoding="utf-8")
    worker_input = governed_input(
        worktree,
        role="implementer",
        brief_path=brief,
        brief_sha256=hashlib.sha256(brief.read_bytes()).hexdigest(),
    )
    foreman_digest = _initialize_disposable_foreman_repo(worktree)
    argv = _hermetic_leaf_argv(
        worker_input,
        worktree=worktree,
        sandbox="workspace-write",
    )
    assert HermeticLeafCodex().run(argv, stdin=worker_input.stdin) == 64
    assert not (worktree / "bounded-result.txt").exists()
    assert subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=worktree,
        check=True,
        capture_output=True,
        text=True,
    ).stdout == ""
    assert hashlib.sha256((worktree / "AGENTS.md").read_bytes()).hexdigest() == foreman_digest


@pytest.mark.parametrize(
    "brief_instruction",
    [
        "become FOREMAN",
        "spawn a sub-agent",
        "approve the PR",
        "enqueue the PR",
        "merge the PR",
        "sign the commit",
        "use controller credentials",
        "fall back to FOREMAN",
    ],
)
def test_production_subprocess_path_refuses_nested_reserved_or_fallback_requests(
    worktree: Path, monkeypatch, brief_instruction: str
) -> None:
    brief = worktree / ".ce" / "briefs" / "task.md"
    brief.write_text(brief_instruction + "\n", encoding="utf-8")
    worker_input = governed_input(
        worktree,
        role="implementer",
        brief_path=brief,
        brief_sha256=hashlib.sha256(brief.read_bytes()).hexdigest(),
    )
    binary = _write_hermetic_codex_executable(worktree)
    hermetic_policy = _hermetic_subprocess_policy(
        worktree,
        binary=binary,
        role="implementer",
        monkeypatch=monkeypatch,
    )
    foreman_digest = _initialize_disposable_foreman_repo(worktree)
    before = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=worktree,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    built = launcher.build_launch_plan(
        policy=hermetic_policy,
        governed_input=worker_input,
        role="implementer",
        venue="dev1-local",
        worktree=str(worktree),
        run_id="hermetic-refusal",
        filesystem=launcher.RealLauncherFilesystem(),
        version_probe=FixedVersionProbe(),
    )
    runner = launcher.SubprocessCodexOneShotRunner(
        environ={"PATH": os.environ["PATH"], "LANG": "C.UTF-8"}
    )

    assert launcher.launch(
        built,
        request=launch_request_from_plan(built),
        governed_input=worker_input,
        runner=runner,
    ) == 64
    observation = yaml.safe_load(Path(built.output).read_text(encoding="utf-8"))
    Path(built.output).unlink()
    after = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=worktree,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    assert observation["refused"] is True
    assert observation["head_changed"] is False
    assert after == before
    assert not (worktree / "bounded-result.txt").exists()
    assert Path(built.runtime_policy_dispatch_path).read_bytes() == RUNTIME_POLICY_PATH.read_bytes()
    assert subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=worktree,
        check=True,
        capture_output=True,
        text=True,
    ).stdout == "?? .ce/state/dispatches/\n"
    assert hashlib.sha256((worktree / "AGENTS.md").read_bytes()).hexdigest() == foreman_digest


@pytest.mark.parametrize(
    ("role", "sandbox"),
    [
        ("architect_research", "workspace-write"),
        ("implementer", "read-only"),
        ("reviewer", "danger-full-access"),
        ("verification", "workspace-write"),
    ],
)
def test_envelope_refuses_role_capability_or_sandbox_escalation(
    worktree: Path, role: str, sandbox: str
) -> None:
    with pytest.raises(launcher.CodexWorkerLaunchError, match="sandbox posture"):
        launcher.build_governed_role_envelope(
            governed_input=governed_input(worktree, role=role),
            worktree=str(worktree),
            sandbox=sandbox,
        )


def test_envelope_refuses_digest_path_control_and_size_ambiguity(worktree: Path) -> None:
    worker_input = governed_input(worktree, role="architect_research")
    with pytest.raises(launcher.CodexWorkerLaunchError, match="role policy SHA-256 mismatch"):
        launcher.build_governed_role_envelope(
            governed_input=replace(worker_input, role_policy_sha256="0" * 64),
            worktree=str(worktree),
            sandbox="read-only",
        )
    with pytest.raises(launcher.CodexWorkerLaunchError, match="brief SHA-256 mismatch"):
        launcher.build_governed_role_envelope(
            governed_input=replace(worker_input, brief_sha256="0" * 64),
            worktree=str(worktree),
            sandbox="read-only",
        )

    ambiguous = worktree / ".ce" / "briefs" / "line\nbreak.md"
    ambiguous.write_bytes(worker_input.stdin)
    with pytest.raises(launcher.CodexWorkerLaunchError, match="canonical envelope path"):
        launcher.build_governed_role_envelope(
            governed_input=replace(worker_input, brief_path=str(ambiguous)),
            worktree=str(worktree),
            sandbox="read-only",
        )
    with pytest.raises(launcher.CodexWorkerLaunchError, match="size"):
        launcher.toml_encode_config_value("x" * (launcher.MAX_DEVELOPER_INSTRUCTIONS_BYTES + 1))


def test_launch_refuses_omitted_mismatched_or_authority_widened_envelope_before_runner(
    worktree: Path,
) -> None:
    worker_input = governed_input(worktree, role="architect_research")
    built = plan(worktree, governed_input=worker_input)
    mutations = [
        replace(
            built,
            argv=tuple(item for item in built.argv if item != "--strict-config"),
        ),
        replace(built, developer_instructions=built.developer_instructions + "\nfallback: foreman"),
        replace(
            built,
            argv=tuple(
                "danger-full-access" if item == "read-only" else item
                for item in built.argv
            ),
        ),
        replace(
            built,
            argv=tuple(
                item
                for item in built.argv
                if item != "features.multi_agent=false"
            ),
        ),
    ]
    for mutation in mutations:
        runner = RecordingRunner()
        with pytest.raises(
            launcher.CodexWorkerLaunchError,
            match="complete launch plan and executable argv are not canonical",
        ):
            launcher.launch(
                mutation,
                request=launch_request_from_plan(built),
                governed_input=worker_input,
                runner=runner,
                filesystem=HermeticFilesystem(),
            )
        assert runner.calls == []


@pytest.mark.parametrize(
    "mutate_argv",
    [
        lambda argv: ("/untrusted/codex", *argv[1:]),
        lambda argv: (argv[0], "run", *argv[2:]),
        lambda argv: (*argv[:-1], "--dangerously-bypass-approvals-and-sandbox", argv[-1]),
        lambda argv: (*argv[:-1], "--config", "features.multi_agent=true", argv[-1]),
        lambda argv: (*argv[:-1], "--sandbox", "danger-full-access", argv[-1]),
        lambda argv: (*argv[:-1], "-m", "untrusted-model", argv[-1]),
        lambda argv: tuple(
            "untrusted-model" if item == "gpt-5.6-terra" else item for item in argv
        ),
        lambda argv: tuple(
            "--model" if item == "-m" else item for item in argv
        ),
        lambda argv: tuple(item for item in argv if item != "--ephemeral"),
        lambda argv: (
            *argv[: argv.index("-C") + 1],
            "/untrusted/worktree",
            *argv[argv.index("-C") + 2 :],
        ),
        lambda argv: tuple(
            "/untrusted/add-dir" if item.endswith("/governance") else item
            for item in argv
        ),
        lambda argv: (
            *argv[: argv.index("-o") + 1],
            "/untrusted/output.json",
            *argv[argv.index("-o") + 2 :],
        ),
        lambda argv: argv[:-1],
        lambda argv: (argv[0], argv[1], argv[3], argv[2], *argv[4:]),
    ],
    ids=[
        "executable",
        "subcommand",
        "unexpected-bypass",
        "long-config-override",
        "long-sandbox-override",
        "duplicate-model",
        "model-value",
        "long-model-form",
        "missing-ephemeral",
        "worktree-value",
        "add-dir-value",
        "output-value",
        "missing-stdin-marker",
        "reordered-options",
    ],
)
def test_launch_refuses_every_noncanonical_argv_mutation_before_runner(
    worktree: Path, mutate_argv
) -> None:
    worker_input = governed_input(worktree, role="architect_research")
    built = plan(worktree, governed_input=worker_input)
    runner = RecordingRunner()

    with pytest.raises(
        launcher.CodexWorkerLaunchError,
        match="complete launch plan and executable argv are not canonical",
    ):
        launcher.launch(
            replace(built, argv=tuple(mutate_argv(built.argv))),
            request=launch_request_from_plan(built),
            governed_input=worker_input,
            runner=runner,
            filesystem=HermeticFilesystem(),
        )

    assert runner.calls == []


def _replace_argv_value(
    argv: tuple[str, ...], old: str, new: str
) -> tuple[str, ...]:
    assert argv.count(old) == 1
    return tuple(new if item == old else item for item in argv)


def test_launch_refuses_coordinated_valid_venue_mutation_before_runner(
    worktree: Path,
) -> None:
    worker_input = governed_input(worktree, role="architect_research")
    built = plan(worktree, governed_input=worker_input)
    request = launcher.build_launch_request(
        policy=policy(worktree),
        governed_input=worker_input,
        role="architect_research",
        venue="dev1-local",
        worktree=str(worktree),
        run_id="test-run",
        filesystem=HermeticFilesystem(),
    )
    runner = RecordingRunner()

    with pytest.raises(
        launcher.CodexWorkerLaunchError,
        match="complete launch plan and executable argv are not canonical",
    ):
        launcher.launch(
            replace(built, venue="dgx-relay"),
            request=request,
            governed_input=worker_input,
            runner=runner,
            filesystem=HermeticFilesystem(),
        )

    assert runner.calls == []


def test_launch_refuses_coordinated_alternate_valid_run_request_before_runner(
    worktree: Path,
) -> None:
    worker_input = governed_input(worktree, role="architect_research")
    built = plan(worktree, governed_input=worker_input)
    request = launcher.build_launch_request(
        policy=policy(worktree),
        governed_input=worker_input,
        role="architect_research",
        venue="dev1-local",
        worktree=str(worktree),
        run_id="test-run",
        filesystem=HermeticFilesystem(),
    )
    alternate_run_id = "alternate-valid-run"
    alternate_output = str(worktree / ".ce" / "state" / f"{alternate_run_id}.json")
    runner = RecordingRunner()

    with pytest.raises(
        launcher.CodexWorkerLaunchError,
        match="complete launch plan and executable argv are not canonical",
    ):
        launcher.launch(
            replace(
                built,
                run_id=alternate_run_id,
                output=alternate_output,
                argv=_replace_argv_value(built.argv, built.output, alternate_output),
            ),
            request=request,
            governed_input=worker_input,
            runner=runner,
            filesystem=HermeticFilesystem(),
        )

    assert runner.calls == []


@pytest.mark.parametrize(
    "mutation",
    [
        lambda built, worktree: replace(
            built,
            binary="/tmp/untrusted-codex",
            argv=("/tmp/untrusted-codex", *built.argv[1:]),
        ),
        lambda built, worktree: replace(
            built,
            model="untrusted-model",
            argv=_replace_argv_value(
                built.argv, built.model, "untrusted-model"
            ),
        ),
        lambda built, worktree: replace(
            built,
            effort="low",
            argv=_replace_argv_value(
                built.argv,
                f"model_reasoning_effort={built.effort}",
                "model_reasoning_effort=low",
            ),
        ),
        lambda built, worktree: replace(
            built,
            add_dirs=(str(worktree / ".ce"), *built.add_dirs[1:]),
            argv=_replace_argv_value(
                built.argv, built.add_dirs[0], str(worktree / ".ce")
            ),
        ),
        lambda built, worktree: replace(
            built,
            sandbox="workspace-write",
            argv=_replace_argv_value(
                built.argv, built.sandbox, "workspace-write"
            ),
        ),
        lambda built, worktree: replace(
            built,
            run_id="../escape",
            output=str(worktree.parent / "escape.json"),
            argv=_replace_argv_value(
                built.argv, built.output, str(worktree.parent / "escape.json")
            ),
        ),
        lambda built, worktree: replace(
            built,
            run_id="bad/slash",
            output=str(worktree / ".ce" / "state" / "bad" / "slash.json"),
            argv=_replace_argv_value(
                built.argv,
                built.output,
                str(worktree / ".ce" / "state" / "bad" / "slash.json"),
            ),
        ),
        lambda built, worktree: replace(
            built,
            binary="/tmp/untrusted-codex",
            model="untrusted-model",
            effort="low",
            add_dirs=(str(worktree / ".ce"), *built.add_dirs[1:]),
            argv=_replace_argv_value(
                _replace_argv_value(
                    _replace_argv_value(
                        ("/tmp/untrusted-codex", *built.argv[1:]),
                        built.model,
                        "untrusted-model",
                    ),
                    f"model_reasoning_effort={built.effort}",
                    "model_reasoning_effort=low",
                ),
                built.add_dirs[0],
                str(worktree / ".ce"),
            ),
        ),
    ],
    ids=[
        "binary-plus-argv",
        "model-plus-argv",
        "effort-plus-argv",
        "add-dirs-plus-argv",
        "sandbox-plus-argv",
        "traversal-run-id-output-plus-argv",
        "malformed-run-id-output-plus-argv",
        "combined-policy-derived-fields-plus-argv",
    ],
)
def test_launch_refuses_coordinated_plan_and_argv_mutation_before_runner(
    worktree: Path, mutation
) -> None:
    worker_input = governed_input(worktree, role="architect_research")
    built = plan(worktree, governed_input=worker_input)
    runner = RecordingRunner()

    with pytest.raises(
        launcher.CodexWorkerLaunchError,
        match="complete launch plan and executable argv are not canonical",
    ):
        launcher.launch(
            mutation(built, worktree),
            request=launch_request_from_plan(built),
            governed_input=worker_input,
            runner=runner,
            filesystem=HermeticFilesystem(),
        )

    assert runner.calls == []


@pytest.mark.parametrize("node_kind", ["symlink", "directory"])
def test_launch_refuses_coordinated_existing_output_node_before_runner(
    worktree: Path, node_kind: str
) -> None:
    worker_input = governed_input(worktree, role="architect_research")
    built = plan(worktree, governed_input=worker_input)
    run_id = "coordinated-output-node"
    output = worktree / ".ce" / "state" / f"{run_id}.json"
    if node_kind == "symlink":
        outside = worktree.parent / "outside-output.json"
        outside.write_text("outside\n", encoding="utf-8")
        output.symlink_to(outside)
    else:
        output.mkdir()
    mutated = replace(
        built,
        run_id=run_id,
        output=str(output),
        argv=_replace_argv_value(built.argv, built.output, str(output)),
    )
    runner = RecordingRunner()

    with pytest.raises(
        launcher.CodexWorkerLaunchError,
        match="complete launch plan and executable argv are not canonical",
    ):
        launcher.launch(
            mutated,
            request=launch_request_from_plan(built),
            governed_input=worker_input,
            runner=runner,
            filesystem=HermeticFilesystem(),
        )

    assert runner.calls == []


@pytest.mark.parametrize(
    "credentials",
    [
        ("OPENAI_API_KEY",),
        ("OPENAI_API_KEY", "OPENAI_API_KEY"),
        ("OPENAI_API_KEY", "GITHUB_TOKEN"),
    ],
    ids=["empty-to-provider", "duplicate", "cross-role"],
)
def test_launch_refuses_reviewer_credential_tuple_mutation_before_runner(
    worktree: Path, credentials: tuple[str, ...]
) -> None:
    worker_input = governed_input(worktree, role="reviewer")
    built = plan(worktree, governed_input=worker_input, role="reviewer")
    runner = RecordingRunner()

    with pytest.raises(launcher.CodexWorkerLaunchError, match="launch envelope"):
        launcher.launch(
            replace(built, provider_credential_env_names=credentials),
            request=launch_request_from_plan(built),
            governed_input=worker_input,
            runner=runner,
            filesystem=HermeticFilesystem(),
        )

    assert runner.calls == []


@pytest.mark.parametrize(
    "credentials",
    [
        (),
        ("OPENAI_API_KEY", "OPENAI_API_KEY"),
        ("GITHUB_TOKEN",),
    ],
    ids=["provider-to-empty", "duplicate", "cross-role"],
)
def test_launch_refuses_provider_role_credential_tuple_mutation_before_runner(
    worktree: Path, credentials: tuple[str, ...]
) -> None:
    worker_input = governed_input(worktree, role="architect_research")
    built = plan(worktree, governed_input=worker_input, role="architect_research")
    runner = RecordingRunner()

    with pytest.raises(launcher.CodexWorkerLaunchError, match="launch envelope"):
        launcher.launch(
            replace(built, provider_credential_env_names=credentials),
            request=launch_request_from_plan(built),
            governed_input=worker_input,
            runner=runner,
            filesystem=HermeticFilesystem(),
        )

    assert runner.calls == []


def test_launch_refuses_reordered_role_credential_tuple_before_runner(
    worktree: Path, monkeypatch
) -> None:
    second_name = "SECOND_PROVIDER_KEY"
    monkeypatch.setattr(
        launcher,
        "ALLOWED_MODEL_PROVIDER_CREDENTIAL_ENV_NAMES",
        frozenset({"OPENAI_API_KEY", second_name}),
    )
    rewrite_policy(
        worktree,
        lambda raw: raw["role_provider_credentials"].__setitem__(
            "architect_research", ["OPENAI_API_KEY", second_name]
        ),
    )
    worker_input = governed_input(worktree, role="architect_research")
    built = plan(worktree, governed_input=worker_input, role="architect_research")
    runner = RecordingRunner()

    with pytest.raises(launcher.CodexWorkerLaunchError, match="launch envelope"):
        launcher.launch(
            replace(
                built,
                provider_credential_env_names=(second_name, "OPENAI_API_KEY"),
            ),
            request=launch_request_from_plan(built),
            governed_input=worker_input,
            runner=runner,
            filesystem=HermeticFilesystem(),
        )

    assert runner.calls == []


@pytest.mark.parametrize("mutation", ["replace", "symlink", "remove", "oversize"])
def test_launch_reopens_and_rebinds_canonical_role_policy_before_runner(
    worktree: Path, mutation: str
) -> None:
    worker_input = governed_input(worktree, role="architect_research")
    built = plan(worktree, governed_input=worker_input)
    role_path = Path(worker_input.role_policy_path)
    if mutation == "replace":
        role_path.write_bytes(b"# replaced after planning\n")
    elif mutation == "symlink":
        role_path.unlink()
        role_path.symlink_to(worktree / ".claude" / "agents" / "reviewer.md")
    elif mutation == "remove":
        role_path.unlink()
    else:
        role_path.write_bytes(b"x" * (launcher.MAX_ROLE_POLICY_BYTES + 1))
    runner = RecordingRunner()

    with pytest.raises(launcher.CodexWorkerLaunchError, match="launch envelope"):
        launcher.launch(
            built,
            request=launch_request_from_plan(built),
            governed_input=worker_input,
            runner=runner,
        )

    assert runner.calls == []


@pytest.mark.parametrize("mutation", ["same-byte-replace", "chmod"])
def test_launch_refuses_role_policy_identity_or_mode_drift_before_runner(
    worktree: Path, mutation: str
) -> None:
    worker_input = governed_input(worktree, role="architect_research")
    built = plan(worktree, governed_input=worker_input)
    role_path = Path(worker_input.role_policy_path)
    if mutation == "same-byte-replace":
        replacement = role_path.with_suffix(".replacement")
        replacement.write_bytes(role_path.read_bytes())
        replacement.chmod(role_path.stat().st_mode)
        replacement.replace(role_path)
    else:
        role_path.chmod(role_path.stat().st_mode ^ 0o022)
    runner = RecordingRunner()

    with pytest.raises(launcher.CodexWorkerLaunchError, match="launch envelope"):
        launcher.launch(
            built,
            request=launch_request_from_plan(built),
            governed_input=worker_input,
            runner=runner,
            filesystem=HermeticFilesystem(),
        )

    assert runner.calls == []


def test_launch_refuses_role_policy_ownership_drift_before_runner(worktree: Path) -> None:
    worker_input = governed_input(worktree, role="architect_research")
    built = plan(worktree, governed_input=worker_input)
    runner = RecordingRunner()

    class OwnershipDriftFilesystem(HermeticFilesystem):
        def read_bytes_with_binding(self, path: str, *, max_bytes: int | None = None):
            payload, binding = super().read_bytes_with_binding(path, max_bytes=max_bytes)
            if os.path.normpath(path) == worker_input.role_policy_path:
                binding = replace(binding, uid=binding.uid + 1)
            return payload, binding

    with pytest.raises(launcher.CodexWorkerLaunchError, match="launch envelope"):
        launcher.launch(
            built,
            request=launch_request_from_plan(built),
            governed_input=worker_input,
            runner=runner,
            filesystem=OwnershipDriftFilesystem(),
        )

    assert runner.calls == []


@pytest.mark.parametrize("digest", ["A" * 64, "f" * 63, "0" * 64])
def test_governed_input_refuses_noncanonical_or_mismatched_digest(worktree: Path, digest: str) -> None:
    with pytest.raises(launcher.CodexWorkerLaunchError, match="brief SHA-256"):
        governed_input(worktree, brief_sha256=digest)


def test_governed_input_refuses_brief_escape_symlink_and_nonregular(worktree: Path) -> None:
    outside = worktree.parent / "outside.md"
    outside.write_text("outside\n", encoding="utf-8")
    link = worktree / ".ce" / "briefs" / "link.md"
    link.symlink_to(outside)
    directory = worktree / ".ce" / "briefs" / "directory"
    directory.mkdir()
    missing = worktree / ".ce" / "briefs" / "missing.md"
    for candidate, message in [
        (outside, "canonical area"),
        (link, "symlink"),
        (directory, "regular readable file"),
        (missing, "regular readable file"),
    ]:
        with pytest.raises(launcher.CodexWorkerLaunchError, match=message):
            governed_input(worktree, brief_path=candidate, brief_sha256="0" * 64)


def test_governed_input_refuses_replaced_canonical_role_policy(worktree: Path) -> None:
    role_path = worktree / ".claude" / "agents" / "implementer.md"
    role_path.unlink()
    role_path.symlink_to(worktree / ".claude" / "agents" / "reviewer.md")
    with pytest.raises(launcher.CodexWorkerLaunchError, match="role policy.*symlink"):
        governed_input(worktree)


def test_canonical_policy_rejects_symlink_replacement(worktree: Path) -> None:
    canonical = worktree / "governance" / "policies" / POLICY_PATH.name
    replacement = worktree / "replacement.yaml"
    replacement.write_bytes(POLICY_PATH.read_bytes())
    canonical.unlink()
    canonical.symlink_to(replacement)
    with pytest.raises(launcher.CodexWorkerLaunchError, match="launcher policy.*symlink"):
        launcher.load_canonical_policy(worktree, filesystem=HermeticFilesystem())


@pytest.mark.parametrize("alias", CANONICAL_ADD_DIR_ALIASES)
def test_policy_parser_refuses_canonical_add_dir_alias_duplicates(
    worktree: Path, alias: str
) -> None:
    rewrite_policy(
        worktree,
        lambda raw: raw["canonical_add_dirs"].append(alias),
    )
    with pytest.raises(
        launcher.CodexWorkerLaunchError, match="canonical_add_dirs.*duplicates"
    ):
        policy(worktree)


@pytest.mark.parametrize("alias", CANONICAL_ADD_DIR_ALIASES)
def test_cli_refuses_canonical_add_dir_alias_duplicates_without_traceback(
    worktree: Path, monkeypatch, capsys, alias: str
) -> None:
    rewrite_policy(
        worktree,
        lambda raw: raw["canonical_add_dirs"].append(alias),
    )
    brief = worktree / ".ce" / "briefs" / "task.md"
    brief.write_bytes(b"bounded cli alias test\n")
    digest = hashlib.sha256(brief.read_bytes()).hexdigest()
    monkeypatch.setattr(
        ce_cli, "_make_codex_launcher_filesystem", lambda: HermeticFilesystem()
    )
    monkeypatch.setattr(
        ce_cli, "_make_codex_version_probe", lambda: pytest.fail("version probe constructed")
    )
    monkeypatch.setattr(
        ce_cli, "_make_codex_one_shot_runner", lambda: pytest.fail("runner constructed")
    )
    assert ce_cli.main(
        [
            "worker",
            "launch",
            "--role",
            "architect_research",
            "--venue",
            "dev1-local",
            "--worktree",
            str(worktree),
            "--brief",
            str(brief),
            "--brief-sha256",
            digest,
            "--run-id",
            "cli-add-dir-alias-test",
        ]
    ) == 1
    captured = capsys.readouterr()
    assert "ce worker launch refused" in captured.err
    assert "Traceback" not in captured.err


@pytest.mark.parametrize("alias", CANONICAL_ADD_DIR_ALIASES)
def test_direct_policy_refuses_canonical_add_dir_alias_duplicates_before_probe(
    worktree: Path, alias: str
) -> None:
    loaded = policy(worktree)
    unsafe_policy = replace(
        loaded,
        canonical_add_dirs=(*loaded.canonical_add_dirs, alias),
    )
    probe = FixedVersionProbe()
    with pytest.raises(
        launcher.CodexWorkerLaunchError, match="canonical_add_dirs.*duplicates"
    ):
        launcher.build_launch_plan(
            policy=unsafe_policy,
            governed_input=governed_input(worktree, role="architect_research"),
            role="architect_research",
            venue="dev1-local",
            worktree=str(worktree),
            filesystem=UnusedFilesystem(),
            version_probe=probe,
        )
    assert probe.calls == []


def test_direct_policy_refuses_resolved_canonical_add_dir_identity_duplicate_before_probe(
    worktree: Path,
) -> None:
    loaded = policy(worktree)
    governance = str(worktree / "governance")
    validators = str(worktree / "validators")

    class ResolvedAliasFilesystem(HermeticFilesystem):
        def realpath(self, path: str) -> str:
            if os.path.normpath(path) == validators:
                return governance
            return super().realpath(path)

    probe = FixedVersionProbe()
    with pytest.raises(
        launcher.CodexWorkerLaunchError, match="canonical_add_dirs.*duplicates"
    ):
        launcher.build_launch_plan(
            policy=loaded,
            governed_input=governed_input(worktree, role="architect_research"),
            role="architect_research",
            venue="dev1-local",
            worktree=str(worktree),
            filesystem=ResolvedAliasFilesystem(),
            version_probe=probe,
        )
    assert probe.calls == []


def test_worktree_and_canonical_directories_are_real_existing_directories(worktree: Path) -> None:
    missing = worktree / "validators"
    missing.rmdir()
    with pytest.raises(launcher.CodexWorkerLaunchError, match="canonical add-dir.*directory"):
        plan(worktree)
    missing.write_text("not a directory\n", encoding="utf-8")
    with pytest.raises(launcher.CodexWorkerLaunchError, match="canonical add-dir.*directory"):
        plan(worktree)


def test_canonical_add_dir_symlink_is_refused(worktree: Path) -> None:
    validators = worktree / "validators"
    validators.rmdir()
    outside = worktree.parent / "outside-validators"
    outside.mkdir()
    validators.symlink_to(outside, target_is_directory=True)
    with pytest.raises(launcher.CodexWorkerLaunchError, match="canonical add-dir.*symlink"):
        plan(worktree)


def test_worktree_symlink_is_refused(worktree: Path) -> None:
    link = worktree.parent / "linked-worker"
    link.symlink_to(worktree, target_is_directory=True)
    loaded = policy(worktree)
    worker_input = governed_input(worktree, role="architect_research")
    with pytest.raises(launcher.CodexWorkerLaunchError, match="worktree.*symlink"):
        launcher.build_launch_plan(
            policy=loaded,
            governed_input=worker_input,
            role="architect_research",
            venue="dev1-local",
            worktree=str(link),
            filesystem=HermeticFilesystem(),
            version_probe=FixedVersionProbe(),
        )


def test_existing_output_symlink_or_nonregular_node_is_refused(worktree: Path) -> None:
    output = worktree / ".ce" / "state" / "test-run.json"
    outside = worktree.parent / "outside-output.json"
    outside.write_text("do not overwrite\n", encoding="utf-8")
    output.symlink_to(outside)
    with pytest.raises(launcher.CodexWorkerLaunchError, match="output.*symlink"):
        plan(worktree)
    output.unlink()
    output.mkdir()
    with pytest.raises(launcher.CodexWorkerLaunchError, match="output.*regular file"):
        plan(worktree)


@pytest.mark.parametrize(
    ("filesystem", "probe", "message"),
    [
        (HermeticFilesystem(binary_exists=False), FixedVersionProbe(), "regular executable"),
        (HermeticFilesystem(binary_executable=False), FixedVersionProbe(), "regular executable"),
        (
            HermeticFilesystem(binary_realpath="/opt/creator-engine/codex/other/bin/codex"),
            FixedVersionProbe(),
            "version root",
        ),
        (HermeticFilesystem(), FixedVersionProbe("0.144.1"), "version probe"),
    ],
)
def test_binary_preflight_refuses_missing_nonexecutable_escape_or_version_mismatch(
    worktree: Path,
    filesystem: HermeticFilesystem,
    probe: FixedVersionProbe,
    message: str,
) -> None:
    with pytest.raises(launcher.CodexWorkerLaunchError, match=message):
        plan(worktree, filesystem=filesystem, version_probe=probe)


def test_only_explicit_launch_calls_injected_runner_with_verified_bytes(worktree: Path) -> None:
    binary = worktree.parent / "codex" / "0.145.0-alpha.9" / "bin" / "codex"
    binary.parent.mkdir(parents=True)
    binary.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    binary.chmod(0o755)
    rewrite_policy(
        worktree,
        lambda raw: raw["venues"]["dev1-local"].__setitem__(
            "codex_binary_template",
            str(binary).replace("0.145.0-alpha.9", "{version}"),
        ),
    )
    runner = RecordingRunner()
    worker_input = governed_input(worktree, role="architect_research")
    built = plan(worktree, governed_input=worker_input)
    assert runner.calls == []
    assert launcher.launch(
        built,
        request=launch_request_from_plan(built),
        governed_input=worker_input,
        runner=runner,
    ) == 0
    assert runner.calls == [(built.argv, worker_input.stdin)]


@pytest.mark.parametrize(
    "mutation",
    [
        "missing-policy",
        "missing-receipt",
        "stale-policy",
        "forged-receipt",
        "insecure-mode",
        "policy-symlink",
        "policy-directory",
    ],
)
def test_runtime_policy_evidence_refuses_before_version_probe(
    worktree: Path, mutation: str
) -> None:
    raw = yaml.safe_load(
        (worktree / launcher.CANONICAL_POLICY_RELATIVE_PATH).read_text()
    )
    binding = raw["runtime_policy_binding"]
    local = worktree / binding["local_policy_relative_path"]
    receipt = worktree / binding["local_receipt_relative_path"]
    if mutation == "missing-policy":
        local.unlink()
    elif mutation == "missing-receipt":
        receipt.unlink()
    elif mutation == "stale-policy":
        local.write_bytes(local.read_bytes() + b"# stale\n")
        local.chmod(0o600)
    elif mutation == "forged-receipt":
        forged = json.loads(receipt.read_text())
        forged["policy_id"] = "forged-policy-v1"
        receipt.write_text(json.dumps(forged, sort_keys=True, separators=(",", ":")) + "\n")
        receipt.chmod(0o600)
    elif mutation == "insecure-mode":
        local.chmod(0o644)
    elif mutation == "policy-symlink":
        outside = worktree.parent / "outside-policy.yaml"
        outside.write_bytes(local.read_bytes())
        local.unlink()
        local.symlink_to(outside)
    else:
        local.unlink()
        local.mkdir()
    probe = FixedVersionProbe()
    with pytest.raises(launcher.CodexWorkerLaunchError, match="runtime policy refused"):
        plan(worktree, version_probe=probe)
    assert probe.calls == []


@pytest.mark.parametrize(
    "encoding",
    ["duplicate-key", "whitespace", "reordered"],
)
def test_runtime_policy_receipt_refuses_noncanonical_bytes_before_version_probe(
    worktree: Path, encoding: str
) -> None:
    raw = yaml.safe_load(
        (worktree / launcher.CANONICAL_POLICY_RELATIVE_PATH).read_text()
    )
    binding = raw["runtime_policy_binding"]
    receipt_path = worktree / binding["local_receipt_relative_path"]
    receipt = json.loads(receipt_path.read_bytes())
    if encoding == "duplicate-key":
        members = json.dumps(receipt, sort_keys=True, separators=(",", ":"))[1:-1]
        payload = (
            '{"kind":"runtime-policy-provenance-receipt",' + members + "}\n"
        ).encode("utf-8")
    elif encoding == "whitespace":
        payload = (json.dumps(receipt, sort_keys=True, indent=2) + "\n").encode("utf-8")
    else:
        reordered = dict(reversed(tuple(receipt.items())))
        payload = (
            json.dumps(reordered, sort_keys=False, separators=(",", ":")) + "\n"
        ).encode("utf-8")
    receipt_path.write_bytes(payload)
    receipt_path.chmod(0o600)
    probe = FixedVersionProbe()

    with pytest.raises(launcher.CodexWorkerLaunchError, match="runtime policy refused"):
        plan(worktree, version_probe=probe)

    assert probe.calls == []


def test_runtime_policy_refuses_deferred_dgx_before_version_probe(worktree: Path) -> None:
    worker_input = governed_input(worktree, role="architect_research")
    probe = FixedVersionProbe()
    with pytest.raises(launcher.CodexWorkerLaunchError, match="execution venue"):
        launcher.build_launch_plan(
            policy=policy(worktree),
            governed_input=worker_input,
            role="architect_research",
            venue="dgx-relay",
            worktree=str(worktree),
            run_id="dgx-refused",
            filesystem=HermeticFilesystem(),
            version_probe=probe,
        )
    assert probe.calls == []


def test_runtime_policy_same_byte_replacement_is_refused_before_runner(worktree: Path) -> None:
    worker_input = governed_input(worktree, role="architect_research")
    built = plan(worktree, governed_input=worker_input)
    local = Path(built.runtime_policy_path)
    payload = local.read_bytes()
    replacement = local.with_name("replacement-policy.yaml")
    replacement.write_bytes(payload)
    replacement.chmod(0o600)
    os.replace(replacement, local)
    runner = RecordingRunner()
    with pytest.raises(launcher.CodexWorkerLaunchError, match="identity or metadata changed"):
        launcher.launch(
            built,
            request=launch_request_from_plan(built),
            governed_input=worker_input,
            runner=runner,
            filesystem=HermeticFilesystem(),
        )
    assert runner.calls == []


def test_runtime_policy_dispatch_copy_is_private_and_idempotent(worktree: Path) -> None:
    binary = worktree.parent / "codex" / "0.145.0-alpha.9" / "bin" / "codex"
    binary.parent.mkdir(parents=True)
    binary.write_text("#!/bin/sh\nexit 0\n")
    binary.chmod(0o755)
    rewrite_policy(
        worktree,
        lambda raw: raw["venues"]["dev1-local"].__setitem__(
            "codex_binary_template", str(binary).replace("0.145.0-alpha.9", "{version}")
        ),
    )
    worker_input = governed_input(worktree, role="architect_research")
    built = plan(worktree, governed_input=worker_input)
    runner = RecordingRunner()
    request = launch_request_from_plan(built)
    assert launcher.launch(built, request=request, governed_input=worker_input, runner=runner) == 0
    first = Path(built.runtime_policy_dispatch_path)
    first_binding = first.stat()
    assert launcher.launch(built, request=request, governed_input=worker_input, runner=runner) == 0
    assert first.read_bytes() == Path(built.runtime_policy_source_path).read_bytes()
    assert first.stat().st_ino == first_binding.st_ino
    assert first.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("component", ["dispatches", "run"])
def test_dispatch_directory_symlink_component_is_refused_before_runner(
    worktree: Path, component: str
) -> None:
    worker_input = governed_input(worktree, role="architect_research")
    built = plan(worktree, governed_input=worker_input)
    state = worktree / ".ce" / "state"
    outside = worktree / "outside-dispatch-target"
    outside.mkdir()
    if component == "dispatches":
        (state / "dispatches").symlink_to(outside, target_is_directory=True)
    else:
        (state / "dispatches").mkdir(mode=0o700)
        (state / "dispatches" / "test-run").symlink_to(outside, target_is_directory=True)
    runner = RecordingRunner()
    with pytest.raises(launcher.CodexWorkerLaunchError, match="not a real directory"):
        launcher.launch(
            built,
            request=launch_request_from_plan(built),
            governed_input=worker_input,
            runner=runner,
            filesystem=HermeticFilesystem(),
        )
    assert runner.calls == []
    assert list(outside.iterdir()) == []


def test_dispatch_materialization_refuses_without_dir_fd_support(
    worktree: Path, monkeypatch
) -> None:
    worker_input = governed_input(worktree, role="architect_research")
    built = plan(worktree, governed_input=worker_input)
    monkeypatch.setattr(launcher.os, "supports_dir_fd", frozenset())
    runner = RecordingRunner()
    with pytest.raises(launcher.CodexWorkerLaunchError, match="dir_fd support"):
        launcher.launch(
            built,
            request=launch_request_from_plan(built),
            governed_input=worker_input,
            runner=runner,
            filesystem=HermeticFilesystem(),
        )
    assert runner.calls == []
    assert not (worktree / ".ce" / "state" / "dispatches").exists()


def test_dispatch_directory_mkdir_permission_error_is_typed_refusal(
    worktree: Path, monkeypatch
) -> None:
    worker_input = governed_input(worktree, role="architect_research")
    built = plan(worktree, governed_input=worker_input)

    def deny_mkdir(*_args, **_kwargs):
        raise PermissionError("injected mkdir denial")

    # Keep the dir_fd capability gate satisfied for the patched callable so
    # the typed wrapping of the mkdir failure itself is what gets exercised.
    monkeypatch.setattr(
        launcher.os, "supports_dir_fd", launcher.os.supports_dir_fd | {deny_mkdir}
    )
    monkeypatch.setattr(launcher.os, "mkdir", deny_mkdir)
    runner = RecordingRunner()
    with pytest.raises(launcher.CodexWorkerLaunchError, match="cannot be created"):
        launcher.launch(
            built,
            request=launch_request_from_plan(built),
            governed_input=worker_input,
            runner=runner,
            filesystem=HermeticFilesystem(),
        )
    assert runner.calls == []
    assert not (worktree / ".ce" / "state" / "dispatches").exists()


@pytest.mark.parametrize("returncode", [0, 1])
def test_production_version_probe_uses_cleanup_bound_credential_free_environment(
    tmp_path: Path, monkeypatch, returncode: int
) -> None:
    captured: dict[str, object] = {}
    hostile = {
        "PATH": "/runtime/bin",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "TERM": "xterm-256color",
        "HOME": str(tmp_path / "host-home"),
        "CODEX_HOME": str(tmp_path / "host-codex"),
        "XDG_CONFIG_HOME": str(tmp_path / "host-config"),
        "GH_TOKEN": "host-gh-secret",
        "AWS_ACCESS_KEY_ID": "host-aws-secret",
        "SSH_AUTH_SOCK": str(tmp_path / "ssh-agent.sock"),
        "GPG_AGENT_INFO": str(tmp_path / "gpg-agent.sock"),
        "CE_CONTROLLER_SOCKET": str(tmp_path / "controller.sock"),
        "OPENAI_API_KEY": "provider-secret-must-not-reach-probe",
    }

    def fake_run(argv, **kwargs):
        env = dict(kwargs["env"])
        captured.update({"argv": argv, "env": env, "root": Path(env["HOME"]).parent})
        for name in (
            "HOME",
            "CODEX_HOME",
            "TMPDIR",
            "XDG_CONFIG_HOME",
            "XDG_CACHE_HOME",
            "XDG_DATA_HOME",
        ):
            assert Path(env[name]).is_dir()
        return subprocess.CompletedProcess(argv, returncode, "codex-cli 0.145.0-alpha.9\n", "")

    monkeypatch.setattr(launcher.subprocess, "run", fake_run)
    probe = launcher.SubprocessCodexVersionProbe(environ=hostile)
    if returncode:
        with pytest.raises(launcher.CodexWorkerLaunchError, match="version probe failed"):
            probe.probe(PINNED_BINARY)
    else:
        assert probe.probe(PINNED_BINARY) == "0.145.0-alpha.9"

    child_env = captured["env"]
    assert isinstance(child_env, dict)
    for name in hostile:
        if name in {"PATH", "LANG", "LC_ALL", "TERM"}:
            continue
        if name in {"HOME", "CODEX_HOME", "XDG_CONFIG_HOME"}:
            assert child_env[name] != hostile[name]
        else:
            assert name not in child_env
    assert child_env["LC_ALL"] == "C.UTF-8"
    assert captured["root"] is not None
    assert not Path(captured["root"]).exists()


@pytest.mark.parametrize("venue", ["dgx-relay", "dev1-local"])
def test_implementer_is_refused_at_former_native_venues_before_runner_execution(
    worktree: Path, venue: str
) -> None:
    runner = RecordingRunner()
    worker_input = governed_input(worktree, role="implementer")
    with pytest.raises(launcher.CodexWorkerLaunchError, match="not attested"):
        launcher.build_launch_plan(
            policy=policy(worktree),
            governed_input=worker_input,
            role="implementer",
            venue=venue,
            worktree=str(worktree),
            filesystem=HermeticFilesystem(),
            version_probe=FixedVersionProbe(),
        )
    assert runner.calls == []


def test_production_runner_uses_isolated_homes_and_scrubs_hostile_ambient_env(
    tmp_path: Path, monkeypatch
) -> None:
    captured: dict[str, object] = {}
    hostile = {
        "PATH": "/runtime/bin",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "TERM": "xterm-256color",
        "HOME": str(tmp_path / "host-home"),
        "CODEX_HOME": str(tmp_path / "host-codex"),
        "XDG_CONFIG_HOME": str(tmp_path / "host-config"),
        "GH_TOKEN": "host-gh-secret",
        "GITHUB_TOKEN": "host-github-secret",
        "AWS_ACCESS_KEY_ID": "host-aws-secret",
        "AWS_SECRET_ACCESS_KEY": "host-aws-secret",
        "SSH_AUTH_SOCK": str(tmp_path / "ssh-agent.sock"),
        "GPG_AGENT_INFO": str(tmp_path / "gpg-agent.sock"),
        "CE_CONTROLLER_SOCKET": str(tmp_path / "controller.sock"),
        "CE_SEAT_SOCKET": str(tmp_path / "seat.sock"),
        "GIT_CONFIG_GLOBAL": str(tmp_path / "host-gitconfig"),
        "AWS_CONFIG_FILE": str(tmp_path / "host-aws-config"),
        "OPENAI_API_KEY": "allowed-provider-secret",
        "ANTHROPIC_API_KEY": "unlisted-provider-secret",
        "HOSTILE_AMBIENT": "must-not-survive",
    }

    def fake_run(argv, **kwargs):
        env = kwargs["env"]
        captured.update({"argv": argv, "env": dict(env)})
        for name in (
            "HOME",
            "CODEX_HOME",
            "TMPDIR",
            "XDG_CONFIG_HOME",
            "XDG_CACHE_HOME",
            "XDG_DATA_HOME",
        ):
            assert Path(env[name]).is_dir()
            assert Path(env[name]).is_relative_to(Path(env["HOME"]).parent)
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr(launcher.subprocess, "run", fake_run)
    runner = launcher.SubprocessCodexOneShotRunner(environ=hostile)
    assert runner.run(
        ["/pinned/codex", "exec"],
        stdin=b"verified",
        provider_credential_env_names=("OPENAI_API_KEY",),
    ) == 0

    child_env = captured["env"]
    assert isinstance(child_env, dict)
    assert child_env["OPENAI_API_KEY"] == "allowed-provider-secret"
    assert child_env["PATH"] == "/runtime/bin"
    assert child_env["LANG"] == "C.UTF-8"
    assert child_env["LC_ALL"] == "C.UTF-8"
    assert child_env["TERM"] == "xterm-256color"
    invocation_owned = {"HOME", "CODEX_HOME", "XDG_CONFIG_HOME"}
    for name in hostile:
        if name not in {
            "PATH",
            "LANG",
            "LC_ALL",
            "TERM",
            "OPENAI_API_KEY",
            *invocation_owned,
        }:
            assert name not in child_env
    for name in invocation_owned:
        assert name in child_env
        assert child_env[name] != hostile[name]
    assert not Path(child_env["HOME"]).exists()
    assert not Path(child_env["CODEX_HOME"]).exists()


def test_production_runner_refuses_untracked_provider_credential_name() -> None:
    runner = launcher.SubprocessCodexOneShotRunner(environ={"GITHUB_TOKEN": "secret"})
    with pytest.raises(launcher.CodexWorkerLaunchError, match="non-provider credential"):
        runner.run(
            ["/pinned/codex", "exec"],
            stdin=b"verified",
            provider_credential_env_names=("GITHUB_TOKEN",),
        )


@pytest.mark.parametrize(
    "credential_name",
    [
        "LC_GITHUB_TOKEN",
        "LC_AWS_SECRET_ACCESS_KEY",
        "LC_PRIVATE_KEY",
        "LC_AUTH_SOCK",
        "LC_CREDENTIALS",
        "LC_PASSWORD",
    ],
)
def test_production_runner_scrubs_credential_shaped_locale_names(
    monkeypatch, credential_name: str
) -> None:
    captured: dict[str, str] = {}

    def fake_run(argv, **kwargs):
        captured.update(kwargs["env"])
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr(launcher.subprocess, "run", fake_run)
    runner = launcher.SubprocessCodexOneShotRunner(
        environ={credential_name: "secret", "LC_ALL": "C.UTF-8"}
    )
    assert runner.run(
        ["/pinned/codex", "exec"],
        stdin=b"verified",
        provider_credential_env_names=(),
    ) == 0
    assert credential_name not in captured
    assert captured["LC_ALL"] == "C.UTF-8"


@pytest.mark.parametrize("credential_name", PREFIXED_EXACT_ONLY_SENSITIVE_ENV_NAMES)
def test_shared_child_environment_refuses_prefixed_exact_only_sensitive_names(
    monkeypatch, credential_name: str
) -> None:
    captured: list[dict[str, str]] = []

    def fake_run(argv, **kwargs):
        captured.append(dict(kwargs["env"]))
        if argv[-1] == "--version":
            return subprocess.CompletedProcess(argv, 0, "codex-cli 0.145.0-alpha.9\n", "")
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr(launcher.subprocess, "run", fake_run)
    source = {
        credential_name: "secret",
        "LC_ALL": "C.UTF-8",
        "LC_CTYPE": "C.UTF-8",
        "LC_MESSAGES": "C.UTF-8",
    }
    assert launcher.SubprocessCodexVersionProbe(environ=source).probe(PINNED_BINARY) == (
        "0.145.0-alpha.9"
    )
    assert launcher.SubprocessCodexOneShotRunner(environ=source).run(
        ["/pinned/codex", "exec"],
        stdin=b"verified",
        provider_credential_env_names=(),
    ) == 0
    assert len(captured) == 2
    for child_env in captured:
        assert credential_name not in child_env
        assert child_env["LC_ALL"] == "C.UTF-8"
        assert child_env["LC_CTYPE"] == "C.UTF-8"
        assert child_env["LC_MESSAGES"] == "C.UTF-8"

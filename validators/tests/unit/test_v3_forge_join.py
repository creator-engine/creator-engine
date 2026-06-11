"""v3.1-G2a/G2c — unit tests for the forge-leg composition root (``v3_forge_join``).

Every network/crypto/subprocess edge is faked through injected seams: ZERO live git / gh /
openssl / HTTPS. The headline boundary invariant — the join imports NO v1 module — is asserted
off the module AST. The gate's heart is the secret-hygiene proof: a sentinel token value appears
in NO argv and NO record bytes, lands only in the authenticated child env; the App private key is
execed by (fake) openssl and its bytes never enter the process; the JIT token is minted with
EXACTLY the least-privilege set and revoked on success AND failure.
"""
from __future__ import annotations

import ast
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from creator_engine_validator import _versions as ver
from creator_engine_validator import coordination, v3_forge_join, v3_seat_bridge
from creator_engine_validator.forge.app_jwt_runner import build_app_jwt
from creator_engine_validator.forge.github_repo_config import ForgeConfigError
from creator_engine_validator.v3_forge_join import (
    AppConfig,
    ForgeJoinRefused,
    load_app_config,
    open_change_for_run,
    openssl_signer,
    policy_sha,
)

SENTINEL = "ghs_SENTINELtoken_DEADBEEFcafef00d"
REPO = "creator-engine/creator-engine"
BRANCH = "v31-g2-forge-join"
LOCAL = "a" * 40
HEAD_SHA = "d" * 40
_FIXED_NOW = datetime(2026, 6, 11, 9, 30, 0, tzinfo=timezone.utc)


def _app_config(**over) -> AppConfig:
    base = dict(
        client_id="Iv1.client",
        installation_id=139551869,
        pem_path="/host/.ce-keys/ce-forge-app.pem",
        repo=REPO,
        permissions=(("contents", "write"), ("pull_requests", "write")),
    )
    base.update(over)
    return AppConfig(**base)


def _CP(argv, rc, stdout="", stderr=""):
    return subprocess.CompletedProcess(list(argv), rc, stdout=stdout, stderr=stderr)


class FakeMintRunner:
    """The App-JWT mint runner (GhRunner shape): returns a minted-token JSON."""

    def __init__(self, token_value=SENTINEL):
        self.calls = []
        self.token_value = token_value

    def __call__(self, argv, input_text=None):
        self.calls.append({"argv": list(argv), "input": input_text})
        return _CP(argv, 0, stdout=json.dumps(
            {"token": self.token_value, "expires_at": "2026-06-11T10:00:00Z"}))


class FakeGhSpawn:
    """The authenticated gh-api spawn (open_change + revoke): routes by argv, records env."""

    def __init__(self, *, pr_number=7, head_sha=HEAD_SHA, fail_open=False, fail_revoke=False):
        self.calls = []
        self.posted = False
        self.pr_number = pr_number
        self.head_sha = head_sha
        self.fail_open = fail_open
        self.fail_revoke = fail_revoke

    def __call__(self, argv, input_text, env):
        argv = list(argv)
        self.calls.append({"argv": argv, "input": input_text, "env": dict(env)})
        if "DELETE" in argv and "installation/token" in argv:
            rc = 1 if self.fail_revoke else 0
            return _CP(argv, rc, stdout="" if rc else "{}", stderr="revoke boom" if rc else "")
        if "POST" in argv:  # open the PR
            if self.fail_open:
                return _CP(argv, 1, stderr="open boom")
            self.posted = True
            return _CP(argv, 0, stdout=json.dumps(
                {"number": self.pr_number, "head": {"sha": self.head_sha}}))
        if "GET" in argv:  # read open pulls (none until POSTed)
            body = ([{"number": self.pr_number, "head": {"sha": self.head_sha}}]
                    if self.posted else [])
            return _CP(argv, 0, stdout=json.dumps(body))
        raise AssertionError(f"unexpected gh argv: {argv}")  # pragma: no cover

    def verb_calls(self, *needles):
        return [c for c in self.calls if all(n in c["argv"] for n in needles)]


class FakeGit:
    """The push spawn: rev-parse (local head) / ls-remote / merge-base / push."""

    def __init__(self, *, local=LOCAL, remote=None, push_rc=0):
        self.calls = []
        self.local = local
        self.remote = remote
        self.push_rc = push_rc

    def __call__(self, argv, input_text, env):
        argv = list(argv)
        self.calls.append({"argv": argv, "env": dict(env)})
        if "rev-parse" in argv:
            return _CP(argv, 0, stdout=self.local + "\n")
        if "ls-remote" in argv:
            out = f"{self.remote}\trefs/heads/{BRANCH}\n" if self.remote else ""
            return _CP(argv, 0, stdout=out)
        if "merge-base" in argv:
            return _CP(argv, 0)
        if "push" in argv:
            return _CP(argv, self.push_rc, stderr="push boom" if self.push_rc else "")
        raise AssertionError(f"unexpected git argv: {argv}")  # pragma: no cover

    def pushed(self):
        return [c for c in self.calls if "push" in c["argv"]]


def _seed_dispatch(root: Path, *, spawned=True, failed=False, change=None, policy=None) -> str:
    """Materialize a schema-valid dispatch (via the bridge), then stamp spawn/failure/change state."""
    plan = coordination.DispatchPlan(
        scope_id="rate-limit-login",
        runtime_policy=policy or {"spend_envelopes": [{"scope": "run", "cap_usd": 5}]},
        mutation_class="code",
        scope_ratification={"approver_ref": "a" * 64, "ratified_scope_sha": "b" * 64},
    )
    rec = v3_seat_bridge.materialize_dispatch(plan, root, now=_FIXED_NOW)
    if spawned:
        rec.data["terminal"] = {"kind": "tmux", "session_id": "$1", "window_id": "@2", "pane_id": "%3"}
        rec.data["spawned_at"] = "20260611T093000Z"
    if failed:
        rec.data["spawn_failed_at"] = "20260611T093000Z"
        rec.data["spawn_failure_reason"] = "CC-D-6 refused"
    if change is not None:
        rec.data["change"] = change
    v3_seat_bridge._write_record(rec)
    return rec.run_id


# ---------------------------------------------------------------------------
# Boundary invariant — AST proves zero v1 imports
# ---------------------------------------------------------------------------

def test_forge_join_imports_no_v1_module():
    src = Path(v3_forge_join.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    referenced: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                referenced.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                referenced.add(node.module.split(".")[0])
            if node.level and node.module is None:
                for alias in node.names:
                    referenced.add(alias.name.split(".")[0])
    crossed = referenced & ver.V1_RUNTIME
    assert crossed == set(), f"forge-join must import no v1 module, found: {sorted(crossed)}"


def test_forge_join_classified_v3():
    assert ver.classify("v3_forge_join") == ver.V3
    assert "v3_forge_join" in ver.V3_RUNTIME


# ---------------------------------------------------------------------------
# load_app_config — fail-closed, ids never reach a record
# ---------------------------------------------------------------------------

def _write_cfg(tmp_path, **over) -> Path:
    data = {
        "client_id": "Iv1.client", "installation_id": 139551869,
        "pem_path": "/host/.ce-keys/ce-forge-app.pem", "repo": REPO,
        "permissions": {"contents": "write", "pull_requests": "write"},
    }
    data.update(over)
    p = tmp_path / "ce-forge-app.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_load_app_config_reads_fields(tmp_path):
    cfg = load_app_config(_write_cfg(tmp_path))
    assert cfg.client_id == "Iv1.client"
    assert cfg.installation_id == 139551869
    assert cfg.repo == REPO
    assert ("contents", "write") in cfg.permissions


def test_load_app_config_repr_hides_app_ids(tmp_path):
    cfg = load_app_config(_write_cfg(tmp_path))
    text = repr(cfg)
    assert "139551869" not in text and "Iv1.client" not in text
    assert "redacted" in text


def test_load_app_config_fail_closed_missing_file(tmp_path):
    with pytest.raises(ForgeJoinRefused):
        load_app_config(tmp_path / "absent.json")


@pytest.mark.parametrize("bad", [
    {"client_id": ""}, {"installation_id": "not-int"}, {"installation_id": 0},
    {"pem_path": ""}, {"repo": "not-a-repo"},
])
def test_load_app_config_fail_closed_bad_fields(tmp_path, bad):
    with pytest.raises(ForgeJoinRefused):
        load_app_config(_write_cfg(tmp_path, **bad))


def test_load_app_config_malformed_json(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(ForgeJoinRefused):
        load_app_config(p)


# ---------------------------------------------------------------------------
# openssl_signer — the App private key stays behind openssl (PEM off-process)
# ---------------------------------------------------------------------------

def test_openssl_signer_execs_openssl_with_input_on_stdin():
    captured = {}

    def fake_openssl(argv, input=None, capture_output=False):
        captured["argv"] = list(argv)
        captured["input"] = input
        return _CP(argv, 0, stdout=b"RAW_SIGNATURE_BYTES")

    sign = openssl_signer("/host/key.pem", runner=fake_openssl)
    sig = sign(b"b64header.b64payload")
    assert sig == b"RAW_SIGNATURE_BYTES"
    assert captured["argv"] == ["openssl", "dgst", "-sha256", "-sign", "/host/key.pem"]
    # the signing input rides STDIN; the PEM is named in argv (openssl reads the file itself)
    assert captured["input"] == b"b64header.b64payload"


def test_openssl_signer_refuses_nonzero_exit():
    sign = openssl_signer("/host/key.pem", runner=lambda *a, **k: _CP(a[0] if a else [], 1))
    with pytest.raises(ForgeJoinRefused):
        sign(b"x")


def test_openssl_signer_refuses_empty_signature():
    sign = openssl_signer("/host/key.pem", runner=lambda *a, **k: _CP([], 0, stdout=b""))
    with pytest.raises(ForgeJoinRefused):
        sign(b"x")


def test_openssl_signer_composes_into_build_app_jwt():
    sign = openssl_signer("/host/key.pem", runner=lambda *a, **k: _CP([], 0, stdout=b"sigbytes"))
    jwt = build_app_jwt("Iv1.client", signer=sign, now=lambda: 1_700_000_000.0)
    assert jwt.count(".") == 2  # header.payload.signature


# ---------------------------------------------------------------------------
# policy_sha — canonical derivation
# ---------------------------------------------------------------------------

def test_policy_sha_uses_existing_hex_or_derives():
    assert policy_sha({"policy_sha": "e" * 64}) == "e" * 64
    derived = policy_sha({"a": 1})
    assert len(derived) == 64 and derived == policy_sha({"a": 1})


# ---------------------------------------------------------------------------
# open_change_for_run — preconditions BEFORE any forge call
# ---------------------------------------------------------------------------

def test_open_refuses_unknown_dispatch_before_mint(tmp_path):
    mint = FakeMintRunner()
    with pytest.raises(ForgeJoinRefused):
        open_change_for_run(
            tmp_path, "run-ghost", app_config=_app_config(), branch=BRANCH,
            manifest_paths=["a.py"], mint_gh_runner=mint,
        )
    assert mint.calls == []  # never minted


def test_open_refuses_unspawned_run_before_mint(tmp_path):
    run_id = _seed_dispatch(tmp_path, spawned=False)
    mint = FakeMintRunner()
    with pytest.raises(ForgeJoinRefused):
        open_change_for_run(
            tmp_path, run_id, app_config=_app_config(), branch=BRANCH,
            manifest_paths=["a.py"], mint_gh_runner=mint,
        )
    assert mint.calls == []


def test_open_refuses_spawn_failed_run(tmp_path):
    run_id = _seed_dispatch(tmp_path, spawned=False, failed=True)
    mint = FakeMintRunner()
    with pytest.raises(ForgeJoinRefused):
        open_change_for_run(
            tmp_path, run_id, app_config=_app_config(), branch=BRANCH,
            manifest_paths=["a.py"], mint_gh_runner=mint,
        )
    assert mint.calls == []


def test_open_refuses_already_stamped_change(tmp_path):
    run_id = _seed_dispatch(tmp_path, change={
        "branch": BRANCH, "base": "main", "pr_number": 5,
        "head_sha": HEAD_SHA, "manifest_paths": ["a.py"], "opened_at": "2026-06-11T09:30:00Z"})
    mint = FakeMintRunner()
    with pytest.raises(ForgeJoinRefused):
        open_change_for_run(
            tmp_path, run_id, app_config=_app_config(), branch=BRANCH,
            manifest_paths=["a.py"], mint_gh_runner=mint,
        )
    assert mint.calls == []


# ---------------------------------------------------------------------------
# Plan-by-default mutates nothing durable
# ---------------------------------------------------------------------------

def test_plan_mode_mints_reads_revokes_but_stamps_no_change(tmp_path):
    run_id = _seed_dispatch(tmp_path)
    mint, git, gh = FakeMintRunner(), FakeGit(remote=None), FakeGhSpawn()
    ref = open_change_for_run(
        tmp_path, run_id, app_config=_app_config(), branch=BRANCH,
        manifest_paths=["a.py", "b.py"], apply=False,
        mint_gh_runner=mint, git_spawn=git, token_spawn=gh,
    )
    assert ref.pr_number is None  # would-create plan
    assert git.pushed() == []  # plan never pushes
    assert gh.verb_calls("POST") == []  # plan never opens
    # the token was still minted (to READ) and revoked
    assert len(mint.calls) == 1 and gh.verb_calls("DELETE", "installation/token")
    # NO change block stamped — plan mutates nothing durable
    drec = yaml.safe_load((tmp_path / "dispatches" / run_id / "dispatch.yaml").read_text())
    assert "change" not in drec


# ---------------------------------------------------------------------------
# apply=True drives mint→push→open→stamp→revoke
# ---------------------------------------------------------------------------

def test_apply_drives_full_chain_and_stamps_change_block(tmp_path):
    run_id = _seed_dispatch(tmp_path)
    mint, git, gh = FakeMintRunner(), FakeGit(remote=None), FakeGhSpawn(pr_number=7)
    ref = open_change_for_run(
        tmp_path, run_id, app_config=_app_config(), branch=BRANCH,
        manifest_paths=["a.py"], apply=True, now=_FIXED_NOW,
        mint_gh_runner=mint, git_spawn=git, token_spawn=gh,
    )
    assert ref.pr_number == 7 and ref.head_sha == HEAD_SHA
    assert git.pushed()  # the branch was pushed
    assert gh.verb_calls("POST")  # a PR was opened
    assert gh.verb_calls("DELETE", "installation/token")  # token revoked
    # the value-free change block landed on dispatch.yaml
    drec = yaml.safe_load((tmp_path / "dispatches" / run_id / "dispatch.yaml").read_text())
    change = drec["change"]
    assert change["pr_number"] == 7 and change["branch"] == BRANCH and change["base"] == "main"
    assert change["head_sha"] == HEAD_SHA and change["manifest_paths"] == ["a.py"]
    assert change["opened_at"] == "2026-06-11T09:30:00Z"


def test_apply_stamped_dispatch_conforms_to_schema(tmp_path):
    import jsonschema
    run_id = _seed_dispatch(tmp_path)
    open_change_for_run(
        tmp_path, run_id, app_config=_app_config(), branch=BRANCH,
        manifest_paths=["a.py"], apply=True, now=_FIXED_NOW,
        mint_gh_runner=FakeMintRunner(), git_spawn=FakeGit(remote=None), token_spawn=FakeGhSpawn(),
    )
    schema = yaml.safe_load(
        (Path(__file__).resolve().parents[3] / "schemas" / "dispatch-record.schema.yaml")
        .read_text(encoding="utf-8")
    )
    drec = yaml.safe_load((tmp_path / "dispatches" / run_id / "dispatch.yaml").read_text())
    jsonschema.validate(drec, schema)  # the stamped change block validates


# ---------------------------------------------------------------------------
# JIT token: EXACT least-privilege + revoke on success AND failure
# ---------------------------------------------------------------------------

def test_token_request_is_exact_least_privilege(tmp_path, monkeypatch):
    run_id = _seed_dispatch(tmp_path)
    seen = {}
    import creator_engine_validator.v3_forge_join as mod
    real_mint = mod.mint_scoped_token

    def spy_mint(request, *, gh_runner=None):
        seen["request"] = request
        return real_mint(request, gh_runner=gh_runner)

    monkeypatch.setattr(mod, "mint_scoped_token", spy_mint)
    open_change_for_run(
        tmp_path, run_id, app_config=_app_config(), branch=BRANCH,
        manifest_paths=["a.py"], apply=True, now=_FIXED_NOW,
        mint_gh_runner=FakeMintRunner(), git_spawn=FakeGit(remote=None), token_spawn=FakeGhSpawn(),
    )
    req = seen["request"]
    assert dict(req.permissions) == {"contents": "write", "pull_requests": "write"}
    assert 0 < req.requested_ttl_seconds <= 900


def test_revoke_runs_even_when_open_fails(tmp_path):
    run_id = _seed_dispatch(tmp_path)
    gh = FakeGhSpawn(fail_open=True)
    with pytest.raises(ForgeConfigError):
        open_change_for_run(
            tmp_path, run_id, app_config=_app_config(), branch=BRANCH,
            manifest_paths=["a.py"], apply=True,
            mint_gh_runner=FakeMintRunner(), git_spawn=FakeGit(remote=None), token_spawn=gh,
        )
    # the credential is released on the failure path too
    assert gh.verb_calls("DELETE", "installation/token")
    # no change block stamped on a failed open
    drec = yaml.safe_load((tmp_path / "dispatches" / run_id / "dispatch.yaml").read_text())
    assert "change" not in drec


def test_revoke_failure_is_swallowed_not_masking(tmp_path):
    run_id = _seed_dispatch(tmp_path)
    # open succeeds; revoke transport fails — must NOT raise (best-effort, token expires on ttl)
    ref = open_change_for_run(
        tmp_path, run_id, app_config=_app_config(), branch=BRANCH,
        manifest_paths=["a.py"], apply=True,
        mint_gh_runner=FakeMintRunner(), git_spawn=FakeGit(remote=None),
        token_spawn=FakeGhSpawn(fail_revoke=True),
    )
    assert ref.pr_number == 7


# ---------------------------------------------------------------------------
# Secret hygiene — the gate's heart
# ---------------------------------------------------------------------------

def test_token_value_in_no_argv_and_no_record_bytes(tmp_path):
    run_id = _seed_dispatch(tmp_path)
    mint, git, gh = FakeMintRunner(), FakeGit(remote=None), FakeGhSpawn()
    open_change_for_run(
        tmp_path, run_id, app_config=_app_config(), branch=BRANCH,
        manifest_paths=["a.py"], apply=True, now=_FIXED_NOW,
        mint_gh_runner=mint, git_spawn=git, token_spawn=gh,
    )
    # the sentinel token NEVER appears in any argv (git or gh) or input body
    for c in git.calls + gh.calls:
        assert SENTINEL not in " ".join(c["argv"])
    for c in gh.calls:
        assert SENTINEL not in str(c.get("input"))
    # nor in the persisted dispatch record bytes
    drec_bytes = (tmp_path / "dispatches" / run_id / "dispatch.yaml").read_text()
    assert SENTINEL not in drec_bytes


def test_token_value_only_in_authenticated_call_env(tmp_path):
    run_id = _seed_dispatch(tmp_path)
    git, gh = FakeGit(remote=None), FakeGhSpawn()
    open_change_for_run(
        tmp_path, run_id, app_config=_app_config(), branch=BRANCH,
        manifest_paths=["a.py"], apply=True,
        mint_gh_runner=FakeMintRunner(), git_spawn=git, token_spawn=gh,
    )
    # the authenticated gh calls (open + revoke) carry GH_TOKEN; local git read calls do not
    for c in gh.calls:
        assert c["env"].get("GH_TOKEN") == SENTINEL
    for c in git.calls:
        if "rev-parse" in c["argv"] or "merge-base" in c["argv"]:
            assert "GH_TOKEN" not in c["env"]
        if "push" in c["argv"]:
            assert c["env"].get("GH_TOKEN") == SENTINEL

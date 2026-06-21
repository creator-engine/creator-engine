"""S6 (ce-ops#157) — the ``resolve_live_config`` shared-App mint-broker branch.

When ``github.app.kind`` is ``shared`` AND a ``CE_FORGE_MINT_BROKER_URL`` is configured, the
driver mints via the standing broker (the user has NO App PEM): ``resolve_live_config`` returns
a :class:`LiveForgeConfig` whose ``token_minter`` is a ``broker_minter`` closure and whose
``signer`` is ``None`` — WITHOUT requiring ``CE_FORGE_APP_PEM``. The existing local-signer
paths are untouched: ``kind: own`` (and the default local path) still require the PEM, and a
shared kind with NO broker URL falls through to ``None`` (fail-closed). The
``CE_FORGE_LIVE_FORGE`` / ``CE_FORGE_ADOPTION_WRITE`` authorization gates are unchanged.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from creator_engine_validator import onboard_apply_live, v3_installer

_REPO = "arad-owner/mythos"


def _schema() -> dict:
    return yaml.safe_load(Path("schemas/install-answers.schema.yaml").read_text(encoding="utf-8"))


def _merged(*, kind: str = "shared", installation_id=555) -> "v3_installer.MergeResult":
    app: dict = {"kind": kind}
    if installation_id is not None:
        app["installation_id"] = installation_id
    github = {"mode": "existing", "repo": _REPO, "app": app}
    answers = {"answers_version": 1, "github": github}
    return v3_installer.merge_answers(_schema(), answers=answers, detected={})


# ---------------------------------------------------------------------------
# shared + broker URL + resolvable install → config WITHOUT a PEM
# ---------------------------------------------------------------------------
def test_shared_with_broker_url_resolves_without_a_pem():
    env = {
        "CE_FORGE_MINT_BROKER_URL": "https://mint.creator-engine.dev",
        "CE_FORGE_APP_CLIENT_ID": "Iv1.shared",
        # NOTE: deliberately NO CE_FORGE_APP_PEM
    }
    cfg = onboard_apply_live.resolve_live_config(_merged(), policy_sha="a" * 64, env=env)
    assert cfg is not None
    assert cfg.signer is None  # the broker holds the key
    assert cfg.token_minter is not None  # mints via the broker seam
    assert cfg.repo == _REPO
    assert cfg.installation_id == 555


def test_shared_broker_config_drives_the_token_minter_seam(monkeypatch):
    # The broker_minter closure POSTs to the broker and returns a ScopedToken from its response.
    posted: list = []

    def fake_post(url, payload):
        posted.append({"url": url, "payload": payload})
        return {
            "status": 200,
            "token": "ghs_from_broker",
            "expires_at": "2026-06-21T15:00:00Z",
            "permissions": [["contents", "read"]],
        }

    monkeypatch.setattr(onboard_apply_live, "_post_mint_broker", fake_post, raising=False)
    env = {
        "CE_FORGE_MINT_BROKER_URL": "https://mint.creator-engine.dev",
        "CE_FORGE_APP_CLIENT_ID": "Iv1.shared",
        "CE_FORGE_MINT_BROKER_USER_TOKEN": "ghu_caller000",
    }
    cfg = onboard_apply_live.resolve_live_config(_merged(), policy_sha="a" * 64, env=env)
    assert cfg is not None
    from creator_engine_validator.forge.scoped_token import TokenRequest

    req = TokenRequest(
        repo=_REPO,
        installation_id=555,
        run_id="r",
        policy_sha="a" * 64,
        permissions={"contents": "read"},
        secret_name="x",
        requested_ttl_seconds=600,
    )
    token = cfg.token_minter(req)
    assert token.value == "ghs_from_broker"
    assert posted and posted[0]["url"].endswith("/v1/token")
    assert posted[0]["payload"]["installation_id"] == 555
    assert posted[0]["payload"]["repo"] == _REPO


# ---------------------------------------------------------------------------
# fail-closed: shared but NO broker URL → None
# ---------------------------------------------------------------------------
def test_shared_without_broker_url_or_pem_is_none():
    env = {"CE_FORGE_APP_CLIENT_ID": "Iv1.shared"}  # no broker URL, no PEM
    cfg = onboard_apply_live.resolve_live_config(_merged(), policy_sha="a" * 64, env=env)
    assert cfg is None


def test_broker_url_but_missing_client_id_is_none():
    env = {"CE_FORGE_MINT_BROKER_URL": "https://mint.creator-engine.dev"}  # no client id
    cfg = onboard_apply_live.resolve_live_config(_merged(), policy_sha="a" * 64, env=env)
    assert cfg is None


def test_broker_url_but_unresolvable_installation_is_none():
    env = {
        "CE_FORGE_MINT_BROKER_URL": "https://mint.creator-engine.dev",
        "CE_FORGE_APP_CLIENT_ID": "Iv1.shared",
    }
    cfg = onboard_apply_live.resolve_live_config(
        _merged(installation_id=None), policy_sha="a" * 64, env=env
    )
    assert cfg is None


# ---------------------------------------------------------------------------
# kind: own (and local path) UNCHANGED — still requires the PEM
# ---------------------------------------------------------------------------
def test_own_kind_still_requires_a_pem_and_ignores_broker_url(tmp_path):
    # Even with a broker URL set, an OWN App must use the local-signer path (PEM required).
    env = {
        "CE_FORGE_MINT_BROKER_URL": "https://mint.creator-engine.dev",
        "CE_FORGE_APP_CLIENT_ID": "Iv1.own",
        # no PEM → own path fails closed
    }
    cfg = onboard_apply_live.resolve_live_config(
        _merged(kind="own"), policy_sha="a" * 64, env=env
    )
    assert cfg is None


def test_own_kind_with_pem_uses_local_signer(tmp_path):
    pem = tmp_path / "own.pem"
    pem.write_text("k", encoding="utf-8")
    env = {
        "CE_FORGE_APP_CLIENT_ID": "Iv1.own",
        "CE_FORGE_APP_PEM": str(pem),
    }
    cfg = onboard_apply_live.resolve_live_config(
        _merged(kind="own"), policy_sha="a" * 64, env=env
    )
    assert cfg is not None
    assert cfg.signer is not None  # local signer
    assert cfg.token_minter is None  # local path


def test_default_local_pem_path_unchanged_when_no_broker_url(tmp_path):
    pem = tmp_path / "ce-app.pem"
    pem.write_text("k", encoding="utf-8")
    env = {
        "CE_FORGE_APP_CLIENT_ID": "Iv1.x",
        "CE_FORGE_APP_PEM": str(pem),
        "CE_FORGE_INSTALLATION_ID": "140271364",
    }
    cfg = onboard_apply_live.resolve_live_config(_merged(), policy_sha="a" * 64, env=env)
    assert cfg is not None
    assert cfg.signer is not None
    assert cfg.token_minter is None

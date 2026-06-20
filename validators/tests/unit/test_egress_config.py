"""Unit tests for the egress-broker per-App config schema + fail-closed loader.

``egress_broker.config.load_broker_config`` reads the host-side broker config AS DATA: the
target repo, the installation owner (org) used for installation-id discovery, the publish
:class:`~egress_broker.policy.BrokerPolicy`, and a per-seat App table covering dev-1/2/3/4
(``app_id``, ``app_owner``, ``pem_path``, optional ``installation_id``). It is fail-closed:
a missing/malformed field, an empty seat table, or an empty author allow-list (a broker that
could never authorize anyone is misconfigured) is a refusal, never a silent default.

Secret hygiene: the per-seat ``SeatAppConfig`` keeps the App id / pem path out of its
``repr`` (these are host-bound identity, not for incidental logs).
"""

import json

import pytest

from egress_broker.config import BrokerConfigError, SeatAppConfig, load_broker_config
from egress_broker.policy import BrokerPolicy


def _doc(**over):
    base = {
        "repo": "creator-engine/creator-engine",
        "installation_owner": "creator-engine",
        "audit_log": "~/.ce-egress/audit.jsonl",
        "policy": {
            "base_branch": "main",
            "allowed_branch_namespaces": ["ce-", "v3-", "feat/"],
            "forbidden_branches": ["develop"],
            "authorized_emails": [],
            "authorized_logins": ["cedev4vps-coder", "ce-dev-3"],
            "max_pushes_per_window": 30,
            "window_seconds": 3600,
        },
        "seats": {
            "dev-4": {
                "app_id": "4085526",
                "app_owner": "cedev4vps-coder",
                "pem_path": "/dev/shm/ce-dev4/ce-forge-dev4.pem",
                "installation_id": None,
            },
            "dev-2": {
                "app_id": "4025879",
                "app_owner": "ubuntuaws745-cmyk",
                "pem_path": "/dev/shm/ce-dev2/ce-forge-dev2.pem",
                "installation_id": 99887766,
            },
        },
    }
    base.update(over)
    return base


def _write(tmp_path, doc):
    p = tmp_path / "broker.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    return p


def test_loads_a_well_formed_config(tmp_path):
    cfg = load_broker_config(_write(tmp_path, _doc()))
    assert cfg.repo == "creator-engine/creator-engine"
    assert cfg.installation_owner == "creator-engine"
    assert isinstance(cfg.policy, BrokerPolicy)
    assert cfg.policy.base_branch == "main"
    assert "ce-" in cfg.policy.allowed_branch_namespaces
    assert set(cfg.seats) == {"dev-4", "dev-2"}


def test_seat_lookup_returns_typed_app_config(tmp_path):
    cfg = load_broker_config(_write(tmp_path, _doc()))
    dev4 = cfg.seat("dev-4")
    assert isinstance(dev4, SeatAppConfig)
    assert dev4.app_id == "4085526"
    assert dev4.app_owner == "cedev4vps-coder"
    assert dev4.installation_id is None  # absent → discovered later
    assert cfg.seat("dev-2").installation_id == 99887766


def test_unknown_seat_is_refused(tmp_path):
    cfg = load_broker_config(_write(tmp_path, _doc()))
    with pytest.raises(BrokerConfigError):
        cfg.seat("dev-9")


def test_policy_normalizes_emails_lowercase_and_builds_frozensets(tmp_path):
    doc = _doc()
    doc["policy"]["authorized_emails"] = ["Dev@Creator-Engine.Example"]
    cfg = load_broker_config(_write(tmp_path, doc))
    assert "dev@creator-engine.example" in cfg.policy.authorized_emails
    assert isinstance(cfg.policy.authorized_logins, frozenset)


def test_forbidden_branches_default_to_floor_when_absent(tmp_path):
    doc = _doc()
    doc["policy"].pop("forbidden_branches", None)
    cfg = load_broker_config(_write(tmp_path, doc))
    assert isinstance(cfg.policy.forbidden_branches, frozenset)  # loader tolerates absence


@pytest.mark.parametrize("bad_repo", ["", "noowner", "a/b/c", "a b/c"])
def test_malformed_repo_is_refused(tmp_path, bad_repo):
    with pytest.raises(BrokerConfigError):
        load_broker_config(_write(tmp_path, _doc(repo=bad_repo)))


def test_empty_seat_table_is_refused(tmp_path):
    with pytest.raises(BrokerConfigError):
        load_broker_config(_write(tmp_path, _doc(seats={})))


def test_empty_author_allow_list_is_refused(tmp_path):
    doc = _doc()
    doc["policy"]["authorized_emails"] = []
    doc["policy"]["authorized_logins"] = []
    with pytest.raises(BrokerConfigError):
        load_broker_config(_write(tmp_path, doc))


def test_empty_namespace_list_is_refused(tmp_path):
    doc = _doc()
    doc["policy"]["allowed_branch_namespaces"] = []
    with pytest.raises(BrokerConfigError):
        load_broker_config(_write(tmp_path, doc))


@pytest.mark.parametrize(
    "mutate",
    [
        lambda s: s.pop("app_id"),
        lambda s: s.pop("app_owner"),
        lambda s: s.pop("pem_path"),
        lambda s: s.update(app_id=""),
        lambda s: s.update(installation_id=0),
        lambda s: s.update(installation_id=-3),
        lambda s: s.update(installation_id="notanint"),
    ],
)
def test_malformed_seat_is_refused(tmp_path, mutate):
    doc = _doc()
    mutate(doc["seats"]["dev-4"])
    with pytest.raises(BrokerConfigError):
        load_broker_config(_write(tmp_path, doc))


def test_missing_file_is_refused(tmp_path):
    with pytest.raises(BrokerConfigError):
        load_broker_config(tmp_path / "nope.json")


def test_invalid_json_is_refused(tmp_path):
    p = tmp_path / "broker.json"
    p.write_text("{ not json", encoding="utf-8")
    with pytest.raises(BrokerConfigError):
        load_broker_config(p)


def test_seat_repr_hides_app_id_and_pem(tmp_path):
    cfg = load_broker_config(_write(tmp_path, _doc()))
    r = repr(cfg.seat("dev-4"))
    assert "4085526" not in r
    assert "/dev/shm" not in r
    assert "cedev4vps-coder" in r  # the owner identity is fine to show


def test_pem_path_user_expansion(tmp_path):
    doc = _doc()
    doc["seats"]["dev-4"]["pem_path"] = "~/keys/dev4.pem"
    cfg = load_broker_config(_write(tmp_path, doc))
    assert not cfg.seat("dev-4").pem_path.startswith("~")


def test_load_from_mapping_directly():
    # the loader also accepts an already-parsed mapping (for the CLI / tests)
    cfg = load_broker_config(_doc())
    assert cfg.repo == "creator-engine/creator-engine"

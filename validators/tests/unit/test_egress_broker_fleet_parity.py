from __future__ import annotations

import configparser
import json
import shutil
from pathlib import Path

import pytest


FLEET_SEATS_PATH = Path("deploy/egress-broker/fleet-seats.json")
BROKER_APP_SEATS_PATH = Path("tools/egress-broker/apps.example.json")
REQUIRED_ENV_KEYS = (
    "CE_EGRESS_BROKER_SOCKET",
    "CE_EGRESS_BROKER_SEAT",
    "CE_EGRESS_BROKER_TARGET_CONTAINER",
    "CE_EGRESS_BROKER_CONTAINER_RUNTIME",
    "CE_EGRESS_BROKER_EXPECTED_PEER_UID",
    "CE_EGRESS_BROKER_EXPECTED_PEER_GID",
    "CE_EGRESS_BROKER_REPO",
    "CE_EGRESS_BROKER_CONFIG",
)
STATIC_FLEET_PATHS = {
    "dev-3": {
        "service": Path("deploy/systemd/ce-egress-broker.service"),
        "socket": Path("deploy/systemd/ce-egress-broker.socket"),
        "env": Path("deploy/egress-broker/dev-3/ce-egress-broker.env"),
        "liveness_service": Path("deploy/systemd/ce-egress-broker-liveness.service"),
        "liveness_timer": Path("deploy/systemd/ce-egress-broker-liveness.timer"),
    },
    "dev-4": {
        "service": Path("deploy/systemd/ce-egress-broker-dev-4.service"),
        "socket": Path("deploy/systemd/ce-egress-broker-dev-4.socket"),
        "env": Path("deploy/egress-broker/dev-4/ce-egress-broker.env"),
        "liveness_service": Path("deploy/systemd/ce-egress-broker-dev-4-liveness.service"),
        "liveness_timer": Path("deploy/systemd/ce-egress-broker-dev-4-liveness.timer"),
    },
}
PREFLIGHT_BY_SEAT = {
    "dev-3": "/usr/bin/env deploy/egress-broker/v1/preflight-peer-identity.sh --env-file %h/.config/creator-engine/ce-egress-broker.env",
    "dev-4": "/usr/bin/env deploy/egress-broker/v1/preflight-peer-identity.sh --env-file /etc/creator-engine/ce-egress-broker-dev-4.env",
}


def _load_json(repo_root: Path, relative_path: Path) -> dict[str, object]:
    return json.loads((repo_root / relative_path).read_text(encoding="utf-8"))


def _load_unit(repo_root: Path, relative_path: Path) -> configparser.ConfigParser:
    parser = configparser.ConfigParser(interpolation=None, strict=False)
    parser.read(repo_root / relative_path, encoding="utf-8")
    return parser


def _load_env(repo_root: Path, relative_path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in (repo_root / relative_path).read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        key, value = line.split("=", 1)
        assert key not in values, f"duplicate environment key: {key}"
        values[key] = value
    return values


def _declared_fleet_seats(repo_root: Path) -> tuple[str, ...]:
    fleet = _load_json(repo_root, FLEET_SEATS_PATH)
    app_table = _load_json(repo_root, BROKER_APP_SEATS_PATH)
    source = fleet["seat_source"]
    assert source == str(BROKER_APP_SEATS_PATH)
    app_seats = app_table["seats"]
    assert isinstance(app_seats, dict)
    seats = fleet["seats"]
    assert isinstance(seats, list)
    assert seats == sorted(set(seats)), "fleet seats must be sorted and unique"
    assert seats, "fleet must declare at least one broker seat"
    assert set(seats) <= set(app_seats), "fleet seats must be declared by the broker app table"
    return tuple(seats)


def _broker_unit_names(repo_root: Path, pattern: str) -> set[str]:
    return {path.name for path in (repo_root / "deploy/systemd").glob(pattern)}


def _assert_no_orphan_static_units(repo_root: Path) -> None:
    expected = {
        kind: {paths[kind].name for paths in STATIC_FLEET_PATHS.values()}
        for kind in ("service", "socket", "liveness_service", "liveness_timer")
    }
    broker_services = {
        name
        for name in _broker_unit_names(repo_root, "ce-egress-broker*.service")
        if not name.endswith("-liveness.service")
    }
    assert broker_services == expected["service"], "broker service exists without a fleet entry"
    assert _broker_unit_names(repo_root, "ce-egress-broker*.socket") == expected[
        "socket"
    ], "broker socket exists without a fleet entry"
    assert _broker_unit_names(repo_root, "ce-egress-broker*-liveness.service") == expected[
        "liveness_service"
    ], "broker liveness service exists without a fleet entry"
    assert _broker_unit_names(repo_root, "ce-egress-broker*-liveness.timer") == expected[
        "liveness_timer"
    ], "broker liveness timer exists without a fleet entry"


def _assert_activation_preflight(service: configparser.ConfigParser, seat: str) -> None:
    preflight = service["Service"].get("ExecStartPre", "")
    assert preflight.startswith(PREFLIGHT_BY_SEAT[seat]), "broker activation must run preflight"
    assert ' --target-container "$CE_EGRESS_BROKER_TARGET_CONTAINER"' in preflight
    assert ' --container-runtime "$CE_EGRESS_BROKER_CONTAINER_RUNTIME"' in preflight


def test_declared_fleet_seats_have_complete_static_push_paths(repo_root: Path):
    """Every declared fleet seat has complete, tracked broker structure."""
    seats = _declared_fleet_seats(repo_root)
    assert set(seats) == set(STATIC_FLEET_PATHS), "declare static broker structure for every fleet seat"
    for seat in seats:
        paths = STATIC_FLEET_PATHS[seat]
        for path in paths.values():
            assert (repo_root / path).is_file(), f"{seat} is missing {path}"

        service = _load_unit(repo_root, paths["service"])
        socket = _load_unit(repo_root, paths["socket"])
        liveness_service = _load_unit(repo_root, paths["liveness_service"])
        liveness_timer = _load_unit(repo_root, paths["liveness_timer"])
        env = _load_env(repo_root, paths["env"])
        assert set(REQUIRED_ENV_KEYS) <= set(env)
        assert all(env[key] for key in REQUIRED_ENV_KEYS)
        assert "EnvironmentFile" in service["Service"]
        assert service["Service"]["Restart"] == "on-failure"
        assert service["Service"]["Sockets"] == socket["Socket"]["Service"].replace(
            ".service", ".socket"
        )
        assert socket["Socket"]["ListenStream"] == f"/run/ce-egress/{seat}.sock"
        assert socket["Socket"]["Service"] == paths["service"].name
        _assert_activation_preflight(service, seat)
        for flag in (
            "--socket",
            "--seat",
            "--expected-peer-uid",
            "--expected-peer-gid",
            "--host-repo-path",
            "--config",
        ):
            assert flag in service["Service"]["ExecStart"]
        assert service["Unit"]["OnFailure"] == paths["liveness_service"].name
        assert service["Unit"]["StartLimitIntervalSec"] == "5m"
        assert service["Unit"]["StartLimitBurst"] == "3"
        assert liveness_service["Service"]["Type"] == "oneshot"
        liveness_command = liveness_service["Service"]["ExecStart"]
        assert f"systemctl is-active {paths['service'].name}" in liveness_command
        assert "if test \"$state\" = active; then" in liveness_command
        assert "systemd-cat" in liveness_command
        assert "-p info" in liveness_command
        assert "else" in liveness_command
        assert "-p err; exit 1; fi" in liveness_command
        assert liveness_timer["Timer"]["Unit"] == paths["liveness_service"].name
        assert liveness_timer["Timer"]["OnBootSec"] == "5m"
        assert liveness_timer["Timer"]["OnUnitActiveSec"] == "5m"
        assert liveness_timer["Timer"]["Persistent"] == "true"

    _assert_no_orphan_static_units(repo_root)


def test_broker_activation_wiring_rejects_removed_preflight(repo_root: Path, tmp_path: Path):
    """The wiring assertion must fail if a broker starts without its preflight."""
    source = repo_root / STATIC_FLEET_PATHS["dev-4"]["service"]
    service_path = tmp_path / source.name
    service_path.write_text(
        "\n".join(
            line
            for line in source.read_text(encoding="utf-8").splitlines()
            if not line.startswith("ExecStartPre=")
        )
        + "\n",
        encoding="utf-8",
    )
    parser = configparser.ConfigParser(interpolation=None, strict=False)
    parser.read(service_path, encoding="utf-8")

    with pytest.raises(AssertionError, match="broker activation must run preflight"):
        _assert_activation_preflight(parser, "dev-4")


@pytest.mark.parametrize(
    ("file_name", "content", "message"),
    (
        ("ce-egress-broker-dev-9.service", "[Service]\nType=simple\n", "broker service exists without a fleet entry"),
        ("ce-egress-broker-dev-9.socket", "[Socket]\n", "broker socket exists without a fleet entry"),
        (
            "ce-egress-broker-dev-9-liveness.service",
            "[Service]\nType=oneshot\n",
            "broker liveness service exists without a fleet entry",
        ),
        (
            "ce-egress-broker-dev-9-liveness.timer",
            "[Timer]\nUnit=ce-egress-broker-dev-9-liveness.service\n",
            "broker liveness timer exists without a fleet entry",
        ),
    ),
    ids=("service", "socket", "liveness-service", "liveness-timer"),
)
def test_static_fleet_discovery_rejects_orphan_required_unit_class(
    repo_root: Path, tmp_path: Path, file_name: str, content: str, message: str
):
    """Every required broker unit class rejects an orphan outside the fleet."""
    systemd_root = tmp_path / "deploy/systemd"
    systemd_root.mkdir(parents=True)
    for source in (repo_root / "deploy/systemd").glob("ce-egress-broker*"):
        shutil.copy2(source, systemd_root / source.name)
    (systemd_root / file_name).write_text(content, encoding="utf-8")

    with pytest.raises(AssertionError, match=message):
        _assert_no_orphan_static_units(tmp_path)

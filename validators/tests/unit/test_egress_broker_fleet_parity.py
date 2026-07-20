from __future__ import annotations

import configparser
import json
from pathlib import Path


FLEET_SEATS_PATH = Path("deploy/egress-broker/fleet-seats.json")
BROKER_APP_SEATS_PATH = Path("tools/egress-broker/apps.example.json")
REQUIRED_ENV_KEYS = (
    "CE_EGRESS_BROKER_SOCKET",
    "CE_EGRESS_BROKER_SEAT",
    "CE_EGRESS_BROKER_EXPECTED_PEER_UID",
    "CE_EGRESS_BROKER_EXPECTED_PEER_GID",
    "CE_EGRESS_BROKER_REPO",
    "CE_EGRESS_BROKER_CONFIG",
)


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


def test_declared_fleet_seats_have_complete_static_push_paths(repo_root: Path):
    """Every declared fleet seat has a tracked configured systemd push path."""
    seats = _declared_fleet_seats(repo_root)

    expected_paths = {
        "dev-3": {
            "service": Path("deploy/systemd/ce-egress-broker.service"),
            "socket": Path("deploy/systemd/ce-egress-broker.socket"),
        },
        "dev-4": {
            "service": Path("deploy/systemd/ce-egress-broker-dev-4.service"),
            "socket": Path("deploy/systemd/ce-egress-broker-dev-4.socket"),
            "env": Path("deploy/egress-broker/dev-4/ce-egress-broker.env"),
            "config": Path("deploy/egress-broker/dev-4/broker-dev4.json"),
        },
    }
    expected_environment_files = {
        "dev-3": "%h/.config/creator-engine/ce-egress-broker.env",
        "dev-4": "/etc/creator-engine/ce-egress-broker-dev-4.env",
    }

    assert set(seats) == set(expected_paths), "declare a static push path for every fleet seat"
    for seat in seats:
        paths = expected_paths[seat]
        for path in paths.values():
            assert (repo_root / path).is_file(), f"{seat} is missing {path}"

        service = _load_unit(repo_root, paths["service"])
        socket = _load_unit(repo_root, paths["socket"])
        assert service["Service"]["EnvironmentFile"] == expected_environment_files[seat]
        assert service["Service"]["Restart"] == "on-failure"
        assert service["Service"]["Sockets"] == socket["Socket"]["Service"].replace(
            ".service", ".socket"
        )
        assert socket["Socket"]["ListenStream"] == f"/run/ce-egress/{seat}.sock"
        assert socket["Socket"]["Service"] == paths["service"].name
        for flag in (
            "--socket",
            "--seat",
            "--expected-peer-uid",
            "--expected-peer-gid",
            "--host-repo-path",
            "--config",
        ):
            assert flag in service["Service"]["ExecStart"]

    dev4 = expected_paths["dev-4"]
    env = _load_env(repo_root, dev4["env"])
    assert tuple(env) == REQUIRED_ENV_KEYS
    assert env == {
        "CE_EGRESS_BROKER_SOCKET": "/run/ce-egress/dev-4.sock",
        "CE_EGRESS_BROKER_SEAT": "dev-4",
        "CE_EGRESS_BROKER_EXPECTED_PEER_UID": "1004",
        "CE_EGRESS_BROKER_EXPECTED_PEER_GID": "1004",
        "CE_EGRESS_BROKER_REPO": "/workspace/creator-engine",
        "CE_EGRESS_BROKER_CONFIG": "/etc/ce-egress/broker-dev4.json",
    }
    config = _load_json(repo_root, dev4["config"])
    seats_config = config["seats"]
    assert isinstance(seats_config, dict)
    assert set(seats_config) == {"dev-4"}


def test_dev4_liveness_configuration_observes_absence_and_crash_loops(repo_root: Path):
    service = _load_unit(repo_root, Path("deploy/systemd/ce-egress-broker-dev-4.service"))
    check = _load_unit(repo_root, Path("deploy/systemd/ce-egress-broker-dev-4-liveness.service"))
    timer = _load_unit(repo_root, Path("deploy/systemd/ce-egress-broker-dev-4-liveness.timer"))

    assert service["Unit"]["OnFailure"] == "ce-egress-broker-dev-4-liveness.service"
    assert service["Unit"]["StartLimitIntervalSec"] == "5m"
    assert service["Unit"]["StartLimitBurst"] == "3"
    assert service["Service"]["Restart"] == "on-failure"
    assert check["Service"]["Type"] == "oneshot"
    assert "systemctl is-active ce-egress-broker-dev-4.service" in check["Service"]["ExecStart"]
    assert "systemd-cat" in check["Service"]["ExecStart"]
    assert "-p err" in check["Service"]["ExecStart"]
    assert 'test "$state" = active' in check["Service"]["ExecStart"]
    assert timer["Timer"]["Unit"] == "ce-egress-broker-dev-4-liveness.service"
    assert timer["Timer"]["OnBootSec"] == "5m"
    assert timer["Timer"]["OnUnitActiveSec"] == "5m"
    assert timer["Timer"]["Persistent"] == "true"

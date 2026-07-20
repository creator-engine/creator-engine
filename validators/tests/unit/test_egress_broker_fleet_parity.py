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
        assert f"systemctl is-active {paths['service'].name}" in liveness_service["Service"]["ExecStart"]
        assert "systemd-cat" in liveness_service["Service"]["ExecStart"]
        assert "-p err" in liveness_service["Service"]["ExecStart"]
        assert 'test "$state" = active' in liveness_service["Service"]["ExecStart"]
        assert liveness_timer["Timer"]["Unit"] == paths["liveness_service"].name
        assert liveness_timer["Timer"]["OnBootSec"] == "5m"
        assert liveness_timer["Timer"]["OnUnitActiveSec"] == "5m"
        assert liveness_timer["Timer"]["Persistent"] == "true"

    broker_services = {
        path.name
        for path in (repo_root / "deploy/systemd").glob("ce-egress-broker*.service")
        if "liveness" not in path.name and "self-review" not in path.name
    }
    assert broker_services == {paths["service"].name for paths in STATIC_FLEET_PATHS.values()}

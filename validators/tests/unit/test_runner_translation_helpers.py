from creator_engine_validator.runner import (
    LAUNCH_PROBE_CONTRACT,
    argv_carries_launch_probe_contract,
    bind_launch_owned_probe_contract,
    launch_probe_container_name,
)


def test_public_probe_helper_binds_after_docker_run_rm():
    argv = bind_launch_owned_probe_contract(
        ("docker", "run", "--rm", "--user", "1001", "image@sha256:" + "a" * 64, "echo"),
        run_id="run/owned-7",
    )

    assert argv[:3] == ("docker", "run", "--rm")
    assert argv[3] == "--name"
    name = argv[4]
    assert name.startswith("ce-probe-run-owned-7-")
    assert argv_carries_launch_probe_contract(argv, run_id="run/owned-7", name=name)
    assert f"creator-engine.probe-contract={LAUNCH_PROBE_CONTRACT}" in argv


def test_launch_probe_container_name_is_stable_and_public():
    assert launch_probe_container_name("run/owned-7") == launch_probe_container_name("run/owned-7")

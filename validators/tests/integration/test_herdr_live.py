"""Optional live herdr binary probe for ce-ops#217 U3."""

from __future__ import annotations

from pathlib import Path

import pytest

from creator_engine_validator.runner.herdr_session import SubprocessHerdrCommandRunner


HERDR_LIVE_BINARY = Path.home() / "herdr-ce" / "target" / "release" / "herdr"


@pytest.mark.skipif(
    not HERDR_LIVE_BINARY.is_file(),
    reason=f"live herdr binary is unavailable at {HERDR_LIVE_BINARY}",
)
def test_live_herdr_binary_can_be_invoked_safely():
    runner = SubprocessHerdrCommandRunner(timeout_seconds=5)
    completed = runner.run([str(HERDR_LIVE_BINARY), "--help"])
    assert completed.returncode == 0

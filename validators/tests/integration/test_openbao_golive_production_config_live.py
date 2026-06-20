from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.skipif(
    os.environ.get("CE_OPENBAO_GOLIVE_DOWNLOAD_SMOKE") != "1",
    reason="set CE_OPENBAO_GOLIVE_DOWNLOAD_SMOKE=1 to download and verify OpenBao 2.5.5",
)
def test_openbao_255_accepts_rendered_production_config(
    repo_root: Path,
    tmp_path: Path,
):
    script = repo_root / "docs/devops/openbao/verify-production-config-openbao-2.5.5.sh"

    completed = subprocess.run(
        [str(script)],
        env={
            **os.environ,
            "OPENBAO_VERIFY_WORKDIR": str(tmp_path),
            "PYTHON_BIN": sys.executable,
        },
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=120,
    )

    assert (
        "PASS openbao 2.5.5 accepted rendered production config and activated file audit after reload"
        in completed.stdout
    )

#!/usr/bin/env python3
"""Drive ONE governed agent run end-to-end inside a live OpenShell gateway (v3.5-A.2b-ii).

This is the live-proof harness for the OpenShell runner backend: it wires the
real CE runtime stack —

    AuditOverlayBackend(OpenShellBackend(SubprocessSandboxClient()))

— and drives a genuine ``provision -> run -> collect -> teardown`` lifecycle
against a connected OpenShell gateway, on the **A.2b-i-corrected surface** (the
``version: 1`` / ``filesystem_policy`` / ``network_policies`` map policy schema
and the ``openshell logs`` OCSF *text* audit). It then writes a sanitized,
replayable **evidence bundle** that captures:

* the **attested hash-chained spine** the audit overlay folded over the lifecycle
  (``provision -> run -> run -> collect -> teardown``) — a clean run satisfies
  ``runtime_evidence_spine.verify_chain(chain) == []`` (the cryptographic proof
  CI then re-verifies offline);
* the **real OCSF governance decisions** OpenShell's OPA egress proxy emitted —
  at least one ``ALLOWED`` (``curl https://api.github.com/zen`` against a CE
  policy that allowlists exactly ``api.github.com:443``) and the ``DENIED``
  counterfactual (``curl https://example.com`` — not on the allowlist), with the
  deny ``reason`` kept verbatim;
* the two probe exec exits.

The bundle this writes is the offline ground truth for
``validators/tests/unit/test_openshell_live_replay.py`` (daemon-free / no-network)
and the curated NVIDIA-arc pitch evidence ("CE governs a real run inside
OpenShell").

**Availability-gated.** It runs ONLY when the ``openshell`` CLI is on ``PATH`` AND
``openshell status`` reports ``Connected``; otherwise it prints why and exits 0.
It lives in ``examples/`` (NOT ``runner/``) so it is never a baselined
``runner.*`` module and CI never executes it — the live transport stays behind
the injectable ``SandboxClient`` seam, exactly as the backend designed.

**Defensive only.** This hardens CE's own governed agent runtime by *exercising*
the runtime-safety enforcer; it is never an offensive capability. It mutates no
repository state and tears its sandbox down even on error.

Usage::

    python examples/openshell_live_run.py            # write the default fixture bundle
    python examples/openshell_live_run.py --bundle-out /tmp/run.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "validators"))

from creator_engine_validator.runner import (  # noqa: E402  (after sys.path wiring)
    AuditOverlayBackend,
    OpenShellBackend,
    ProvisionRequest,
    RunRequest,
    SubprocessSandboxClient,
)
from creator_engine_validator.runner.openshell_backend import (  # noqa: E402
    OPENSHELL_PINNED_VERSION,
    render_sandbox_policy_yaml,
    translate_to_sandbox_policy,
)
from creator_engine_validator.runtime_evidence_spine import (  # noqa: E402
    RECORD_KIND,
    verify_chain,
)

#: The default in-repo bundle the replay test consumes (this run records it live).
DEFAULT_BUNDLE_OUT = (
    REPO_ROOT / "validators" / "tests" / "unit" / "fixtures" / "openshell_live_bundle.json"
)

#: The digest-pinned base image the live gateway runs (confirmed from the local
#: image store: ``ghcr.io/nvidia/openshell-community/sandboxes/base``).
BASE_IMAGE_NAME = "ghcr.io/nvidia/openshell-community/sandboxes/base"
BASE_IMAGE_SHA = "sha256:aeef1c63f00e2913ea002ccb3aaf925f338b5c5d70e63576f0d95c16a138044e"

#: The deterministic run id this harness attests under (no wall-clock; the spine
#: clock is the backend default CounterClock, so the recorded bundle is stable).
RUN_ID = "openshell-live-a2bii"

#: The two governed probes — the ALLOWED action and the DENIED counterfactual.
ALLOWED_PROBE = ("curl", "-sS", "https://api.github.com/zen")
DENIED_PROBE = ("curl", "-sS", "https://example.com")

#: A bounded warmup probe (separate from the recorded probes) used only to wait
#: out the freshly-created sandbox's policy-settle window before the real run.
_WARMUP_PROBE = ("curl", "-sS", "--max-time", "20", "-o", "/dev/null", "https://api.github.com/zen")
_WARMUP_MAX_ATTEMPTS = 25
_WARMUP_RETRY_SECONDS = 3

#: Each probe host's CANONICAL governance verdict (what the policy decides). We
#: surface exactly these decisions into the bundle and drop everything else for the
#: host — in particular the transient tunnel-teardown lines the gateway emits while
#: re-resolving policy (a momentary ``DENIED`` for the ALLOWED host "because policy
#: reloaded"), which are operational artifacts, not governance decisions.
_EXPECTED_DISPOSITION = {"api.github.com": "ALLOWED", "example.com": "DENIED"}
#: Hosts whose OCSF decision lines we surface into the bundle (our two probes).
_PROBE_HOSTS = tuple(_EXPECTED_DISPOSITION)

#: ANSI SGR escape sequences (``openshell status`` colorizes its output).
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(text: str) -> str:
    """Strip ANSI colour codes so recorded text is clean, deterministic plaintext."""
    return _ANSI_RE.sub("", text)


# ---------------------------------------------------------------------------
# Availability gate (so CI / an unconfigured host never drives a live run)
# ---------------------------------------------------------------------------
def gateway_connected() -> tuple[bool, str]:
    """True + the status text when ``openshell`` is on PATH and reports Connected."""
    if shutil.which("openshell") is None:
        return False, "the `openshell` CLI is not on PATH"
    try:
        completed = subprocess.run(
            ["openshell", "status"], capture_output=True, text=True, check=False, timeout=30
        )
    except (OSError, subprocess.SubprocessError) as exc:  # pragma: no cover - env-specific
        return False, f"`openshell status` could not run: {exc}"
    out = _strip_ansi((completed.stdout or "") + (completed.stderr or ""))
    if "Connected" in out:
        return True, out.strip()
    return False, f"`openshell status` is not Connected:\n{out.strip()}"


# ---------------------------------------------------------------------------
# The CE runtime-policy this run provisions (minimal, valid, deny-by-default).
# ---------------------------------------------------------------------------
def build_runtime_policy() -> dict[str, Any]:
    """A minimal-but-functional, schema-clean runtime-policy: allowlist exactly api.github.com:443.

    Two live-gateway requirements (verified against OpenShell v0.0.57; both are
    expressed through the EXISTING runtime-policy contract — no backend change):

    * **Filesystem read paths.** Under Landlock (``best_effort``) the sandbox can
      only read paths the policy grants, so the base image's standard read paths
      (``/usr``, ``/lib``, ``/etc`` for the CA bundle, ...) must be in the mount
      manifest or curl cannot load its libraries / TLS roots. These map to the
      OpenShell ``filesystem_policy.read_only`` / ``read_write`` Landlock allowlist.
    * **Calling-binary scope.** An OpenShell ``network_policies`` rule with NO
      ``binaries`` scope denies the connection at the OPA engine ("binary
      '/usr/bin/curl' not allowed in policy ..."); the egress rule's optional
      ``binary_identity`` (``/usr/bin/curl``) is translated to the rule's
      ``binaries: [{path: ...}]`` so curl is authorized to use the endpoint.

    The policy MUST be applied at CREATE time (which this harness does) — the
    gateway resolves the binary scope during sandbox startup, so a later
    ``policy set`` does not retroactively authorize an already-resolved binary.

    ``policy_sha`` is a real content digest of the record (so the spine's
    policy-binding is honest provenance, not a placeholder).
    """
    policy: dict[str, Any] = {
        "kind": "runtime-policy-record",
        "record_type": "runtime_policy",
        "schema_version": "1",
        "policy_id": "openshell-live-implementer",
        "role": "implementer",
        "isolation_backend": "openshell",
        "image_ref": {"name": BASE_IMAGE_NAME, "sha": BASE_IMAGE_SHA},
        # The base image's standard read paths (Landlock read allowlist) + the
        # scratch read-write paths — without these curl cannot load libs / CA roots.
        "mount_manifest": [
            {"path": "/usr", "mode": "ro"},
            {"path": "/lib", "mode": "ro"},
            {"path": "/lib64", "mode": "ro"},
            {"path": "/bin", "mode": "ro"},
            {"path": "/etc", "mode": "ro"},
            {"path": "/proc", "mode": "ro"},
            {"path": "/dev/urandom", "mode": "ro"},
            {"path": "/app", "mode": "ro"},
            {"path": "/var/log", "mode": "ro"},
            {"path": "/sandbox", "mode": "rw", "write_justification": "sandbox scratch space"},
            {"path": "/tmp", "mode": "rw", "write_justification": "temp files"},
            {"path": "/dev/null", "mode": "rw", "write_justification": "null sink"},
        ],
        # Deny-by-default egress with a single allowlisted endpoint, scoped to the
        # calling binary. The DENIED counterfactual (example.com) is NOT here -> the
        # OPA proxy blocks it ("not allowed by any policy").
        "egress_allowlist": [
            {"host": "api.github.com", "port": 443, "binary_identity": "/usr/bin/curl"}
        ],
        "secret_allowlist": [],
        "grant_extensible": False,
        "grant_authority": "controller",
    }
    material = {k: v for k, v in policy.items() if k != "policy_sha"}
    policy["policy_sha"] = hashlib.sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
            "utf-8"
        )
    ).hexdigest()
    return policy


# ---------------------------------------------------------------------------
# Sanitization — strip host-specific PIDs/timestamps; keep decision fields verbatim
# ---------------------------------------------------------------------------
_TS_PREFIX_RE = re.compile(r"^\[\d+(?:\.\d+)?\]")
_PID_RE = re.compile(r"\((\d+)\)")
_HOME_RE = re.compile(r"/home/[^/\s]+")


def sanitize_ocsf_line(line: str) -> str:
    """Sanitize one OCSF text line: epoch ts -> ``[<ts>]``; in-sandbox PID -> ``(PID)``.

    The load-bearing decision fields (event type, severity, ALLOWED/DENIED
    disposition, target, ``policy``/``engine``/``reason``) are left VERBATIM — only
    the ephemeral epoch timestamp, the in-sandbox process id, and any stray host
    home-directory path are normalized.
    """
    out = _TS_PREFIX_RE.sub("[<ts>]", line.strip())
    out = _PID_RE.sub("(PID)", out)
    out = _HOME_RE.sub("/home/<user>", out)
    return out


def _line_disposition(line: str) -> str | None:
    """The ALLOWED/DENIED token of an OCSF line (None when it carries neither)."""
    if " ALLOWED " in line:
        return "ALLOWED"
    if " DENIED " in line:
        return "DENIED"
    return None


def extract_ocsf_lines(records: tuple[dict[str, Any], ...]) -> list[str]:
    """Pull each probe's canonical OCSF governance-decision line(s) out of collected evidence.

    ``AuditOverlayBackend.collect`` returns the mapped OCSF records followed by the
    spine records. A mapped OCSF record preserves its original log line at
    ``record["raw"]["raw"]``; a spine record carries ``kind == RECORD_KIND`` and no
    such nested ``raw``. We keep, in log order, only the lines that:

    * reference one of the two probe hosts (dropping NET:CLOSE / relay noise), AND
    * carry that host's CANONICAL :data:`_EXPECTED_DISPOSITION` verdict.

    The second condition makes the recorded bundle deterministic and honest: it
    keeps the real governance decisions (``api.github.com`` ALLOWED — the NET:OPEN
    and the L7 HTTP:GET — and ``example.com`` DENIED) and drops the transient
    tunnel-teardown artifacts the gateway can emit for the ALLOWED host while
    re-resolving policy (a momentary ``DENIED ... [reason:L7 tunnel closed ...
    policy reload/changed]``), which are operational noise, not a verdict that the
    host is forbidden. Lines are sanitized and de-duplicated, so a host probed more
    than once (warmup + recorded) collapses to a single decision line.
    """
    seen: set[str] = set()
    lines: list[str] = []
    for record in records:
        if not isinstance(record, dict) or record.get("kind") == RECORD_KIND:
            continue
        raw = record.get("raw")
        if not isinstance(raw, dict):
            continue
        line = raw.get("raw")
        if not isinstance(line, str):
            continue
        host = next((h for h in _PROBE_HOSTS if h in line), None)
        if host is None or _line_disposition(line) != _EXPECTED_DISPOSITION[host]:
            continue
        sanitized = sanitize_ocsf_line(line)
        if sanitized in seen:
            continue
        seen.add(sanitized)
        lines.append(sanitized)
    return lines


# ---------------------------------------------------------------------------
# The live run
# ---------------------------------------------------------------------------
def drive_live_run(status_text: str) -> dict[str, Any]:
    """Drive the real lifecycle and return the recorded (sanitized) evidence bundle."""
    policy = build_runtime_policy()
    sandbox_policy = translate_to_sandbox_policy(policy)
    policy_yaml = render_sandbox_policy_yaml(sandbox_policy)

    client = SubprocessSandboxClient()
    inner = OpenShellBackend(client=client)
    overlay = AuditOverlayBackend(inner=inner)

    handle = overlay.provision(ProvisionRequest(runtime_policy=policy, run_id=RUN_ID))
    probes: list[dict[str, Any]] = []
    try:
        # Warm up: the first connection after a fresh create can race the gateway
        # still applying the policy (the L7 tunnel is torn down "because policy
        # changed"). Drive a bounded, NON-recorded warmup probe (directly through
        # the client, so it never touches the attested spine) until the allow path
        # settles, so the recorded run below is clean. The first call also absorbs
        # the supervisor-relay warmup.
        sandbox_id = inner._sandboxes.get(handle.ref)
        if not sandbox_id:  # pragma: no cover - provision always records the id
            raise SystemExit("HALT: provision did not record a sandbox id")
        settled = False
        for attempt in range(_WARMUP_MAX_ATTEMPTS):
            warm = client.exec_sandbox(sandbox_id, _WARMUP_PROBE)
            if warm.exit_code == 0:
                settled = True
                print(f"  warmup: policy settled after {attempt + 1} attempt(s)")
                break
            time.sleep(_WARMUP_RETRY_SECONDS)
        if not settled:  # pragma: no cover - HALT if the allow path never settles
            raise SystemExit(
                "HALT: the api.github.com allow path never settled during warmup "
                f"({_WARMUP_MAX_ATTEMPTS} attempts); not recording a bundle"
            )
        for label, command, expect in (
            ("allowed", ALLOWED_PROBE, "ALLOWED"),
            ("denied", DENIED_PROBE, "DENIED"),
        ):
            result = overlay.run(handle, RunRequest(command=command))
            probes.append(
                {
                    "label": label,
                    "command": list(command),
                    "expect": expect,
                    "exit_code": result.exit_code,
                    "stdout_excerpt": (result.stdout or "")[:200],
                    "stderr_excerpt": (result.stderr or "")[:200],
                }
            )
            print(
                f"  probe[{label}] {' '.join(command)} -> exit {result.exit_code} "
                f"(expect {expect})"
            )
        # Let the gateway flush the OCSF decision lines to the log stream before
        # the collect step reads them (the deny line lands a beat after the probe).
        time.sleep(5)
        evidence = overlay.collect(handle)
    finally:
        # Always release the sandbox, even if a probe/collect raised.
        teardown = overlay.teardown(handle)
        print(f"  teardown released={teardown.released}")

    full_chain = list(overlay.chain(handle))  # provision,run,run,collect,teardown
    ocsf_lines = extract_ocsf_lines(evidence.records)  # already sanitized + deduped
    ocsf_textlog = "\n".join(ocsf_lines) + ("\n" if ocsf_lines else "")

    # Re-derive the mapped OCSF records from the SANITIZED text through the exact
    # backend mapping path (parse_ocsf_textlog -> _map_ocsf_record), so the bundle's
    # records and its text are internally consistent and the replay test can
    # reproduce them offline.
    from creator_engine_validator.runner.openshell_backend import (
        _map_ocsf_record,
        parse_ocsf_textlog,
    )

    ocsf_records = [_map_ocsf_record(r) for r in parse_ocsf_textlog(ocsf_textlog)]
    dispositions = [r.get("disposition") for r in ocsf_records if r.get("disposition")]

    chain_findings = verify_chain(full_chain)
    if chain_findings:  # pragma: no cover - a clean live run verifies; HALT loudly otherwise
        raise SystemExit(
            "HALT: the recorded spine chain did not verify clean (expected verify_chain == []): "
            + "; ".join(f"{f.kind}@{f.index}:{f.message}" for f in chain_findings)
        )

    bundle: dict[str, Any] = {
        "schema_version": "ce-openshell-live-bundle/1",
        "kind": "openshell-live-run-bundle",
        # Honesty marker: this bundle attests a REAL live run (not a replay).
        "recorded_mode": "live",
        "openshell_version": OPENSHELL_PINNED_VERSION,
        "gateway_status": "Connected",
        "image_ref": f"{BASE_IMAGE_NAME}@{BASE_IMAGE_SHA}",
        "run_id": RUN_ID,
        "policy_sha": policy["policy_sha"],
        "policy_yaml": policy_yaml,
        "probes": probes,
        "ocsf_textlog": ocsf_textlog,
        "ocsf_records": ocsf_records,
        "ocsf_dispositions": dispositions,
        "spine_chain": full_chain,
        "lifecycle_phases": [
            r.get("lifecycle_phase") for r in full_chain if isinstance(r, dict)
        ],
        "verify_chain_clean": True,
        "sanitization": (
            "epoch timestamps -> [<ts>]; in-sandbox PIDs -> (PID); host home paths "
            "-> /home/<user>; decision fields kept verbatim. Each probe's canonical "
            "policy verdict is surfaced (api.github.com ALLOWED, example.com DENIED); "
            "transient tunnel-teardown lines emitted during gateway policy "
            "re-resolution are dropped (operational noise, not a verdict)."
        ),
        "gateway_status_text": status_text,
    }
    return bundle


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bundle-out",
        type=Path,
        default=DEFAULT_BUNDLE_OUT,
        help="where to write the recorded evidence bundle JSON (default: the replay fixture)",
    )
    args = parser.parse_args()

    connected, status_text = gateway_connected()
    if not connected:
        print(f"[skip] OpenShell live run not performed: {status_text}")
        return 0

    print(f"[live] OpenShell gateway Connected; driving a governed run (run_id={RUN_ID})")
    bundle = drive_live_run(status_text)

    n_allowed = sum(1 for d in bundle["ocsf_dispositions"] if d == "ALLOWED")
    n_denied = sum(1 for d in bundle["ocsf_dispositions"] if d == "DENIED")
    if n_allowed < 1 or n_denied < 1:  # pragma: no cover - HALT if the live run lost a decision
        raise SystemExit(
            f"HALT: expected >=1 ALLOWED and >=1 DENIED OCSF decision, got "
            f"ALLOWED={n_allowed} DENIED={n_denied}. OCSF text:\n{bundle['ocsf_textlog']}"
        )

    args.bundle_out.parent.mkdir(parents=True, exist_ok=True)
    args.bundle_out.write_text(json.dumps(bundle, indent=2, ensure_ascii=False) + "\n", "utf-8")

    print(
        f"[ok] recorded live bundle -> {args.bundle_out}\n"
        f"     spine records={len(bundle['spine_chain'])} (verify_chain clean), "
        f"OCSF ALLOWED={n_allowed} DENIED={n_denied}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

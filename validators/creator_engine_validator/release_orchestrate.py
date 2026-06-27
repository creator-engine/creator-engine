"""Release orchestrator for autonomous release (Phase A3, stage-to-seam).

Chains the Phase-A staging steps into one fail-closed sequence:

    bump (A1) → changelog (A2) → release-stage (existing) → ratification packet

The output is a fully-staged, **signature-SHAPED** artifact: the same
placeholder-signature mirror :mod:`.release_publish` already produces (its root
signing HARD REFUSAL is preserved untouched — this module only *wraps* it).
Nothing here signs, publishes, commits, or touches ``ce-root-v1``. The human
signs offline (Phase B); this collapses the staging into one command.

The orchestrator is the natural home for the version derivation: when given a
``release/vX.Y.Z`` tag it derives the version, bumps the canonical sources to
it (asserting tag==version fail-closed), aggregates the changelog since the
last release tag, then stages at the now-coupled version. ``--dry-run`` runs
the full build/parity/stage verification without promoting the output dir.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .release_bump import (
    BumpResult,
    ReleaseBumpError,
    bump_release_version,
    version_from_tag,
)
from .release_changelog import (
    ChangelogResult,
    ReleaseChangelogError,
    aggregate_changelog,
)
from .release_publish import (
    ReleasePublishError,
    ReleaseStageResult,
    SIGNING_KEY_ID,
    stage_signed_release,
)


class ReleaseOrchestrationError(RuntimeError):
    """Orchestration refused before producing a staged artifact (fail-closed)."""


@dataclass(frozen=True)
class RatificationPacket:
    """The pointers the Operator needs at the one signing gesture.

    Pure data — the bytes already live in the staged dir
    (``llms-install.canonical``, ``release-stage-manifest.yml``,
    ``SIGNING-INSTRUCTIONS.md``). This just surfaces them for the CLI.
    """

    version: str
    build_git_sha: str
    canonical_spec_sha256: str
    signing_key_id: str
    signature_placeholder: str
    signing_command: str
    canonical_path: str
    manifest_path: str
    signing_instructions_path: str


@dataclass(frozen=True)
class OrchestrationResult:
    version: str
    bump: BumpResult
    changelog: ChangelogResult
    stage: ReleaseStageResult
    packet: RatificationPacket
    changelog_out: Path | None


def orchestrate_release(
    *,
    repo_root: Path | str,
    out: Path | str,
    tag: str | None = None,
    version: str | None = None,
    part: str | None = None,
    signing_key_id: str = SIGNING_KEY_ID,
    changelog_out: Path | str | None = None,
    force: bool = False,
    dry_run: bool = False,
    build_wheel=None,
    verify_parity=None,
) -> OrchestrationResult:
    """Run bump → changelog → stage, returning the staged ratification packet.

    Version resolution (exactly one path):

    * ``tag`` (``release/vX.Y.Z``): version derived from the tag; the bumper
      asserts tag==version fail-closed.
    * ``part`` (``major|minor|patch``): rehearsal path; next version computed
      from the current canonical source.
    * ``version`` (explicit ``X.Y.Z``): stage at this version, bumping the
      sources to it (no tag/part arithmetic) — used by the dry-run rehearsal.

    All staging is placeholder-signed via the existing, unchanged
    :func:`stage_signed_release`. Nothing is committed, signed, or published.
    """
    provided = [name for name, val in (("tag", tag), ("version", version), ("part", part)) if val]
    if len(provided) != 1:
        raise ReleaseOrchestrationError(
            f"provide exactly one of tag/version/part; got {provided or 'none'}"
        )

    root = Path(repo_root).resolve()

    # --- Step 1/2: bump the canonical version sources (staged only) -------
    try:
        if tag is not None:
            bump = bump_release_version(repo_root=root, tag=tag)
        elif part is not None:
            bump = bump_release_version(repo_root=root, part=part)
        else:
            # Explicit version: drive the sources to it via a synthetic tag so
            # the same fail-closed tag==version assertion applies.
            bump = bump_release_version(repo_root=root, tag=f"release/v{version}")
    except ReleaseBumpError as exc:
        raise ReleaseOrchestrationError(f"version bump failed: {exc}") from exc

    target_version = bump.version

    # --- Step 3: aggregate the changelog since the last release tag -------
    try:
        changelog = aggregate_changelog(repo_root=root, version=target_version)
    except ReleaseChangelogError as exc:
        raise ReleaseOrchestrationError(f"changelog aggregation failed: {exc}") from exc

    written_changelog: Path | None = None
    if changelog_out is not None:
        written_changelog = Path(changelog_out).resolve()
        written_changelog.parent.mkdir(parents=True, exist_ok=True)
        written_changelog.write_text(changelog.notes, encoding="utf-8")

    # --- Step 4/5: wrap the existing release-stage (placeholder signing) --
    stage_kwargs = dict(
        repo_root=root,
        version=target_version,
        out=out,
        signing_key_id=signing_key_id,
        force=force,
        dry_run=dry_run,
    )
    if build_wheel is not None:
        stage_kwargs["build_wheel"] = build_wheel
    if verify_parity is not None:
        stage_kwargs["verify_parity"] = verify_parity
    try:
        stage = stage_signed_release(**stage_kwargs)
    except ReleasePublishError as exc:
        raise ReleaseOrchestrationError(f"release-stage failed: {exc}") from exc

    # Cross-check: the staged version MUST equal the bumped version (the
    # tag==version invariant carried all the way through staging).
    if stage.version != target_version:
        raise ReleaseOrchestrationError(
            f"staged version {stage.version!r} disagrees with bumped version {target_version!r}"
        )

    out_dir = stage.out_dir
    packet = RatificationPacket(
        version=stage.version,
        build_git_sha=stage.build_git_sha,
        canonical_spec_sha256=stage.canonical_spec_sha256,
        signing_key_id=signing_key_id,
        signature_placeholder=stage.signature_placeholder,
        signing_command=stage.signing_command,
        canonical_path=str(out_dir / "llms-install.canonical"),
        manifest_path=str(out_dir / "release-stage-manifest.yml"),
        signing_instructions_path=str(out_dir / "SIGNING-INSTRUCTIONS.md"),
    )

    return OrchestrationResult(
        version=target_version,
        bump=bump,
        changelog=changelog,
        stage=stage,
        packet=packet,
        changelog_out=written_changelog,
    )

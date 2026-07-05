# Onboard relaunch UX

- Declared work class: story.
- Added a safe relaunch path that archives stale launched seat surfaces only when the prior sentinel is verifiably dead and no tmux session is live.
- Kept ambiguous launched surfaces fail-closed with remediation pointing at `ce reap once`.
- Surfaced sentinel tail-event details, including exit code and command, when onboarding launch dies before the single-controller assertion can pass.
- Added a `ce doctor --require-visible-launch --harness ...` PATH precheck for the configured harness binary.
- Regenerated the committed CLI reference for the new `ce doctor --harness` option.
- Added unit coverage for stale archive-and-proceed, ambiguous liveness refusal, exit-127 diagnosis, and doctor harness check pass/fail.
- Fix (review follow-up): the launch-gate now reads `events.jsonl` STRICTLY before deciding archive-vs-refuse — any unparseable line, or any `launched` event with a missing/non-positive-int/bool pid, is treated as ambiguous and refuses (fail-closed), closing a gap where a mixed dead-pid/corrupt-pid shape — or a wholly-unparseable events file — could bypass the reuse gate and let a second live seat spawn under the same identity. `seat_sentinel`'s tolerant reader is unchanged (other observability consumers still rely on it).
- Fix (review follow-up): `ce doctor`'s codex harness-binary check now delegates to `codex_launch_spec.resolve_codex_harness_binary` (the exact resolution the launcher uses — `CE_CODEX_HARNESS` override used exclusively when set, else composed PATH merging live PATH with the known-good dirs) instead of a bare `shutil.which`, so doctor never reports green for a codex binary the launcher would actually refuse to resolve.
- Fix (round-2 review follow-up): `_strict_events_file_scan` now treats `OSError` on `read_text` of an existing events file as ambiguous (`return True, []`) rather than silently proceeding (`return False, []`); an unreadable-but-present sentinel file is indistinguishable from one we cannot verify, so the gate refuses. The genuinely-absent-file branch (is_file() False) is unchanged. `_archive_stale_launched_surface`'s inline pid extraction now delegates to `_parse_positive_pid` so the two definitions cannot desync (behavioral change: `bool` pids and zero/negative pids previously accepted by the lax isinstance check are now consistently rejected at both call sites).

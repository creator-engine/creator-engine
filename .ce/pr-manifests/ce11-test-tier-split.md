# PR path manifest -- ce-ops#11 test tier split

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce11-test-tier-split` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Closes creator-engine/ce-ops#11

- **Declared work class:** feature

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=73

AUTHORIZED_PATHS_SHA256=35bfb3afd520226ccd6c6d3a2431dc3f9d7cc28a0c7fbd4cddfe8130b284f366

```text
.ce/changelog/ce11-test-tier-split.md
.ce/pr-manifests/ce11-test-tier-split.md
validators/README.md
validators/pyproject.toml
validators/tests/integration/__init__.py
validators/tests/integration/test_architect_evidence_examples.py
validators/tests/integration/test_belt_launch_e2e.py
validators/tests/integration/test_ce_bootstrap_cli.py
validators/tests/integration/test_ce_brain_cli.py
validators/tests/integration/test_ce_brain_ingest_cli.py
validators/tests/integration/test_ce_brain_init_lane_gate.py
validators/tests/integration/test_ce_brain_recall_cli.py
validators/tests/integration/test_ce_brain_recall_smoke.py
validators/tests/integration/test_ce_check_cli.py
validators/tests/integration/test_ce_connector_cli.py
validators/tests/integration/test_ce_connector_tracker_cli.py
validators/tests/integration/test_ce_connector_write_cli.py
validators/tests/integration/test_ce_doctor_cli.py
validators/tests/integration/test_ce_event_cli.py
validators/tests/integration/test_ce_fanin_cli.py
validators/tests/integration/test_ce_init_cli.py
validators/tests/integration/test_ce_lane_cli.py
validators/tests/integration/test_ce_launch_cli.py
validators/tests/integration/test_ce_ledger_cli.py
validators/tests/integration/test_ce_pcl_cli.py
validators/tests/integration/test_ce_runtime_evidence_examples.py
validators/tests/integration/test_ce_runtime_policy_examples.py
validators/tests/integration/test_ce_worker_cli.py
validators/tests/integration/test_claude_hook_pack_pretooluse.py
validators/tests/integration/test_claude_hook_pack_settings.py
validators/tests/integration/test_claude_hook_pack_stop.py
validators/tests/integration/test_claude_launch_refusal.py
validators/tests/integration/test_codex_hook_pack_pretooluse.py
validators/tests/integration/test_completion_report_examples.py
validators/tests/integration/test_computer_use_authority_examples.py
validators/tests/integration/test_container_instance_examples.py
validators/tests/integration/test_controller_key_examples.py
validators/tests/integration/test_controller_runtime_contract_examples.py
validators/tests/integration/test_extension_hook_contract_examples.py
validators/tests/integration/test_fs_mediation_landlock.py
validators/tests/integration/test_greenfield_first_project.py
validators/tests/integration/test_handoff_examples.py
validators/tests/integration/test_harness_seat_contract_examples.py
validators/tests/integration/test_herdr_live.py
validators/tests/integration/test_hook_check_cli.py
validators/tests/integration/test_identity_examples.py
validators/tests/integration/test_implementer_evidence_examples.py
validators/tests/integration/test_install_bootstrap.py
validators/tests/integration/test_lane_launch_tmux.py
validators/tests/integration/test_mutation_class_examples.py
validators/tests/integration/test_onboard_apply_brownfield.py
validators/tests/integration/test_onboard_apply_greenfield.py
validators/tests/integration/test_openbao_golive_production_config_live.py
validators/tests/integration/test_openbao_golive_restore_drill_live.py
validators/tests/integration/test_openbao_p3_live.py
validators/tests/integration/test_pane_registry_examples.py
validators/tests/integration/test_pco_allocator_cli.py
validators/tests/integration/test_playbook_format_examples.py
validators/tests/integration/test_resource_bound_systemd.py
validators/tests/integration/test_review_evidence_examples.py
validators/tests/integration/test_reviewer_authority_examples.py
validators/tests/integration/test_reviewer_triage_examples.py
validators/tests/integration/test_runner_ring1_codex_push.py
validators/tests/integration/test_schema_path_resolution.py
validators/tests/integration/test_seat_class_policy_examples.py
validators/tests/integration/test_side_effect_ledger_examples.py
validators/tests/integration/test_sidecar_examples.py
validators/tests/integration/test_state_boundary_contract_examples.py
validators/tests/integration/test_state_version_record_examples.py
validators/tests/integration/test_v1_delivery_rehearsal.py
validators/tests/integration/test_worker_container_policy_examples.py
validators/tests/integration/test_worktree_lease_examples.py
validators/tests/unit/test_tier_split.py
```

"""Unit tests for the G2.001.1 ``ce_terminology_v2`` terminology-canon check."""

from __future__ import annotations

from pathlib import Path

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks.ce_terminology_v2 import (
    CHECK_NAME,
    CODE_HERMES_ACTIVE,
    CODE_SIDECAR_ALIAS,
    CODE_SOURCE_RATIFIES,
    CODE_SOURCE_ROLE,
    run,
    validate_file,
)


def _codes(errors) -> set[str]:
    return {error.code for error in errors}


def test_check_registered():
    checks = registered_checks()
    assert CHECK_NAME in checks
    frs = checks[CHECK_NAME].frs
    assert CODE_SOURCE_ROLE in frs
    assert CODE_SOURCE_RATIFIES in frs
    assert CODE_HERMES_ACTIVE in frs


def test_canonical_artifact_passes(examples_root: Path):
    path = examples_root / "well-formed/ce-terminology-v2/canonical-spec.ce.yml"
    errors = validate_file(path)
    assert errors == [], [e.format() for e in errors]


def test_real_g20010_sidecar_passes(repo_root: Path):
    """The shipped G2.001.0 spec.ce.yml (with the terminology canon) must pass."""
    path = repo_root / "specs/v2/001-v2-foundation-substrate/spec.ce.yml"
    errors = validate_file(path)
    assert errors == [], [e.format() for e in errors]


def test_real_crosswalk_register_accepted(repo_root: Path):
    """_crosswalk.yml is legacy/crosswalk context and is accepted as-is."""
    path = repo_root / "specs/v2/_crosswalk.yml"
    assert validate_file(path) == []


def test_emitted_source_role_fails(examples_root: Path):
    path = examples_root / "malformed/ce-terminology-v2/emits-source-role.ce.yml"
    errors = validate_file(path)
    assert CODE_SOURCE_ROLE in _codes(errors)


def test_hermes_active_root_fails(examples_root: Path):
    path = examples_root / "malformed/ce-terminology-v2/hermes-active-root.ce.yml"
    errors = validate_file(path)
    assert CODE_HERMES_ACTIVE in _codes(errors)


def test_source_ratifies_line_fails(examples_root: Path):
    path = examples_root / "malformed/ce-terminology-v2/source-ratifies-line.md"
    errors = validate_file(path)
    assert CODE_SOURCE_RATIFIES in _codes(errors)


def test_import_alias_context_accepted(examples_root: Path):
    """Legacy forms under an explicit import-alias marker are accepted (Q-O5)."""
    path = examples_root / "well-formed/ce-terminology-v2/import-alias.ce.yml"
    assert validate_file(path) == []


def test_run_over_well_formed_dir_passes(examples_root: Path):
    result = run([examples_root / "well-formed/ce-terminology-v2"])
    assert result.ok, [e.format() for e in result.errors]


def test_run_over_malformed_dir_fails_closed(examples_root: Path):
    result = run([examples_root / "malformed/ce-terminology-v2"])
    assert not result.ok
    assert _codes(result.errors) == {
        CODE_SOURCE_ROLE,
        CODE_HERMES_ACTIVE,
        CODE_SOURCE_RATIFIES,
        CODE_SIDECAR_ALIAS,
    }


def test_out_of_scope_paths_are_ignored(tmp_path: Path):
    """A legacy emission outside specs/v2/ is not this check's concern (no v1 regression)."""
    offending = tmp_path / "docs" / "legacy-note.ce.yml"
    offending.parent.mkdir(parents=True)
    offending.write_text("required_ratifier_role: source\n", encoding="utf-8")
    result = run([tmp_path])
    assert result.ok, [e.format() for e in result.errors]
    # The same file IS flagged when validated directly (scope is a run()-level gate).
    assert CODE_SOURCE_ROLE in _codes(validate_file(offending))


def test_crosswalk_filename_accepts_legacy(tmp_path: Path):
    crosswalk = tmp_path / "specs" / "v2" / "_crosswalk.yml"
    crosswalk.parent.mkdir(parents=True)
    crosswalk.write_text(
        "roles:\n  - required_ratifier_role: source\nactive_state_root: .hermes/\n",
        encoding="utf-8",
    )
    assert validate_file(crosswalk) == []
    result = run([tmp_path])
    assert result.ok, [e.format() for e in result.errors]


# --- Review blocker #1: structured legacy-role emission shapes must fail closed ---


def test_plural_roles_array_with_source_fails(tmp_path: Path):
    p = tmp_path / "specs" / "v2" / "plural-roles.ce.yml"
    p.parent.mkdir(parents=True)
    p.write_text("roles: [source]\n", encoding="utf-8")
    assert CODE_SOURCE_ROLE in _codes(validate_file(p))


def test_alternate_authority_field_names_with_source_fail(tmp_path: Path):
    p = tmp_path / "specs" / "v2" / "authority-fields.ce.yml"
    p.parent.mkdir(parents=True)
    p.write_text("human_authority: source\nauthority: source\n", encoding="utf-8")
    assert CODE_SOURCE_ROLE in _codes(validate_file(p))


# --- Review blocker #2: nested structured .hermes/ active/write roots must fail closed ---


def test_nested_hermes_write_roots_fail(tmp_path: Path):
    p = tmp_path / "specs" / "v2" / "nested-roots.ce.yml"
    p.parent.mkdir(parents=True)
    p.write_text(
        "write_roots:\n  primary: .hermes/\n"
        "active_state_root:\n  path: .hermes/active-work-ledger/\n"
        "allowed_write_roots:\n  - root: .hermes/\n",
        encoding="utf-8",
    )
    assert CODE_HERMES_ACTIVE in _codes(validate_file(p))


# --- Q-O5 preserved: the same bypass shapes are accepted under a legacy marker ---


def test_structured_bypass_shapes_accepted_under_legacy_marker(tmp_path: Path):
    p = tmp_path / "specs" / "v2" / "legacy-marked.ce.yml"
    p.parent.mkdir(parents=True)
    p.write_text(
        "ce_terminology_context: import\n"
        "roles: [source]\n"
        "write_roots:\n  primary: .hermes/\n",
        encoding="utf-8",
    )
    assert validate_file(p) == []


# --- New malformed fixtures (bundled) must fail closed with the expected codes ---


def test_structured_source_roles_fixture_fails(examples_root: Path):
    path = examples_root / "malformed/ce-terminology-v2/structured-source-roles.ce.yml"
    assert CODE_SOURCE_ROLE in _codes(validate_file(path))


def test_nested_hermes_roots_fixture_fails(examples_root: Path):
    path = examples_root / "malformed/ce-terminology-v2/nested-hermes-roots.ce.yml"
    assert CODE_HERMES_ACTIVE in _codes(validate_file(path))


# --- Round 2 blocker: plural active/write-root keys must fail closed ---


def test_plural_active_root_keys_with_hermes_fail(tmp_path: Path):
    p = tmp_path / "specs" / "v2" / "plural-roots.ce.yml"
    p.parent.mkdir(parents=True)
    p.write_text(
        "active_state_roots: [.hermes/]\nstate_roots: [.hermes/]\nactive_roots: [.hermes/]\n",
        encoding="utf-8",
    )
    assert CODE_HERMES_ACTIVE in _codes(validate_file(p))


def test_plural_hermes_roots_fixture_fails(examples_root: Path):
    path = examples_root / "malformed/ce-terminology-v2/plural-hermes-roots.ce.yml"
    assert CODE_HERMES_ACTIVE in _codes(validate_file(path))


def test_plural_active_roots_accepted_under_legacy_marker(tmp_path: Path):
    p = tmp_path / "specs" / "v2" / "legacy-plural.ce.yml"
    p.parent.mkdir(parents=True)
    p.write_text(
        "ce_terminology_context: import\nactive_state_roots: [.hermes/]\n", encoding="utf-8"
    )
    assert validate_file(p) == []


def test_legacy_root_key_not_treated_as_active_root(tmp_path: Path):
    """Low-false-positive guard: `legacy_root` is descriptive legacy context, not an
    active-root emission; the plural broadening must not start flagging it."""
    p = tmp_path / "specs" / "v2" / "legacy-root-desc.ce.yml"
    p.parent.mkdir(parents=True)
    p.write_text(
        "legacy_root: .hermes/\nlegacy_roots: [.hermes/]\ncanonical_active_root: .ce/\n",
        encoding="utf-8",
    )
    assert _codes(validate_file(p)) == set()


# --- Round 3 blocker: nested / key-encoded legacy `source` role shapes fail closed ---


def test_nested_role_dict_value_with_source_fails(tmp_path: Path):
    p = tmp_path / "specs" / "v2" / "nested-role-value.ce.yml"
    p.parent.mkdir(parents=True)
    p.write_text("roles:\n  primary: source\n", encoding="utf-8")
    assert CODE_SOURCE_ROLE in _codes(validate_file(p))


def test_source_encoded_as_map_key_fails(tmp_path: Path):
    p = tmp_path / "specs" / "v2" / "source-key.ce.yml"
    p.parent.mkdir(parents=True)
    p.write_text("roles:\n  source:\n    active: true\n", encoding="utf-8")
    assert CODE_SOURCE_ROLE in _codes(validate_file(p))


def test_nested_authority_and_role_dicts_with_source_fail(tmp_path: Path):
    p = tmp_path / "specs" / "v2" / "nested-auth.ce.yml"
    p.parent.mkdir(parents=True)
    p.write_text("human_authority:\n  machine: source\nrole:\n  name: source\n", encoding="utf-8")
    assert CODE_SOURCE_ROLE in _codes(validate_file(p))


def test_list_of_role_dicts_with_source_fail(tmp_path: Path):
    p = tmp_path / "specs" / "v2" / "list-role-dicts.ce.yml"
    p.parent.mkdir(parents=True)
    p.write_text("roles:\n  - name: source\n", encoding="utf-8")
    assert CODE_SOURCE_ROLE in _codes(validate_file(p))


def test_nested_source_roles_fixture_fails(examples_root: Path):
    path = examples_root / "malformed/ce-terminology-v2/nested-source-roles.ce.yml"
    assert CODE_SOURCE_ROLE in _codes(validate_file(path))


def test_nested_source_role_shapes_accepted_under_legacy_marker(tmp_path: Path):
    p = tmp_path / "specs" / "v2" / "legacy-nested-role.ce.yml"
    p.parent.mkdir(parents=True)
    p.write_text(
        "ce_terminology_context: import\nroles:\n  source:\n    active: true\n", encoding="utf-8"
    )
    assert validate_file(p) == []


def test_canonical_nested_role_value_not_flagged(tmp_path: Path):
    """Low-false-positive guard: nested role dicts with canonical `operator` pass."""
    p = tmp_path / "specs" / "v2" / "canonical-nested.ce.yml"
    p.parent.mkdir(parents=True)
    p.write_text("roles:\n  primary: operator\nrole:\n  name: operator\n", encoding="utf-8")
    assert _codes(validate_file(p)) == set()


def test_role_subtree_legacy_alias_descriptor_not_flagged(tmp_path: Path):
    """The terminology canon DOCUMENTS the legacy alias (`legacy_alias: source` paired
    with `canonical_emit: operator`); that is a description, not an emission, and must
    pass even though `human_authority` is a recognized role-bearing key."""
    p = tmp_path / "specs" / "v2" / "canon-self-desc.ce.yml"
    p.parent.mkdir(parents=True)
    p.write_text(
        "human_authority:\n"
        "  canonical_emit: operator\n"
        "  legacy_alias: source\n"
        "  emit_legacy_in_v2: false\n"
        "  accept_on_import_only: true\n",
        encoding="utf-8",
    )
    assert _codes(validate_file(p)) == set()


# --- Round 4 blocker 1: ordered-list Markdown ratification lines fail closed ---


def test_ordered_list_dot_source_ratifies_fails(tmp_path: Path):
    p = tmp_path / "specs" / "v2" / "ol-dot.md"
    p.parent.mkdir(parents=True)
    p.write_text("1. Source ratifies prompt:/x\n", encoding="utf-8")
    assert CODE_SOURCE_RATIFIES in _codes(validate_file(p))


def test_ordered_list_paren_source_ratifies_fails(tmp_path: Path):
    p = tmp_path / "specs" / "v2" / "ol-paren.md"
    p.parent.mkdir(parents=True)
    p.write_text("1) Source ratifies prompt:/x\n", encoding="utf-8")
    assert CODE_SOURCE_RATIFIES in _codes(validate_file(p))


def test_numbered_descriptive_ratifies_line_not_flagged(tmp_path: Path):
    """A numbered item that merely DESCRIBES the legacy phrase is not an emission."""
    p = tmp_path / "specs" / "v2" / "ol-desc.md"
    p.parent.mkdir(parents=True)
    p.write_text(
        "1. The Source ratifies prompt: phrase is accepted on import only.\n", encoding="utf-8"
    )
    assert _codes(validate_file(p)) == set()


def test_ordered_list_source_ratifies_fixture_fails(examples_root: Path):
    path = examples_root / "malformed/ce-terminology-v2/ordered-list-source-ratifies.md"
    assert CODE_SOURCE_RATIFIES in _codes(validate_file(path))


# --- Round 4 blocker 2: exact `.hermes` (no trailing slash) active roots fail closed ---


def test_exact_hermes_active_roots_fail(tmp_path: Path):
    p = tmp_path / "specs" / "v2" / "bare-hermes.ce.yml"
    p.parent.mkdir(parents=True)
    p.write_text(
        "active_state_root: .hermes\nwrite_roots:\n  primary: .hermes\nactive_state_roots: [.hermes]\n",
        encoding="utf-8",
    )
    assert CODE_HERMES_ACTIVE in _codes(validate_file(p))


def test_bare_hermes_roots_fixture_fails(examples_root: Path):
    path = examples_root / "malformed/ce-terminology-v2/bare-hermes-roots.ce.yml"
    assert CODE_HERMES_ACTIVE in _codes(validate_file(path))


def test_hermes_prefixed_nonroot_value_not_flagged(tmp_path: Path):
    """Exact-match guard: a `.hermes`-prefixed but distinct value (e.g. `.hermesphere`)
    is not the `.hermes` root and must not be flagged."""
    p = tmp_path / "specs" / "v2" / "hermes-prefix.ce.yml"
    p.parent.mkdir(parents=True)
    p.write_text("active_state_root: .hermesphere\n", encoding="utf-8")
    assert _codes(validate_file(p)) == set()


# --- Round 4 optional: singular `allowed_write_root` coverage ---


def test_singular_allowed_write_root_hermes_fails(tmp_path: Path):
    p = tmp_path / "specs" / "v2" / "singular-awr.ce.yml"
    p.parent.mkdir(parents=True)
    p.write_text("allowed_write_root: .hermes/\n", encoding="utf-8")
    assert CODE_HERMES_ACTIVE in _codes(validate_file(p))


# --- Round 5 blocker 1: `.hermes` encoded as a YAML map key fails closed ---


def test_hermes_root_as_map_key_fails(tmp_path: Path):
    p = tmp_path / "specs" / "v2" / "key-root.ce.yml"
    p.parent.mkdir(parents=True)
    p.write_text(
        "write_roots:\n  .hermes/: active\nallowed_write_roots:\n  .hermes/: true\n",
        encoding="utf-8",
    )
    assert CODE_HERMES_ACTIVE in _codes(validate_file(p))


# --- Round 5 blocker 2: repo-relative `./.hermes` spellings fail closed ---


def test_repo_relative_hermes_roots_fail(tmp_path: Path):
    p = tmp_path / "specs" / "v2" / "rel-root.ce.yml"
    p.parent.mkdir(parents=True)
    p.write_text(
        "active_state_root: ./.hermes/\nwrite_roots:\n  primary: ./.hermes\nactive_state_roots: [./.hermes/]\n",
        encoding="utf-8",
    )
    assert CODE_HERMES_ACTIVE in _codes(validate_file(p))


def test_repo_relative_hermesphere_not_flagged(tmp_path: Path):
    p = tmp_path / "specs" / "v2" / "rel-prefix.ce.yml"
    p.parent.mkdir(parents=True)
    p.write_text(
        "active_state_root: ./.hermesphere\nwrite_roots:\n  primary: .hermesphere\n", encoding="utf-8"
    )
    assert _codes(validate_file(p)) == set()


def test_round5_fixture_fails(examples_root: Path):
    path = examples_root / "malformed/ce-terminology-v2/key-and-relative-hermes-roots.ce.yml"
    assert CODE_HERMES_ACTIVE in _codes(validate_file(path))


# --- Consolidated table of forbidden / accepted active-root spellings + encodings ---
# (systemic note: one place that captures every known forbidden active-root form so a
#  future review is less likely to find a one-shape gap.)

_FORBIDDEN_ACTIVE_ROOT_YAML = [
    "active_state_root: .hermes/",
    "active_state_root: .hermes",
    "active_state_root: ./.hermes/",
    "active_state_root: ./.hermes",
    "active_state_root: .hermes/active-work-ledger/",
    "active_state_roots: [.hermes]",
    "active_state_roots: [./.hermes/]",
    "active_roots: [.hermes/]",
    "state_roots: [.hermes]",
    "write_roots:\n  primary: .hermes\n",
    "write_roots:\n  primary: ./.hermes/\n",
    "write_roots:\n  .hermes/: active\n",
    "allowed_write_roots:\n  - root: .hermes/\n",
    "allowed_write_roots:\n  .hermes/: true\n",
    "allowed_write_root: .hermes/",
]

_ACCEPTED_ACTIVE_ROOT_YAML = [
    "canonical_active_root: .ce/",
    "active_state_root: .hermesphere",
    "active_state_root: ./.hermesphere",
    "legacy_root: .hermes/",  # legacy_root is not an active-root key (descriptive)
    "active_state_root_axis:\n  legacy_read_only: .hermes/\n",  # axis key, not active-root
]


def test_forbidden_active_root_spellings_table(tmp_path: Path):
    for i, snippet in enumerate(_FORBIDDEN_ACTIVE_ROOT_YAML):
        p = tmp_path / "specs" / "v2" / f"forbidden-{i}.ce.yml"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(snippet if snippet.endswith("\n") else snippet + "\n", encoding="utf-8")
        assert CODE_HERMES_ACTIVE in _codes(validate_file(p)), f"expected fail-closed for: {snippet!r}"


def test_accepted_active_root_spellings_table(tmp_path: Path):
    for i, snippet in enumerate(_ACCEPTED_ACTIVE_ROOT_YAML):
        p = tmp_path / "specs" / "v2" / f"accepted-{i}.ce.yml"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(snippet if snippet.endswith("\n") else snippet + "\n", encoding="utf-8")
        assert CODE_HERMES_ACTIVE not in _codes(validate_file(p)), f"unexpected fail for: {snippet!r}"


# --- Round 6 blocker 1: broad descriptor-key bypass for source roles ---


def test_roles_legacy_key_with_source_fails(tmp_path: Path):
    p = tmp_path / "specs" / "v2" / "roles-legacy.ce.yml"
    p.parent.mkdir(parents=True)
    p.write_text("roles:\n  legacy: source\n", encoding="utf-8")
    assert CODE_SOURCE_ROLE in _codes(validate_file(p))


def test_roles_alias_key_with_source_fails(tmp_path: Path):
    p = tmp_path / "specs" / "v2" / "roles-alias.ce.yml"
    p.parent.mkdir(parents=True)
    p.write_text("roles:\n  alias: source\n", encoding="utf-8")
    assert CODE_SOURCE_ROLE in _codes(validate_file(p))


def test_roles_aliases_list_with_source_fails(tmp_path: Path):
    p = tmp_path / "specs" / "v2" / "roles-aliases.ce.yml"
    p.parent.mkdir(parents=True)
    p.write_text("roles:\n  aliases: [source]\n", encoding="utf-8")
    assert CODE_SOURCE_ROLE in _codes(validate_file(p))


def test_descriptor_key_source_roles_fixture_fails(examples_root: Path):
    path = examples_root / "malformed/ce-terminology-v2/descriptor-key-source-roles.ce.yml"
    assert CODE_SOURCE_ROLE in _codes(validate_file(path))


def test_broad_descriptor_shapes_accepted_under_legacy_marker(tmp_path: Path):
    p = tmp_path / "specs" / "v2" / "legacy-broad.ce.yml"
    p.parent.mkdir(parents=True)
    p.write_text("ce_terminology_context: import\nroles:\n  legacy: source\n", encoding="utf-8")
    assert validate_file(p) == []


# --- Round 6 blocker 2: Markdown task-list ratification lines ---


def test_task_list_dash_source_ratifies_fails(tmp_path: Path):
    p = tmp_path / "specs" / "v2" / "tl-dash.md"
    p.parent.mkdir(parents=True)
    p.write_text("- [ ] Source ratifies prompt:/x\n", encoding="utf-8")
    assert CODE_SOURCE_RATIFIES in _codes(validate_file(p))


def test_task_list_star_checked_source_ratifies_fails(tmp_path: Path):
    p = tmp_path / "specs" / "v2" / "tl-star.md"
    p.parent.mkdir(parents=True)
    p.write_text("* [x] Source ratifies prompt:/x\n", encoding="utf-8")
    assert CODE_SOURCE_RATIFIES in _codes(validate_file(p))


def test_task_list_descriptive_ratifies_not_flagged(tmp_path: Path):
    p = tmp_path / "specs" / "v2" / "tl-desc.md"
    p.parent.mkdir(parents=True)
    p.write_text("- [ ] The Source ratifies prompt: phrase is legacy wording.\n", encoding="utf-8")
    assert _codes(validate_file(p)) == set()


def test_task_list_source_ratifies_fixture_fails(examples_root: Path):
    path = examples_root / "malformed/ce-terminology-v2/task-list-source-ratifies.md"
    assert CODE_SOURCE_RATIFIES in _codes(validate_file(path))


# --- Round 7 blocker 1: YAML ratification-line emissions fail closed ---


def test_yaml_scalar_ratification_line_fails(tmp_path: Path):
    p = tmp_path / "specs" / "v2" / "rl-scalar.ce.yml"
    p.parent.mkdir(parents=True)
    p.write_text('ratification_line: "Source ratifies prompt:/x"\n', encoding="utf-8")
    assert CODE_SOURCE_RATIFIES in _codes(validate_file(p))


def test_yaml_nested_ratification_line_fails(tmp_path: Path):
    p = tmp_path / "specs" / "v2" / "rl-nested.ce.yml"
    p.parent.mkdir(parents=True)
    p.write_text('authority:\n  ratification_line: "Source ratifies prompt:/x"\n', encoding="utf-8")
    assert CODE_SOURCE_RATIFIES in _codes(validate_file(p))


def test_yaml_ratification_lines_list_fails(tmp_path: Path):
    p = tmp_path / "specs" / "v2" / "rl-list.ce.yml"
    p.parent.mkdir(parents=True)
    p.write_text('ratification_lines:\n  - "Source ratifies prompt:/x"\n', encoding="utf-8")
    assert CODE_SOURCE_RATIFIES in _codes(validate_file(p))


def test_yaml_ratification_fixture_fails(examples_root: Path):
    path = examples_root / "malformed/ce-terminology-v2/yaml-source-ratifies.ce.yml"
    assert CODE_SOURCE_RATIFIES in _codes(validate_file(path))


def test_yaml_canon_ratification_descriptor_accepted(tmp_path: Path):
    """The canon documents the legacy ratification line under `legacy_alias`; that is
    self-description, not emission, and must pass."""
    p = tmp_path / "specs" / "v2" / "rl-canon.ce.yml"
    p.parent.mkdir(parents=True)
    p.write_text(
        'ratification_line:\n'
        '  canonical_emit: "Operator ratifies prompt:"\n'
        '  legacy_alias: "Source ratifies prompt:"\n'
        '  emit_legacy_in_v2: false\n',
        encoding="utf-8",
    )
    assert _codes(validate_file(p)) == set()


def test_yaml_descriptive_ratification_mention_accepted(tmp_path: Path):
    """A string that merely MENTIONS the phrase (does not begin with it) is descriptive."""
    p = tmp_path / "specs" / "v2" / "rl-desc.ce.yml"
    p.parent.mkdir(parents=True)
    p.write_text('note: "accept the Source ratifies prompt: form on import only"\n', encoding="utf-8")
    assert _codes(validate_file(p)) == set()


# --- Round 7 blocker 2: active_write_root key coverage fails closed ---


def test_active_write_root_hermes_fails(tmp_path: Path):
    p = tmp_path / "specs" / "v2" / "awr.ce.yml"
    p.parent.mkdir(parents=True)
    p.write_text("active_write_root: .hermes/\n", encoding="utf-8")
    assert CODE_HERMES_ACTIVE in _codes(validate_file(p))


def test_active_write_roots_plural_hermes_fails(tmp_path: Path):
    p = tmp_path / "specs" / "v2" / "awrs.ce.yml"
    p.parent.mkdir(parents=True)
    p.write_text("active_write_roots: [.hermes]\n", encoding="utf-8")
    assert CODE_HERMES_ACTIVE in _codes(validate_file(p))


def test_active_write_root_fixture_fails(examples_root: Path):
    path = examples_root / "malformed/ce-terminology-v2/active-write-root-hermes.ce.yml"
    assert CODE_HERMES_ACTIVE in _codes(validate_file(path))


# --- Round 8 blocker 1: canonical_*_root key coverage ---


def test_canonical_root_keys_with_hermes_fail(tmp_path: Path):
    p = tmp_path / "specs" / "v2" / "canon-roots.ce.yml"
    p.parent.mkdir(parents=True)
    p.write_text(
        "canonical_write_root: .hermes/\ncanonical_write_roots: [.hermes/]\n"
        "canonical_state_root: .hermes/\ncanonical_state_roots: [.hermes/]\n",
        encoding="utf-8",
    )
    assert CODE_HERMES_ACTIVE in _codes(validate_file(p))


# --- Round 8 blocker 2: plural ratifier role fields ---


def test_plural_ratifier_fields_with_source_fail(tmp_path: Path):
    p = tmp_path / "specs" / "v2" / "ratifiers.ce.yml"
    p.parent.mkdir(parents=True)
    p.write_text(
        "ratifiers: [source]\nrequired_ratifiers: [source]\nallowed_ratifiers: [source]\n",
        encoding="utf-8",
    )
    assert CODE_SOURCE_ROLE in _codes(validate_file(p))


# --- Round 8 blocker 3: YAML block-scalar ratification lines (line-wise) ---


def test_block_scalar_ratification_line_fails(tmp_path: Path):
    p = tmp_path / "specs" / "v2" / "block-scalar.ce.yml"
    p.parent.mkdir(parents=True)
    p.write_text("note: |\n  intro line\n  Source ratifies prompt:/x\n", encoding="utf-8")
    assert CODE_SOURCE_RATIFIES in _codes(validate_file(p))


def test_block_scalar_descriptive_not_flagged(tmp_path: Path):
    p = tmp_path / "specs" / "v2" / "block-scalar-desc.ce.yml"
    p.parent.mkdir(parents=True)
    p.write_text(
        "note: |\n  intro line\n  the Source ratifies prompt: phrase is legacy wording\n",
        encoding="utf-8",
    )
    assert _codes(validate_file(p)) == set()


# --- Round 8 blocker 4: sidecar filename canon (*.creator-engine.yml) ---

_SIDECAR_CODE = "VAL-TERMINOLOGY-SIDECAR-ALIAS"


def test_creator_engine_yml_filename_fails(tmp_path: Path):
    p = tmp_path / "specs" / "v2" / "foo.creator-engine.yml"
    p.parent.mkdir(parents=True)
    p.write_text("schema: x\n", encoding="utf-8")  # benign content
    assert _SIDECAR_CODE in _codes(validate_file(p))


def test_ce_yml_filename_not_flagged(tmp_path: Path):
    p = tmp_path / "specs" / "v2" / "foo.ce.yml"
    p.parent.mkdir(parents=True)
    p.write_text("schema: x\n", encoding="utf-8")
    assert _SIDECAR_CODE not in _codes(validate_file(p))


def test_creator_engine_yml_legacy_path_accepted(tmp_path: Path):
    p = tmp_path / "specs" / "v2" / "archive" / "old.creator-engine.yml"
    p.parent.mkdir(parents=True)
    p.write_text("schema: x\n", encoding="utf-8")
    assert validate_file(p) == []


def test_creator_engine_yml_legacy_marker_accepted(tmp_path: Path):
    p = tmp_path / "specs" / "v2" / "marked.creator-engine.yml"
    p.parent.mkdir(parents=True)
    p.write_text("ce_terminology_context: import\nschema: x\n", encoding="utf-8")
    assert validate_file(p) == []


# --- Round 8 bundled fixtures ---


def test_round8_canonical_root_fixture_fails(examples_root: Path):
    path = examples_root / "malformed/ce-terminology-v2/canonical-root-hermes.ce.yml"
    assert CODE_HERMES_ACTIVE in _codes(validate_file(path))


def test_round8_ratifiers_fixture_fails(examples_root: Path):
    path = examples_root / "malformed/ce-terminology-v2/plural-ratifiers-source.ce.yml"
    assert CODE_SOURCE_ROLE in _codes(validate_file(path))


def test_round8_block_scalar_fixture_fails(examples_root: Path):
    path = examples_root / "malformed/ce-terminology-v2/block-scalar-source-ratifies.ce.yml"
    assert CODE_SOURCE_RATIFIES in _codes(validate_file(path))


def test_round8_sidecar_fixture_fails(examples_root: Path):
    path = examples_root / "malformed/ce-terminology-v2/forbidden-sidecar.creator-engine.yml"
    assert _SIDECAR_CODE in _codes(validate_file(path))

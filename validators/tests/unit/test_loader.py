from pathlib import Path

from creator_engine_validator.loader import discover_sidecar, iter_tenant_identity_records


def test_discover_sidecar_uses_only_canonical_adjacent_names(tmp_path: Path):
    spec = tmp_path / "spec.md"
    canonical = tmp_path / "spec.creator-engine.yml"
    noncanonical = tmp_path / "spec.md.creator-engine.yml"
    spec.write_text("# Spec\n")
    canonical.write_text("id: example\n")
    noncanonical.write_text("id: wrong\n")

    assert discover_sidecar(spec) == canonical


def test_iter_tenant_identity_records_discovers_nested_records(tmp_path: Path):
    record = tmp_path / "tenants" / "example" / "identity-record.yml"
    record.parent.mkdir(parents=True)
    record.write_text("tenant_id: example\n")

    assert list(iter_tenant_identity_records([tmp_path])) == [record]

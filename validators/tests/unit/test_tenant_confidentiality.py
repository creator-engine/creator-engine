"""Unit tests for the tenant confidentiality denylist matrix."""
from __future__ import annotations

from pathlib import Path
import re
import subprocess

from creator_engine_validator import public_docs_confidentiality as guard
from creator_engine_validator import tenant_confidentiality as tenant_conf


def _tenant(
    tenant_id: str,
    *,
    token: str,
    venue: str,
    allowlist: tuple[tenant_conf.TenantAllowlistEntry, ...] = (),
) -> tenant_conf.TenantDenylist:
    return tenant_conf.TenantDenylist(
        tenant_id=tenant_id,
        patterns=(
            tenant_conf.TenantPattern(
                tenant_id=tenant_id,
                label="private marker",
                pattern=re.compile(re.escape(token)),
            ),
        ),
        venue_paths=(venue,),
        allowlist=allowlist,
    )


def _config(*tenants: tenant_conf.TenantDenylist) -> guard.ConfidentialityScanConfig:
    return guard.ConfidentialityScanConfig(
        tenant_matrix=tenant_conf.TenantDenylistMatrix(tenants)
    )


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _write_tracked(repo: Path, rel: str, text: str) -> Path:
    target = repo / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    _git(repo, "add", "--", rel)
    return target


def _make_repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init")
    return tmp_path


def test_denylist_ref_loads_data_driven_tenant_patterns(tmp_path: Path):
    tenant_record = tmp_path / "governance" / "tenants" / "alpha" / "tenant.yaml"
    tenant_record.parent.mkdir(parents=True)
    tenant_record.write_text(
        """
kind: tenant-record
tenant_id: alpha
confidentiality:
  denylist_ref: governance/tenants/alpha/denylist.yaml
""".lstrip(),
        encoding="utf-8",
    )
    (tenant_record.parent / "denylist.yaml").write_text(
        """
version: 1
tenant_id: alpha
patterns:
  - label: repository slug
    pattern: '\\balpha-secret-repo\\b'
venue_paths:
  - tenant-venues/alpha/
""".lstrip(),
        encoding="utf-8",
    )

    matrix = tenant_conf.load_tenant_denylist_matrix(tmp_path)
    config = guard.ConfidentialityScanConfig(tenant_matrix=matrix)
    public_doc = tmp_path / "README.md"
    public_doc.write_text("Do not publish alpha-secret-repo here.\n", encoding="utf-8")

    hits = guard.offenses(public_doc, repo_root=tmp_path, config=config)

    assert len(hits) == 1
    assert "README.md:1 [tenant alpha denylist: repository slug]" in hits[0]


def test_ce_forbidden_patterns_stay_unconditional_inside_tenant_venue(tmp_path: Path):
    config = _config(_tenant("alpha", token="ALPHA-PRIVATE", venue="tenants/alpha/"))
    doc = tmp_path / "tenants" / "alpha" / "issue.md"
    doc.parent.mkdir(parents=True)
    ticket_ref = "ce-ops" + "#123"
    doc.write_text(f"Tenant venue still cannot mention {ticket_ref}.\n", encoding="utf-8")

    hits = guard.offenses(doc, repo_root=tmp_path, config=config)

    assert len(hits) == 1
    assert "[confidential ce-ops# ticket reference]" in hits[0]


def test_tenant_denylist_is_enforced_both_directions(tmp_path: Path):
    alpha = _tenant("alpha", token="ALPHA-PRIVATE", venue="tenant-alpha/")
    beta = _tenant("beta", token="BETA-PRIVATE", venue="tenant-beta/")
    config = _config(alpha, beta)
    public_doc = tmp_path / "README.md"
    beta_doc = tmp_path / "tenant-beta" / "scope.md"
    alpha_doc = tmp_path / "tenant-alpha" / "scope.md"
    beta_doc.parent.mkdir()
    alpha_doc.parent.mkdir()
    public_doc.write_text("Public docs must not mention ALPHA-PRIVATE.\n", encoding="utf-8")
    beta_doc.write_text("Beta must not receive ALPHA-PRIVATE.\n", encoding="utf-8")
    alpha_doc.write_text("Alpha may mention its own ALPHA-PRIVATE marker.\n", encoding="utf-8")

    public_hits = guard.offenses(public_doc, repo_root=tmp_path, config=config)
    beta_hits = guard.offenses(beta_doc, repo_root=tmp_path, config=config)
    alpha_hits = guard.offenses(alpha_doc, repo_root=tmp_path, config=config)

    assert "tenant alpha denylist: private marker" in public_hits[0]
    assert "tenant alpha denylist: private marker" in beta_hits[0]
    assert alpha_hits == []


def test_per_tenant_allowlist_suppresses_current_debt_and_only_shrinks(tmp_path: Path):
    repo = _make_repo(tmp_path)
    entry = tenant_conf.TenantAllowlistEntry(
        tenant_id="alpha",
        path="tenant-beta/legacy.md",
        pattern_label="private marker",
        reason="legacy client migration debt",
    )
    config = _config(
        _tenant("alpha", token="ALPHA-PRIVATE", venue="tenant-alpha/", allowlist=(entry,)),
        _tenant("beta", token="BETA-PRIVATE", venue="tenant-beta/"),
    )
    legacy = _write_tracked(repo, "tenant-beta/legacy.md", "Known debt: ALPHA-PRIVATE.\n")

    assert guard.scan_offenses(repo_root=repo, config=config) == []

    legacy.write_text("Debt cleaned.\n", encoding="utf-8")

    stale = guard.scan_offenses(repo_root=repo, config=config)
    assert len(stale) == 1
    assert "[tenant allowlist stale]" in stale[0]
    assert "tenant-beta/legacy.md" in stale[0]


def test_tenant_denylist_scans_pr_issue_and_evidence_surfaces(tmp_path: Path):
    repo = _make_repo(tmp_path)
    config = _config(_tenant("alpha", token="ALPHA-PRIVATE", venue="tenant-alpha/"))
    _write_tracked(repo, ".ce/pr-manifests/demo.md", "PR body leak: ALPHA-PRIVATE.\n")
    _write_tracked(repo, ".ce/issues/demo.md", "Issue text leak: ALPHA-PRIVATE.\n")
    _write_tracked(repo, ".ce/evidence/run.yaml", "Evidence leak: ALPHA-PRIVATE.\n")

    hits = guard.scan_offenses(repo_root=repo, config=config)

    assert len(hits) == 3
    rendered = "\n".join(hits)
    assert ".ce/pr-manifests/demo.md" in rendered
    assert ".ce/issues/demo.md" in rendered
    assert ".ce/evidence/run.yaml" in rendered

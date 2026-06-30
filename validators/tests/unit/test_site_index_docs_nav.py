"""Offline checks for the live site index documentation navigation."""
from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SITE_INDEX = _REPO_ROOT / "docs" / "index.html"
_DOCS_ROOT = _REPO_ROOT / "docs"

_VOID_TAGS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}

_EXPECTED_DOC_LINKS = {
    "llms-install.md",
}

_EXPECTED_RENDERED_DOC_LINKS = {
    "what-is-creator-engine.html",
    "guide/understanding-ce.html",
    "guide/pilot-runbook.html",
    "guide/contributing-to-ce.html",
    "guide/solo-dev-onboarding.html",
    "guide/solo-ceo-onboarding.html",
    "security/SECURITY_MODEL.html",
}


class _SiteIndexParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: set[str] = set()
        self.same_page_hrefs: list[str] = []
        self.docs_links: list[str] = []
        self._stack: list[tuple[str, bool]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._handle_start(tag, attrs, push=tag not in _VOID_TAGS)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._handle_start(tag, attrs, push=False)

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self._stack) - 1, -1, -1):
            open_tag, _inside_docs = self._stack[index]
            if open_tag == tag:
                del self._stack[index:]
                break

    def _handle_start(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
        *,
        push: bool,
    ) -> None:
        attr_map = {name: value for name, value in attrs if value is not None}
        node_id = attr_map.get("id")
        if node_id:
            self.ids.add(node_id)

        href = attr_map.get("href") or attr_map.get("xlink:href")
        if href and href.startswith("#"):
            self.same_page_hrefs.append(href)

        inside_docs = node_id == "docs" or any(
            ancestor_inside for _ancestor_tag, ancestor_inside in self._stack
        )
        if inside_docs and tag == "a" and href:
            self.docs_links.append(href)

        if push:
            self._stack.append((tag, inside_docs))


def _parse_site_index() -> _SiteIndexParser:
    parser = _SiteIndexParser()
    parser.feed(_SITE_INDEX.read_text(encoding="utf-8"))
    parser.close()
    return parser


def test_every_same_page_anchor_href_resolves_to_an_element_id():
    site = _parse_site_index()
    targets = {href.removeprefix("#") for href in site.same_page_hrefs if href != "#"}
    missing = sorted(targets - site.ids)

    assert not missing, f"docs/index.html has unresolved same-page anchors: {missing}"


def test_docs_anchor_exists_and_links_to_current_docs():
    site = _parse_site_index()

    assert "docs" in site.ids
    assert _EXPECTED_DOC_LINKS <= set(site.docs_links)
    assert _EXPECTED_RENDERED_DOC_LINKS <= set(site.docs_links)

    for href in site.docs_links:
        parsed = urlparse(href)
        assert not parsed.scheme and not parsed.netloc, f"docs link must be relative: {href}"
        if not parsed.path.endswith(".md"):
            assert parsed.path in _EXPECTED_RENDERED_DOC_LINKS, f"unexpected rendered docs link: {href}"

        target = (_DOCS_ROOT / parsed.path).resolve()
        assert target.is_relative_to(_DOCS_ROOT.resolve())
        assert target.is_file(), f"docs link target does not exist: {href}"

"""XOR gate for mediated brain append intents versus direct ledger edits."""

from __future__ import annotations

from .reporting import ValidationError


CHECK_NAME = "brain_append_intent_xor_direct_ledger"
CONTRACT = "docs/design/ce-491-optiona-merge-intent.md"
ASSERTIONS_PATH = ".ce/brain/assertions.yaml"
INTENT_PREFIX = ".ce/brain/append-intents/"
ERROR_MESSAGE = (
    "PR carries both an append intent file and a direct .ce/brain/assertions.yaml edit; "
    "hybrid PRs are refused regardless of stale-tail status"
)


def _is_append_intent(path: str) -> bool:
    return (
        path.startswith(INTENT_PREFIX)
        and "/" not in path.removeprefix(INTENT_PREFIX)
        and (path.endswith(".yaml") or path.endswith(".yml"))
    )


def check_xor(changed_paths: list[str]) -> list[ValidationError]:
    has_intent = any(_is_append_intent(path) for path in changed_paths)
    has_direct_ledger = any(path == ASSERTIONS_PATH for path in changed_paths)
    if not has_intent or not has_direct_ledger:
        return []
    return [
        ValidationError(
            code=CHECK_NAME,
            path=ASSERTIONS_PATH,
            message=ERROR_MESSAGE,
            contract=CONTRACT,
        )
    ]

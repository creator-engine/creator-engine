"""Unit tests for the shared ``secret_paths`` credential-path predicate.

Covers the extraction from v1 ``hook_check`` into the shared line: the public
``hook_check.is_secret_path`` must remain the SAME object (single source of
truth, no re-derivation) and the classification must be byte-for-byte unchanged.
"""

from __future__ import annotations

import pytest

from creator_engine_validator import hook_check
from creator_engine_validator import secret_paths
from creator_engine_validator.secret_paths import (
    CREDENTIAL_PATH_RULE_CLASSES,
    is_secret_path,
)


def test_hook_check_reexports_the_same_object():
    # The single source of truth: hook_check must reuse the shared predicate,
    # not keep its own copy.
    assert hook_check.is_secret_path is is_secret_path
    assert hook_check.is_secret_path is secret_paths.is_secret_path


@pytest.mark.parametrize(
    "path,expected",
    [
        ("config/.env", ".env"),
        (".env", ".env"),
        ("x/.env.local", ".env"),
        ("a/id_rsa", "id_rsa"),
        ("deep/id_ed25519", "id_ed25519"),
        ("a/.netrc", ".netrc"),
        ("svc/credentials.json", "credentials.json"),
        ("tls/server.pem", "private-key/cert"),
        ("store/app.key", "private-key/cert"),
        ("home/.ssh/known_hosts", "credential-store-directory"),
        ("home/.aws/config", "credential-store-directory"),
        ("vault/secrets/token", "credential-store-directory"),
        ("my-credentials.txt", "credential-like-name"),
        ("a/topsecret.txt", "credential-like-name"),
        ("src/app.py", None),
        ("README.md", None),
        ("keys/id_rsa.pub", None),  # public key is intentionally NOT secret
        ("", None),
        (None, None),
        (123, None),
    ],
)
def test_classification_unchanged(path, expected):
    assert is_secret_path(path) == expected


def test_rule_classes_inventory_is_stable_strings():
    # The capability declaration enumerates these; they must be a non-empty tuple
    # of stable, machine-readable strings.
    assert isinstance(CREDENTIAL_PATH_RULE_CLASSES, tuple)
    assert CREDENTIAL_PATH_RULE_CLASSES
    assert all(isinstance(c, str) and c for c in CREDENTIAL_PATH_RULE_CLASSES)


def test_predicate_never_reads_the_file(tmp_path):
    # Passing a path to a real, readable credential file must classify by SHAPE
    # only — the function takes a string and never touches the filesystem.
    secret = tmp_path / ".env"
    secret.write_text("TOKEN=should-never-be-read\n", encoding="utf-8")
    assert is_secret_path(str(secret)) == ".env"

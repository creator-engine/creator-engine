"""Unit tests for the v3 G-3.7.0b ``gh``-stderr credential redactor.

``forge._redact.redact_gh_stderr`` masks token / JWT / ``Authorization``-header material in
a ``gh`` subprocess's stderr BEFORE that stderr is interpolated into a
:class:`ForgeConfigError` message (a message that may be logged or surfaced into evidence).

This is defense-in-depth (belt-and-suspenders): the scoped/installation token lives ONLY in
the child ``gh`` env (``GH_TOKEN``) and must never reach stderr — the forge ops pass no
secret on the argv and G-3.7.0a scrubs the child env. The redactor is the SECONDARY net for
the case ``gh`` ever emits a credential into its stderr. The redactor makes NO length/format
assumption about a token (GitHub App installation tokens are opaque, ~520-char ``ghs_`` JWTs)
and preserves all non-credential diagnostic text.
"""

from creator_engine_validator.forge._redact import redact_gh_stderr

_SENTINEL = "<redacted>"


# ---------------------------------------------------------------------------
# Token-shaped material is masked (no length/format assumption)
# ---------------------------------------------------------------------------
def test_masks_classic_ghs_token():
    tok = "ghs_minted_secret_value_0123456789ABCDEF"
    out = redact_gh_stderr(f"HTTP 401: Bad credentials (token {tok})")
    assert tok not in out
    assert _SENTINEL in out
    # the non-secret remainder is preserved for diagnosis
    assert "HTTP 401: Bad credentials" in out


def test_masks_long_opaque_installation_token_regardless_of_length():
    # The stateless ``ghs_APPID_JWT`` brownout shape: ~520 chars, App id cleartext, a
    # JWT body with ``.`` separators + base64url ``-``/``_``. Must be FULLY masked with NO
    # length cap and NO assumption about the embedded structure.
    body_a = "Q" * 240
    body_b = "Z" * 240
    sig = "k9-_xY" * 4
    tok = f"ghs_123456_eyJ{body_a}.{body_b}.{sig}"
    assert len(tok) > 500  # ~520-char, opaque
    out = redact_gh_stderr(f"could not mint: {tok}")
    assert tok not in out
    # no internal fragment of the token survives (defense against partial masking)
    for frag in (body_a, body_b, sig, "ghs_123456"):
        assert frag not in out
    assert _SENTINEL in out


def test_masks_other_github_token_prefixes():
    for tok in ("gho_OAuthTokenABCDEFGHIJ0123456789", "ghp_ClassicPAT0123456789ABCDEFGHIJ",
                "ghu_UserToServer0123456789ABCDEFGH", "ghr_Refresh0123456789ABCDEFGHIJKLMN",
                "github_pat_11AABBCCDD_0123456789abcdefghijABCDEFGHIJ0123456789"):
        out = redact_gh_stderr(f"rejected: {tok}")
        assert tok not in out
        assert _SENTINEL in out


def test_masks_three_segment_jwt():
    jwt = ("eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9"
           ".eyJpc3MiOiIxMjM0NTYiLCJpYXQiOjE2MDB9"
           ".SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c")
    out = redact_gh_stderr(f"jwt rejected: {jwt}")
    assert jwt not in out
    assert _SENTINEL in out


def test_masks_authorization_header_value():
    for header in ("Authorization: token ghs_secretsecretsecret0123456789",
                   "authorization: Bearer ghs_anothersecret0123456789ABCDEF",
                   "Authorization: Basic QWxhZGRpbjpvcGVuc2VzYW1l"):
        out = redact_gh_stderr(f"request used header [{header}]")
        # neither the credential nor the raw header value survives
        assert "ghs_secretsecretsecret0123456789" not in out
        assert "ghs_anothersecret0123456789ABCDEF" not in out
        assert "QWxhZGRpbjpvcGVuc2VzYW1l" not in out
        assert _SENTINEL in out


# ---------------------------------------------------------------------------
# No over-masking — benign diagnostic text passes through verbatim
# ---------------------------------------------------------------------------
def test_does_not_mask_benign_text():
    benign = "HTTP 404: Not Found (repos/creator-engine/creator-engine#7)"
    assert redact_gh_stderr(benign) == benign


def test_does_not_mask_a_bare_git_sha():
    sha = "d" * 40  # a 40-hex git SHA is not a credential and must not be masked
    msg = f"unexpected merge sha {sha}"
    out = redact_gh_stderr(msg)
    assert sha in out
    assert _SENTINEL not in out


def test_does_not_mask_the_word_token_in_prose():
    # the bare keyword "token" in ordinary error prose must NOT trigger masking
    msg = "the token is invalid or has expired"
    out = redact_gh_stderr(msg)
    assert out == msg
    assert _SENTINEL not in out


# ---------------------------------------------------------------------------
# Empty / whitespace -> empty (so the call-site ``or 'unknown error'`` still fires)
# ---------------------------------------------------------------------------
def test_empty_input_returns_empty():
    assert redact_gh_stderr("") == ""
    assert redact_gh_stderr("   \n  ") == ""


def test_strips_surrounding_whitespace():
    assert redact_gh_stderr("  Not Found  ") == "Not Found"


# ---------------------------------------------------------------------------
# Purity — a pure stdlib helper registers no check and adds no backend
# ---------------------------------------------------------------------------
def test_redactor_registers_no_check_and_no_backend():
    from creator_engine_validator.checks import registered_checks
    from creator_engine_validator.runner import available_backends

    assert len(registered_checks()) == 48  # G-6 added ce_scope; v3.5-C A-C1 added decision_record
    assert available_backends() == ("gvisor-proxy", "local-noop", "openshell")  # +openshell (v3.5-A.2a)

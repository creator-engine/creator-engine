# ce121-aarch64 Build Note

Date: 2026-06-18
Issue: ce-ops#121
Base: `5302520250c1510df9f8fac1d0b7268087228b4f`

## What Changed

- Added signed-manifest platform selection for `linux-x86_64-cp314` and
  `linux-aarch64-cp314` in `v3_installer.py` and `docs/install.sh`.
- Added aarch64 PyYAML, rpds-py, and uv wheels to both `validators/wheelhouse/`
  and `docs/downloads/0.2.0/`.
- Rebuilt `creator_engine_validator-0.2.0-py3-none-any.whl` after changing
  shipped installer code; final app-wheel sha256:
  `768451ab925bd9fe32d5187cec2fdb609920da81173fc42b41f482c48c112f85`.
- Regenerated `validators/wheelhouse/SHA256SUMS` and
  `docs/downloads/0.2.0/SHA256SUMS`; final mirror `SHA256SUMS` sha256:
  `e6460c09e925576bfe39ae9465fea1e589df182e318b520d6867be0cb145f86c`.
- Updated `docs/llms-install.md` with platform-aware wheel and uv acquisition
  entries. The signature `value` is intentionally
  `<RESIGN-REQUIRED-ce-root-v1>`; no signature was fabricated.

## Wheel Acquisition Evidence

Fetched with:

```bash
python3 -m pip download --only-binary=:all: --no-deps --python-version 3.14 --implementation cp --abi cp314 --platform manylinux2014_aarch64 --dest /tmp/ce121-aarch64-wh pyyaml==6.0.3 rpds-py==0.30.0 uv==0.11.21
```

Fetched files matched `/tmp/aarch64-probe/wh/` by sha256:

- `pyyaml-6.0.3-cp314-cp314-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl`
  `501a031947e3a9025ed4405a168e6ef5ae3126c59f90ce0cd6f2bfc477be31b7`
- `rpds_py-0.30.0-cp314-cp314-manylinux_2_17_aarch64.manylinux2014_aarch64.whl`
  `f251c812357a3fed308d684a5079ddfb9d933860fc6de89f2b7ab00da481e65f`
- `uv-0.11.21-py3-none-manylinux_2_17_aarch64.manylinux2014_aarch64.musllinux_1_1_aarch64.whl`
  `00193e4e077c27ee3d66da356744dbf0b3aa59356dfbd9a9efb1dc8469af8ad7`

The aarch64 uv acquisition tarball was fetched from the uv release and pinned as:

- `https://github.com/astral-sh/uv/releases/download/0.11.21/uv-aarch64-unknown-linux-gnu.tar.gz`
  `88e800834007cc5efd4675f166eb2a51e7e3ad19876d85fa8805a6fb5c922397`

## Test Evidence

Red evidence before implementation:

- Focused TDD run: 6 failed tests covering missing manifest platform metadata,
  Linux/aarch64 refusal, missing aarch64 uv path, and absent aarch64 wheels.

Green evidence:

- Focused installer/packaging/wheel surface suite:
  `175 passed, 1 skipped`.
- Full validator suite:
  `3407 passed, 2 skipped`.
- `bash -n docs/install.sh`: pass.
- `sha256sum -c validators/wheelhouse/SHA256SUMS`: pass.
- Staged mirror `sha256sum -c SHA256SUMS` with `install.sh` and all mirrored
  wheels in one directory: pass.
- `docs/llms-install.md` canonical hash equals embedded `content_sha256`:
  `2d2d4ef30da2371e3a5f78cbe23a401386658cc28dd9247e5c932b57bc6d59df`.

The x86_64 path remains covered by the existing installer integration test that
creates the venv, installs from the signed mirror wheelhouse, runs inventory, and
reruns idempotently.

## Operator Follow-Up

Reconstruct the canonical bytes:

```bash
sed -E 's#^(  value: ).*#\1<published-with-this-spec>#; s#^(  content_sha256: ).*#\1<published-with-this-spec>#' docs/llms-install.md > <canonical-file>
```

Sign with the offline Operator-held key:

```bash
ssh-keygen -Y sign -f ~/.ce-keys/ce-root-v1 -n ce-spec-v1 <canonical-file>
base64 -w0 <canonical-file>.sig
```

Then replace `value: <RESIGN-REQUIRED-ce-root-v1>` with the base64 output and
verify with stock `ssh-keygen -Y verify`. Publishing `docs/` to GitHub Pages is
a separate gated deploy after re-signing.

---

## #953 DGX image rebuild provenance addendum

Date: 2026-07-11. This is a PREP-only controller-attested record; no image was
built, fetched, published, loaded, or run while preparing the carrier.

- Codex 0.144.1 arm64 release artifact:
  `https://github.com/openai/codex/releases/download/rust-v0.144.1/codex-aarch64-unknown-linux-musl.tar.gz`.
  Controller-attested first-fetch SHA-256:
  `9513fa3f5f4ad444ac1e40d972aef0e2664834ec54da987d54aba0dc2f13ea07`.
  Production rebuilds compare the exact release asset in
  `codex-package_SHA256SUMS`; the sibling Sigstore attestation is
  `codex-aarch64-unknown-linux-musl.sigstore`.
- CPython `3.14-slim-bookworm` controller-attested from
  `docker buildx imagetools inspect` (Docker Library Python upstream revision
  `7914d06b7ddb`): manifest list
  `sha256:4ff4b92a68355dbdb52584ab3391dff8d371a61d4e063468bfd0130e3189c6d9`,
  `linux/amd64` child
  `sha256:01d4f0a9b0f284f9ef577e86a1ae7c7c22572e19fddc052d011c38217f856a94`,
  and `linux/arm64/v8` child
  `sha256:0670f5b579f8ba90903a95007ae10c890ac7f0d54de138ebd20574d56b10f3cc`.

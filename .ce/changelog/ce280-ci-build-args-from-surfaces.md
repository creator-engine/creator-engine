---
slug: ce280-ci-build-args-from-surfaces
date: 2026-06-27
kind: story
scope:
  - surfaces/render.py
  - deploy/oci/build-image.sh
  - deploy/oci/Dockerfile
  - deploy/vps-runsc/Dockerfile
  - deploy/dgx-runsc/Dockerfile
  - deploy/dgx-controller-runsc/Dockerfile
  - deploy/vps-runsc/build-image.sh
  - deploy/dgx-runsc/build-image.sh
  - deploy/dgx-controller-runsc/build-image.sh
issue: ce-ops#280
work_class: story
---

- **Declared work class:** story

Wired CI/build-image dry runs, supported image build wrappers, and Dockerfiles
to consume `surfaces/render.py build-args` for rented build surfaces.
Manifest-controlled Dockerfile image and toolchain inputs now default to
`UNSET`, while non-manifest build args such as `SOURCE_DATE_EPOCH`,
`CE_IMAGE_REVISION`, and runtime uid/gid/user args remain local.

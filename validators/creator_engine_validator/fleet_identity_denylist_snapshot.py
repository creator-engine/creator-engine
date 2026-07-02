"""Vendored CE identity denylist snapshot for fleet manifest validation.

Generated from the private identity registry. Do not vendor the source
registry body into this public repository.
"""

from __future__ import annotations

SOURCE_REPO = 'creator-engine/ce-ops'
SOURCE_PATH = 'infra/identity-registry.yaml'
SOURCE_BLOB_SHA = '1df56f9fef97633a3c1c2633d1be2ac59ca79081'

IDENTITY_REGISTRY_DENYLIST_TOKENS = (
    '100.100.105.50',
    '100.106.203.52',
    '100.72.252.20',
    '294754021+cedev4vps-coder@users.noreply.github.com',
    'approval-capability-wall',
    'ce-dev-1',
    'ce-dev-2',
    'ce-dev-3',
    'ce-dev-4',
    'ce-dev1-root-v1',
    'ce-kv/',
    'ce-kv/forge/',
    'ce-kv/forge/approval-capability/wall',
    'ce-kv/forge/approval-capability/wall#signing_secret',
    'ce-kv/forge/dev-1',
    'ce-kv/forge/dev-1#private_key',
    'ce-kv/forge/dev-3',
    'ce-kv/forge/dev-3#private_key',
    'ce-kv/forge/dev-4',
    'ce-kv/forge/dev-4#private_key',
    'ce-overwatch',
    'ce-root-v1',
    'ce-spec-v1',
    'cedev1',
    'cedev1vps-cmd',
    'cedev2',
    'cedev3',
    'cedev4',
    'creator-engine/*',
    'creator-engine/ce-ops',
    'creator-engine/creator-engine',
    'dev-1',
    'dev-2',
    'dev-2-overwatch',
    'dev-3',
    'dev-4',
    'dgx-spark-1',
    'egress-self-push-broker',
    'file:///home/ce-dev-1/.ce-keys',
    'file://~/.ce-keys/ce-dev-2.pat',
    'file://~/.ce-keys/ce-dev-4.pat',
    'file://~/.ce-keys/ce-dev1-root-v1',
    'file://~/.ce-keys/ce-root-v1',
    'file://~/.ce-keys/overwatch.env',
    'gvisor-runsc',
    'herdr-pty-substrate',
    'laptop-peer',
    'openbao-ref:ce-kv/forge/approval-capability/wall#signing_secret',
    'openbao-ref:ce-kv/forge/dev-1#private_key',
    'openbao-ref:ce-kv/forge/dev-3#private_key',
    'openbao-ref:ce-kv/forge/dev-4#private_key',
    'seat-dev-1',
    'seat-dev-3',
    'seat-dev-4',
    'spark-b824',
    'ubuntuaws745-cmyk',
)

"""Host-ops broker v1 library slice.

Slice 1 intentionally exposes a dict-in/dict-out dispatcher and injectable host
adapters only. Transport, caller authentication, live systemd/runtime/OpenBao
adapters, and service supervision are deferred by the ratified design.
"""
from __future__ import annotations

__all__ = ["__version__"]

__version__ = "v1"

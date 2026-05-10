"""Validation result and reporting helpers for FR-027."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class ValidationError:
    """A contract-referenced validator failure.

    FR-027 requires every failure to name the violated FR/clause, the field or
    path that violated it, and the contract document the reader can consult.
    """

    code: str
    path: str
    message: str
    contract: str

    def format(self) -> str:
        return f"{self.code}: {self.path}: {self.message} (consult {self.contract})"

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class CheckResult:
    name: str
    errors: tuple[ValidationError, ...] = ()
    warnings: tuple[ValidationError, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "ok": self.ok,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
        }


def make_error(code: str, path: str | Path, field: str, message: str, contract: str | Path) -> ValidationError:
    rendered_path = f"{path}:{field}" if field else str(path)
    return ValidationError(code=code, path=rendered_path, message=message, contract=str(contract))


def format_errors(errors: Iterable[ValidationError]) -> str:
    return "\n".join(error.format() for error in errors)

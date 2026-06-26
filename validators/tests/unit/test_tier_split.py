from __future__ import annotations

import ast
import tomllib
from pathlib import Path

VALIDATORS_ROOT = Path(__file__).resolve().parents[2]
TESTS_ROOT = VALIDATORS_ROOT / "tests"


def _python_files(path: Path) -> list[Path]:
    return sorted(path.glob("*.py"))


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _is_pytest_slow_attr(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "slow"
        and isinstance(node.value, ast.Attribute)
        and node.value.attr == "mark"
        and isinstance(node.value.value, ast.Name)
        and node.value.value.id == "pytest"
    )


def _contains_slow_mark(node: ast.AST) -> bool:
    if _is_pytest_slow_attr(node):
        return True
    if isinstance(node, ast.Call):
        return _contains_slow_mark(node.func) or any(
            _contains_slow_mark(arg) for arg in [*node.args, *(kw.value for kw in node.keywords)]
        )
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return any(_contains_slow_mark(elt) for elt in node.elts)
    return False


def _module_pytestmark_values(tree: ast.Module) -> list[ast.AST]:
    values: list[ast.AST] = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == "pytestmark" for target in node.targets):
                values.append(node.value)
        elif isinstance(node, ast.AnnAssign):
            target = node.target
            if isinstance(target, ast.Name) and target.id == "pytestmark" and node.value is not None:
                values.append(node.value)
    return values


def test_slow_marker_registered_in_pyproject() -> None:
    data = tomllib.loads((VALIDATORS_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    markers = data["tool"]["pytest"]["ini_options"]["markers"]

    assert any(marker.split(":", 1)[0].strip().split("(", 1)[0] == "slow" for marker in markers)


def test_all_integration_files_have_module_slow_mark() -> None:
    missing = []
    for path in _python_files(TESTS_ROOT / "integration"):
        values = _module_pytestmark_values(_tree(path))
        if not any(_contains_slow_mark(value) for value in values):
            missing.append(path.relative_to(VALIDATORS_ROOT).as_posix())

    assert missing == []


def test_unit_files_do_not_declare_slow_marks() -> None:
    offenders = []
    for path in _python_files(TESTS_ROOT / "unit"):
        tree = _tree(path)
        has_module_mark = any(_contains_slow_mark(value) for value in _module_pytestmark_values(tree))
        has_decorator_mark = any(
            _contains_slow_mark(decorator)
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            for decorator in node.decorator_list
        )
        if has_module_mark or has_decorator_mark:
            offenders.append(path.relative_to(VALIDATORS_ROOT).as_posix())

    assert offenders == []

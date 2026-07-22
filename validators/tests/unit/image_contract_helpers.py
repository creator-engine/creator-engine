"""Shared token-aware helpers for static Dockerfile RUN contracts.

The image-contract tests bind requirements to executable ``RUN`` commands,
not to comments or unrelated instructions.  These deliberately small parsing
helpers only need to identify top-level semicolon command boundaries; they do
not try to evaluate shell expansions.
"""

from __future__ import annotations

import re
import shlex


def _split_top_level_shell_commands(text: str) -> list[str]:
    """Split *text* at semicolons outside quotes and command substitutions.

    A Dockerfile currently uses a double-quoted command substitution containing
    further double quotes (``"$(find ... "$(basename ...)" ...)"``).  The
    former regex only tracked quote parity, so it could mistake that nesting
    for a top-level shell separator.  Track a quote state for every ``$(...)``
    nesting level instead and treat only a top-level unquoted ``;`` as a
    command boundary.
    """

    commands: list[str] = []
    start = 0
    quote_stack: list[str | None] = [None]
    index = 0
    while index < len(text):
        character = text[index]
        quote = quote_stack[-1]
        if character == "\\":
            index += 2
            continue
        if quote == "'":
            if character == "'":
                quote_stack[-1] = None
            index += 1
            continue
        if character == '"':
            quote_stack[-1] = None if quote == '"' else '"'
            index += 1
            continue
        if character == "'" and quote is None:
            quote_stack[-1] = "'"
            index += 1
            continue
        if character == "$" and index + 1 < len(text) and text[index + 1] == "(":
            quote_stack.append(None)
            index += 2
            continue
        if character == ")" and quote is None and len(quote_stack) > 1:
            quote_stack.pop()
            index += 1
            continue
        if character == ";" and quote is None and len(quote_stack) == 1:
            commands.append(text[start:index].strip())
            start = index + 1
        index += 1
    commands.append(text[start:].strip())
    return [command for command in commands if command]


def run_shell_commands(text: str) -> list[str]:
    """Return uncommented shell commands from Dockerfile ``RUN`` instructions."""

    blocks = re.findall(r"(?ms)^RUN\s+(.*?)(?=^[A-Z]+(?:\s|$)|\Z)", text)
    commands: list[str] = []
    for block in blocks:
        uncommented = "\n".join(
            line.split("#", 1)[0]
            for line in block.splitlines()
            if not line.lstrip().startswith("#")
        )
        commands.extend(_split_top_level_shell_commands(uncommented.replace("\\\n", " ")))
    return commands


def run_command_has_tokens(text: str, required: list[str]) -> bool:
    """Whether one ``RUN`` shell command contains *required* in order."""

    for command in run_shell_commands(text):
        try:
            tokens = shlex.split(command)
        except ValueError:
            continue
        normalised = [token.rstrip(";") for token in tokens]
        for start in range(len(normalised) - len(required) + 1):
            if start and not tokens[start - 1].endswith(";"):
                continue
            if required[:4] == ["apt-get", "install", "-y", "--no-install-recommends"]:
                command_end = next(
                    (index for index in range(start, len(tokens)) if tokens[index].endswith(";")),
                    len(tokens),
                )
                if (
                    normalised[start : start + 4] == required[:4]
                    and required[4] in normalised[start + 4 : command_end]
                ):
                    return True
            if normalised[start : start + len(required)] == required:
                return True
    return False

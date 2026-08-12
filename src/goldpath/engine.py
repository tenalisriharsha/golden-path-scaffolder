"""Minimal, strict template engine for golden-path-scaffolder.

Supports:
  - ``{{ variable }}`` substitution
  - ``{% if variable %} ... {% endif %}`` conditionals (nestable)

The engine is strict: referencing an undefined variable in either a
substitution or a conditional raises :class:`TemplateError`. Unbalanced
tags are also errors. There is deliberately no expression language —
golden path templates should be boring.
"""

from __future__ import annotations

import re
from typing import Mapping

__all__ = ["TemplateError", "render"]

_VAR = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}")
_TAG = re.compile(r"\{%\s*(if\s+[A-Za-z_][A-Za-z0-9_]*|endif)\s*%\}")


class TemplateError(Exception):
    """Raised for any malformed template or undefined variable."""


def render(template: str, context: Mapping[str, object]) -> str:
    """Render *template* against *context*.

    Raises :class:`TemplateError` on undefined variables or unbalanced tags.
    """
    out, pos = _render_block(template, 0, context, inside_if=False)
    if pos != len(template):  # pragma: no cover - defensive
        raise TemplateError("template not fully consumed")
    return _substitute(out, context)


def _render_block(
    text: str, pos: int, context: Mapping[str, object], inside_if: bool
) -> tuple[str, int]:
    """Render from *pos* until the matching ``{% endif %}`` (or end of text)."""
    chunks: list[str] = []
    while pos < len(text):
        match = _TAG.search(text, pos)
        if match is None:
            chunks.append(text[pos:])
            pos = len(text)
            break
        chunks.append(text[pos : match.start()])
        tag = match.group(1)
        if tag == "endif":
            if not inside_if:
                raise TemplateError("unexpected {% endif %} without matching {% if %}")
            return "".join(chunks), match.end()
        var = tag.split()[1]
        if var not in context:
            raise TemplateError(f"undefined variable in conditional: {var!r}")
        inner, pos = _render_block(text, match.end(), context, inside_if=True)
        if context[var]:
            chunks.append(inner)
    if inside_if:
        raise TemplateError("unclosed {% if %}: missing {% endif %}")
    return "".join(chunks), pos


def _substitute(text: str, context: Mapping[str, object]) -> str:
    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in context:
            raise TemplateError(f"undefined variable: {name!r}")
        return str(context[name])

    return _VAR.sub(replace, text)

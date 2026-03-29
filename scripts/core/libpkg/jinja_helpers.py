from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, Template


TEMPLATE_DIR = Path(__file__).parent / "templates"

_env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=False,
    trim_blocks=True,
    lstrip_blocks=True,
)


def render_template_file(template_name: str, **context: Any) -> str:
    tpl = _env.get_template(template_name)
    return tpl.render(**context)


def render_template_string(s: str, **context: Any) -> str:
    t = Template(s)
    return t.render(**context)

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    from jinja2 import Environment, FileSystemLoader, Template
    JINJA_AVAILABLE = True
except ImportError:
    JINJA_AVAILABLE = False


TEMPLATE_DIR = Path(__file__).parent / "templates"

_env = None
if JINJA_AVAILABLE:
    _env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_template_file(template_name: str, **context: Any) -> str:
    if _env is None:
        raise RuntimeError("jinja2 is required but not installed")
    tpl = _env.get_template(template_name)
    return tpl.render(**context)


def render_template_string(s: str, **context: Any) -> str:
    if not JINJA_AVAILABLE:
        raise RuntimeError("jinja2 is required but not installed")
    t = Template(s)
    return t.render(**context)

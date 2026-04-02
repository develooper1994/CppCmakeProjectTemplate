"""build package — backward-compatible re-exports.

Keeps ``from core.commands.build import main`` (and similar) working after
the monolith was split into sub-modules.
"""
from .cli import build_parser, main  # noqa: F401
from .commands import (  # noqa: F401
    cmd_build,
    cmd_check,
    cmd_clean,
    cmd_deploy,
    cmd_extension,
    cmd_docker,
)
from ._helpers import (  # noqa: F401
    DEFAULT_PRESET,
    EXT_DIR,
)

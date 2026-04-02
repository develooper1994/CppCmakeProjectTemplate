"""lib package — backward-compatible re-exports.

Keeps ``from core.commands.lib import main`` (and similar) working after
the monolith was split into sub-modules.
"""
from .cli import build_parser, main  # noqa: F401
from .commands import (  # noqa: F401
    cmd_add,
    cmd_deps,
    cmd_doctor,
    cmd_export,
    cmd_info,
    cmd_lib_upgrade_std,
    cmd_list,
    cmd_move,
    cmd_remove,
    cmd_rename,
    cmd_test,
    cmd_tree,
)
from ._helpers import LIBS_DIR  # noqa: F401

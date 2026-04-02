"""sol package — project orchestration commands.

Re-exports all public symbols for backward compatibility so that
``from core.commands.sol import main`` continues to work.
"""
from .cli import build_parser, main  # noqa: F401

# ── Helpers / constants ───────────────────────────────────────────────────────
from ._helpers import (  # noqa: F401
    TOOLCHAINS_DIR,
    PRESETS_FILE,
    FETCH_DEPS_FILE,
    VALID_COMPILERS,
    VALID_TYPES,
    VALID_LINKS,
    load_presets,
    load_fetch_deps,
    save_presets,
    _make_preset_name,
    _generate_custom_gnu,
)

# ── Target / preset commands ─────────────────────────────────────────────────
from .targets import (  # noqa: F401
    cmd_target_list,
    cmd_target_build,
    cmd_target_add,
    cmd_preset_list,
    cmd_preset_add,
    cmd_preset_remove,
)

# ── Toolchain / sysroot commands ──────────────────────────────────────────────
from .toolchains import (  # noqa: F401
    cmd_toolchain_list,
    cmd_toolchain_add,
    cmd_toolchain_remove,
    cmd_sysroot_add,
    _cmd_sysroot_list,
)

# ── Project-wide commands ─────────────────────────────────────────────────────
from .project import (  # noqa: F401
    cmd_config_get,
    cmd_config_set,
    cmd_doctor,
    cmd_test_run,
    cmd_upgrade_std,
    cmd_check_extra,
    cmd_init_skeleton,
    cmd_ci,
    cmd_cmake_version,
    cmd_clangd,
)

# ── Repo commands ─────────────────────────────────────────────────────────────
from .repo import (  # noqa: F401
    cmd_repo_list,
    cmd_repo_add_submodule,
    cmd_repo_add_fetch,
    cmd_repo_sync,
    cmd_repo_versions,
)

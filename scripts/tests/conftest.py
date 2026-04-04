import datetime

import pytest


def pytest_sessionstart(session):
    """Reset global CLI flags before test collection to avoid module-level
    test assignments leaking into other tests (some tests set
    GlobalConfig.JSON=True at import-time).
    """
    try:
        from core.utils.common import GlobalConfig
        GlobalConfig.DRY_RUN = False
        GlobalConfig.YES = False
        GlobalConfig.JSON = False
        GlobalConfig.VERBOSE = False
    except Exception:
        pass


@pytest.fixture(autouse=True)
def isolate_logging_and_globals(tmp_path, monkeypatch):
    """Per-test isolation: redirect log file to a tmp location and silence
    console Logger output to avoid noisy test output and prevent writes to
    repository build_logs during tests. Restores GlobalConfig after each test.
    """
    try:
        from core.utils import common
        from core.utils.common import GlobalConfig
    except Exception:
        yield
        return

    # Snapshot current global flags and LOG_FILE
    orig_flags = (
        GlobalConfig.DRY_RUN,
        GlobalConfig.YES,
        GlobalConfig.JSON,
        GlobalConfig.VERBOSE,
    )
    orig_log_file = common.LOG_FILE

    # Redirect LOG_FILE into tmp_path to avoid polluting repo
    monkeypatch.setattr(common, "LOG_FILE", tmp_path / "build_logs" / "tool.log")

    # Replace Logger._log with a silent writer that does not print to stdout
    def _silent_log(level: str, msg: str, color: str = ""):
        try:
            log_path = common.LOG_FILE
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(log_path, "a", encoding="utf-8") as f:
                ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"{ts} {level:<8} {msg}\n")
        except Exception:
            pass

    monkeypatch.setattr(common.Logger, "_log", staticmethod(_silent_log))

    # Ensure JSON mode is disabled for tests by default so textual output is
    # visible to tests that assert on human-friendly messages.
    GlobalConfig.JSON = False

    try:
        yield
    finally:
        # Restore globals
        GlobalConfig.DRY_RUN, GlobalConfig.YES, GlobalConfig.JSON, GlobalConfig.VERBOSE = orig_flags
        monkeypatch.setattr(common, "LOG_FILE", orig_log_file)

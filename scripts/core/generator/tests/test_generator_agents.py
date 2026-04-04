"""
Tests for core/generator/agents.py — AI agent instructions generator.
"""
from __future__ import annotations

import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

import pytest

_SCRIPTS = Path(__file__).resolve().parent.parent.parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


@dataclass
class MockContext:
    name: str = "TestProj"
    version: str = "1.0.0"
    description: str = "Test desc"
    author: str = "Tester"
    cxx_standard: str = "17"
    libs: list[dict] = field(default_factory=lambda: [{"name": "lib1"}])
    apps: list[dict] = field(default_factory=lambda: [{"name": "app1"}])


@pytest.fixture
def ctx():
    return MockContext()


class TestGeneratorAgents:
    def test_generate_all_returns_files(self, ctx):
        from core.generator.agents import generate_all
        files = generate_all(ctx, Path("/tmp"))
        
        assert "AGENTS.md" in files
        assert ".github/copilot-instructions.md" in files
        assert ".cursorrules" in files
        assert ".clinerules" in files
        assert ".claude/instructions.md" in files

    def test_agents_md_contains_metadata(self, ctx):
        from core.generator.agents import _gen_agents_md
        content = _gen_agents_md(ctx)
        
        assert "TestProj" in content
        assert "C++17" in content
        assert "`lib1`" in content
        assert "`app1`" in content

    def test_copilot_instructions_contains_metadata(self, ctx):
        from core.generator.agents import _gen_copilot_instructions
        content = _gen_copilot_instructions(ctx)
        
        assert "TestProj" in content
        assert "C++17" in content
        assert "- `lib1`" in content

    def test_cursorrules_contains_metadata(self, ctx):
        from core.generator.agents import _gen_cursorrules
        content = _gen_cursorrules(ctx)
        
        assert "TestProj" in content
        assert "C++17" in content

    def test_clinerules_contains_metadata(self, ctx):
        from core.generator.agents import _gen_clinerules
        content = _gen_clinerules(ctx)
        
        assert "TestProj" in content
        assert "C++17" in content

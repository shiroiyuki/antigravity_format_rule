#!/usr/bin/env python3
"""
Unit tests for Antigravity Customization Standards Validator (scripts/validate.py)
"""

import unittest
import tempfile
from pathlib import Path
import sys

# Add scripts directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import validate


class TestAntigravityValidator(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dir_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_valid_rule_file(self):
        rule = self.dir_path / "valid_rule.md"
        rule.write_text(
            "---\n"
            "trigger: model_decision\n"
            "description: 'Valid description for routing'\n"
            "---\n\n"
            "# Valid Rule\n"
            "Content here\n",
            encoding="utf-8"
        )
        errors = validate.validate_rule_file(rule)
        self.assertEqual(errors, [])

    def test_invalid_always_on_flag(self):
        rule = self.dir_path / "invalid_always_on.md"
        rule.write_text(
            "---\n"
            "always_on: true\n"
            "---\n\n"
            "# Bad Rule\n",
            encoding="utf-8"
        )
        errors = validate.validate_rule_file(rule)
        self.assertTrue(any("always_on: true" in e for e in errors))

    def test_missing_trigger(self):
        rule = self.dir_path / "no_trigger.md"
        rule.write_text(
            "---\n"
            "description: 'test'\n"
            "---\n\n"
            "# Bad Rule\n",
            encoding="utf-8"
        )
        errors = validate.validate_rule_file(rule)
        self.assertTrue(any("缺少 `trigger`" in e for e in errors))

    def test_model_decision_missing_description(self):
        rule = self.dir_path / "missing_desc.md"
        rule.write_text(
            "---\n"
            "trigger: model_decision\n"
            "---\n\n"
            "# Bad Rule\n",
            encoding="utf-8"
        )
        errors = validate.validate_rule_file(rule)
        self.assertTrue(any("description" in e for e in errors))

    def test_oversized_rule_file(self):
        rule = self.dir_path / "huge_rule.md"
        rule.write_text(
            "---\n"
            "trigger: always_on\n"
            "---\n\n"
            + ("A" * 24005),
            encoding="utf-8"
        )
        errors = validate.validate_rule_file(rule)
        self.assertTrue(any("24,000 bytes" in e for e in errors))

    def test_agents_md_no_frontmatter(self):
        rule = self.dir_path / "AGENTS.md"
        rule.write_text(
            "---\n"
            "trigger: model_decision\n"
            "---\n\n"
            "# AGENTS\n",
            encoding="utf-8"
        )
        errors = validate.validate_rule_file(rule)
        self.assertTrue(any("不應宣告 YAML Frontmatter" in e for e in errors))

    def test_valid_agent_file(self):
        agent = self.dir_path / "agent.md"
        agent.write_text(
            "---\n"
            "name: test-agent\n"
            "description: 'test agent description'\n"
            "model: flash\n"
            "subagent: true\n"
            "tools:\n"
            "  - read_file\n"
            "  - write_file\n"
            "---\n\n"
            "# Test Agent\n"
            "Prompt here\n",
            encoding="utf-8"
        )
        errors = validate.validate_agent_file(agent)
        self.assertEqual(errors, [])

    def test_deprecated_agent_fields(self):
        agent = self.dir_path / "agent.md"
        agent.write_text(
            "---\n"
            "name: bad-agent\n"
            "enable_write_tools: true\n"
            "tools:\n"
            "  - read_file\n"
            "---\n\n"
            "# Bad Agent\n",
            encoding="utf-8"
        )
        errors = validate.validate_agent_file(agent)
        self.assertTrue(any("enable_write_tools" in e for e in errors))

    def test_agent_missing_tools(self):
        agent = self.dir_path / "agent.md"
        agent.write_text(
            "---\n"
            "name: bad-agent\n"
            "model: pro\n"
            "---\n\n"
            "# Bad Agent\n",
            encoding="utf-8"
        )
        errors = validate.validate_agent_file(agent)
        self.assertTrue(any("未宣告 `tools`" in e for e in errors))

    def test_glob_trigger_valid(self):
        rule = self.dir_path / "glob_rule.md"
        rule.write_text(
            "---\n"
            "trigger: glob\n"
            "globs: '**/*.ts, **/*.tsx'\n"
            "---\n\n"
            "# TS Rule\n",
            encoding="utf-8"
        )
        errors = validate.validate_rule_file(rule)
        self.assertEqual(errors, [])

    def test_glob_trigger_missing_globs(self):
        rule = self.dir_path / "glob_missing.md"
        rule.write_text(
            "---\n"
            "trigger: glob\n"
            "---\n\n"
            "# TS Rule\n",
            encoding="utf-8"
        )
        errors = validate.validate_rule_file(rule)
        self.assertTrue(any("globs" in e for e in errors))

    def test_manual_trigger(self):
        rule = self.dir_path / "manual_rule.md"
        rule.write_text(
            "---\n"
            "trigger: manual\n"
            "---\n\n"
            "# Manual Rule\n",
            encoding="utf-8"
        )
        errors = validate.validate_rule_file(rule)
        self.assertEqual(errors, [])

    def test_agent_missing_h1(self):
        agent = self.dir_path / "agent.md"
        agent.write_text(
            "---\n"
            "name: bad-agent\n"
            "tools:\n"
            "  - read_file\n"
            "---\n\n"
            "No heading here, just prompt.\n",
            encoding="utf-8"
        )
        errors = validate.validate_agent_file(agent)
        self.assertTrue(any("# H1" in e for e in errors))


if __name__ == "__main__":
    unittest.main()

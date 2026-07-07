"""Tests for the Security Plugin.

Focused on pure helpers (`_strip_score_tags`, `_build_context`) that survive
the SDK port; class-shape tests were retired with the PluginBase model.
"""

from skillberry_plugin_security.plugin import SkillberryPluginSecurity


def test_plugin_manifest_slug():
    plugin = SkillberryPluginSecurity()
    assert plugin.manifest.slug == "security"


def test_plugin_manifest_has_api():
    plugin = SkillberryPluginSecurity()
    assert plugin.manifest.has_api is True


# ── helper: _strip_score_tags ────────────────────────────────────────────────

def test_strip_score_tags_removes_only_security():
    plugin = SkillberryPluginSecurity()
    tags = ["python", "security-score:4", "quality-score:8", "performance-score:7", "utility"]
    result = plugin._strip_score_tags(tags)
    assert result == ["python", "quality-score:8", "performance-score:7", "utility"]


def test_strip_score_tags_no_security_tag_unchanged():
    plugin = SkillberryPluginSecurity()
    tags = ["python", "utility"]
    assert plugin._strip_score_tags(tags) == ["python", "utility"]


def test_strip_score_tags_empty_list():
    plugin = SkillberryPluginSecurity()
    assert plugin._strip_score_tags([]) == []


# ── helper: _build_context ───────────────────────────────────────────────────

def test_build_context_excludes_previous_security_from_extra():
    plugin = SkillberryPluginSecurity()
    obj = {
        "name": "my_tool",
        "description": "does something",
        "extra": {
            "custom_key": "keep_me",
            "evaluation": {"security": {"score": 4, "evaluation": "old finding"}},
        },
        "tags": [],
    }
    context = plugin._build_context(obj, "tool")
    assert "keep_me" in context
    assert "old finding" not in context


def test_build_context_tool_includes_key_fields():
    plugin = SkillberryPluginSecurity()
    obj = {
        "uuid": "tool-1",
        "name": "my_tool",
        "description": "does something useful",
        "programming_language": "python",
        "packaging_format": "code",
        "params": {"type": "object", "properties": {}},
        "tags": ["utility"],
        "extra": {},
    }
    context = plugin._build_context(obj, "tool")
    assert "my_tool" in context
    assert "does something useful" in context
    assert "python" in context


def test_build_context_skill_includes_uuids():
    plugin = SkillberryPluginSecurity()
    obj = {
        "name": "my_skill",
        "description": "orchestrates things",
        "tool_uuids": ["uuid-a", "uuid-b"],
        "snippet_uuids": ["uuid-c"],
        "tags": [],
        "extra": {},
    }
    context = plugin._build_context(obj, "skill")
    assert "my_skill" in context
    assert "uuid-a" in context
    assert "uuid-c" in context


def test_build_context_snippet_includes_content():
    plugin = SkillberryPluginSecurity()
    obj = {
        "name": "my_snippet",
        "description": "a greeting",
        "content": "Hello World",
        "content_type": "text/plain",
        "tags": [],
        "extra": {},
    }
    context = plugin._build_context(obj, "snippet")
    assert "Hello World" in context
    assert "my_snippet" in context

"""Tests for AUTO_DETECT_TOOL_DEPENDENCIES environment flag."""

import os
import pytest
from unittest import mock
from skillberry_store.tools.configure import is_auto_detect_dependencies_enabled


class TestAutoDetectFlag:
    """Test cases for the auto-detect dependencies flag."""

    def test_default_enabled(self):
        """Test that auto-detection is enabled by default."""
        with mock.patch.dict(os.environ, {}, clear=True):
            assert is_auto_detect_dependencies_enabled() is True

    def test_explicitly_enabled_true(self):
        """Test that 'true' enables auto-detection."""
        with mock.patch.dict(os.environ, {"AUTO_DETECT_TOOL_DEPENDENCIES": "true"}):
            assert is_auto_detect_dependencies_enabled() is True

    def test_explicitly_enabled_1(self):
        """Test that '1' enables auto-detection."""
        with mock.patch.dict(os.environ, {"AUTO_DETECT_TOOL_DEPENDENCIES": "1"}):
            assert is_auto_detect_dependencies_enabled() is True

    def test_explicitly_enabled_yes(self):
        """Test that 'yes' enables auto-detection."""
        with mock.patch.dict(os.environ, {"AUTO_DETECT_TOOL_DEPENDENCIES": "yes"}):
            assert is_auto_detect_dependencies_enabled() is True

    def test_explicitly_enabled_on(self):
        """Test that 'on' enables auto-detection."""
        with mock.patch.dict(os.environ, {"AUTO_DETECT_TOOL_DEPENDENCIES": "on"}):
            assert is_auto_detect_dependencies_enabled() is True

    def test_explicitly_disabled_false(self):
        """Test that 'false' disables auto-detection."""
        with mock.patch.dict(os.environ, {"AUTO_DETECT_TOOL_DEPENDENCIES": "false"}):
            assert is_auto_detect_dependencies_enabled() is False

    def test_explicitly_disabled_0(self):
        """Test that '0' disables auto-detection."""
        with mock.patch.dict(os.environ, {"AUTO_DETECT_TOOL_DEPENDENCIES": "0"}):
            assert is_auto_detect_dependencies_enabled() is False

    def test_explicitly_disabled_no(self):
        """Test that 'no' disables auto-detection."""
        with mock.patch.dict(os.environ, {"AUTO_DETECT_TOOL_DEPENDENCIES": "no"}):
            assert is_auto_detect_dependencies_enabled() is False

    def test_case_insensitive(self):
        """Test that the flag is case-insensitive."""
        with mock.patch.dict(os.environ, {"AUTO_DETECT_TOOL_DEPENDENCIES": "TRUE"}):
            assert is_auto_detect_dependencies_enabled() is True
        
        with mock.patch.dict(os.environ, {"AUTO_DETECT_TOOL_DEPENDENCIES": "FALSE"}):
            assert is_auto_detect_dependencies_enabled() is False

    def test_invalid_value_defaults_to_false(self):
        """Test that invalid values default to False."""
        with mock.patch.dict(os.environ, {"AUTO_DETECT_TOOL_DEPENDENCIES": "invalid"}):
            assert is_auto_detect_dependencies_enabled() is False
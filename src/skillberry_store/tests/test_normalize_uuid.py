"""Tests for UUID normalization utility."""

import pytest
from skillberry_store.utils.utils import normalize_uuid


class TestNormalizeUuid:
    """Test suite for normalize_uuid function."""

    def test_normalize_valid_lowercase_uuid(self):
        """Test that a valid lowercase UUID is returned as-is."""
        uuid_str = "12345678-1234-1234-1234-123456789abc"
        result = normalize_uuid(uuid_str)
        assert result == uuid_str

    def test_normalize_valid_uppercase_uuid(self):
        """Test that a valid uppercase UUID is normalized to lowercase."""
        uuid_str = "12345678-1234-1234-1234-123456789ABC"
        expected = "12345678-1234-1234-1234-123456789abc"
        result = normalize_uuid(uuid_str)
        assert result == expected

    def test_normalize_valid_mixed_case_uuid(self):
        """Test that a valid mixed-case UUID is normalized to lowercase."""
        uuid_str = "ABCDEF12-3456-7890-ABCD-ef1234567890"
        expected = "abcdef12-3456-7890-abcd-ef1234567890"
        result = normalize_uuid(uuid_str)
        assert result == expected

    def test_normalize_uuid_without_hyphens(self):
        """Test that a UUID without hyphens is normalized correctly."""
        uuid_str = "12345678123412341234123456789abc"
        expected = "12345678-1234-1234-1234-123456789abc"
        result = normalize_uuid(uuid_str)
        assert result == expected

    def test_normalize_invalid_uuid_returns_none(self):
        """Test that an invalid UUID returns None."""
        invalid_uuid = "invalid-uuid-string"
        result = normalize_uuid(invalid_uuid)
        assert result is None

    def test_normalize_none_returns_none(self):
        """Test that None input returns None."""
        result = normalize_uuid(None)
        assert result is None

    def test_normalize_empty_string_returns_none(self):
        """Test that an empty string returns None."""
        result = normalize_uuid("")
        assert result is None

    def test_normalize_uuid_with_extra_characters(self):
        """Test that a UUID with extra characters returns None."""
        invalid_uuid = "12345678-1234-1234-1234-123456789abc-extra"
        result = normalize_uuid(invalid_uuid)
        assert result is None

    def test_normalize_uuid_too_short(self):
        """Test that a UUID that's too short returns None."""
        invalid_uuid = "12345678-1234-1234-1234"
        result = normalize_uuid(invalid_uuid)
        assert result is None

    def test_normalize_uuid_with_invalid_characters(self):
        """Test that a UUID with invalid characters returns None."""
        invalid_uuid = "12345678-1234-1234-1234-123456789xyz"
        result = normalize_uuid(invalid_uuid)
        assert result is None

    def test_normalize_uuid_consistency(self):
        """Test that normalizing the same UUID multiple times gives consistent results."""
        uuid_str = "ABCDEF12-3456-7890-ABCD-EF1234567890"
        result1 = normalize_uuid(uuid_str)
        result2 = normalize_uuid(uuid_str)
        assert result1 == result2

    def test_normalize_uuid_idempotent(self):
        """Test that normalizing an already normalized UUID returns the same value."""
        uuid_str = "12345678-1234-1234-1234-123456789abc"
        result = normalize_uuid(uuid_str)
        result2 = normalize_uuid(result)
        assert result == result2

    def test_normalize_uuid_version_4(self):
        """Test normalization of a valid UUID version 4."""
        uuid_str = "550e8400-e29b-41d4-a716-446655440000"
        result = normalize_uuid(uuid_str)
        assert result == uuid_str

    def test_normalize_uuid_all_zeros(self):
        """Test normalization of a UUID with all zeros."""
        uuid_str = "00000000-0000-0000-0000-000000000000"
        result = normalize_uuid(uuid_str)
        assert result == uuid_str

    def test_normalize_uuid_all_fs(self):
        """Test normalization of a UUID with all Fs."""
        uuid_str = "FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF"
        expected = "ffffffff-ffff-ffff-ffff-ffffffffffff"
        result = normalize_uuid(uuid_str)
        assert result == expected

# Made with Bob

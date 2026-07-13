"""Schema-level tests for VnfsSchema, including the npx_compat protocol rule."""

import pytest
from pydantic import ValidationError

from skillberry_store.schemas.vnfs_schema import VnfsSchema


def test_defaults_are_backwards_compatible() -> None:
    """A schema built without npx_compat behaves like it always has."""
    schema = VnfsSchema(name="foo")
    assert schema.protocol == "webdav"
    assert schema.npx_compat is False


def test_webdav_with_npx_compat_accepted() -> None:
    schema = VnfsSchema(name="foo", protocol="webdav", npx_compat=True)
    assert schema.npx_compat is True


def test_webdav_without_npx_compat_accepted() -> None:
    schema = VnfsSchema(name="foo", protocol="webdav", npx_compat=False)
    assert schema.npx_compat is False


def test_nfs_with_npx_compat_rejected() -> None:
    with pytest.raises(ValidationError) as info:
        VnfsSchema(name="foo", protocol="nfs", npx_compat=True)
    assert "npx_compat" in str(info.value)
    assert "webdav" in str(info.value)


def test_nfs_without_npx_compat_accepted() -> None:
    schema = VnfsSchema(name="foo", protocol="nfs")
    assert schema.protocol == "nfs"
    assert schema.npx_compat is False


def test_from_dict_ignores_unknown_fields() -> None:
    schema = VnfsSchema.from_dict(
        {
            "name": "foo",
            "protocol": "webdav",
            "npx_compat": True,
            "not_a_real_field": "ignored",
        }
    )
    assert schema.npx_compat is True


def test_from_dict_missing_flag_defaults_to_false() -> None:
    schema = VnfsSchema.from_dict({"name": "foo", "protocol": "nfs"})
    assert schema.npx_compat is False

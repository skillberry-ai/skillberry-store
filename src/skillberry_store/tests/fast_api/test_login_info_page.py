# Copyright 2025 IBM Corp.
# Licensed under the Apache License, Version 2.0
"""Unit tests for the login-message serving helpers.

``test_ui_serving.py`` covers the same behavior through the real ``/ui`` route;
these test the module directly, with no app and no HTTP, so a failure points at
the injection or the response construction rather than at the route.

See §6.1-6.2 of docs/design/login-info.md.
"""

from __future__ import annotations

import logging
from html import unescape

import pytest

from skillberry_store.fast_api.login_info import (
    LOGIN_INFO_META_NAME,
    LoginInfoPage,
    inject_login_info,
    render_login_info_meta,
)

MESSAGE = "Shared eval box — do not store secrets."
INDEX_HTML = (
    b'<!doctype html><html><head><title>t</title></head>'
    b"<body><div id='root'></div></body></html>"
)


class _FakeRequest:
    """Just the one attribute the helpers read."""

    def __init__(self, method: str = "GET") -> None:
        self.method = method


@pytest.fixture
def bundle(tmp_path):
    """A minimal bundle directory with an entry point and one hashed asset."""
    (tmp_path / "index.html").write_bytes(INDEX_HTML)
    (tmp_path / "app-abc123.js").write_text("console.log('bundle')")
    return tmp_path


# --------------------------------------------------------------------------- #
# render_login_info_meta
# --------------------------------------------------------------------------- #

def test_meta_tag_carries_the_agreed_name():
    assert f'name="{LOGIN_INFO_META_NAME}"' in render_login_info_meta(MESSAGE)


def test_meta_tag_escapes_quotes_and_angle_brackets():
    """The value must not be able to terminate the attribute or the tag."""
    raw = 'he said "hi" <b>&</b> \'x\''
    tag = render_login_info_meta(raw)

    content = tag.split('content="', 1)[1].rsplit('">', 1)[0]
    assert '"' not in content
    assert "<" not in content
    assert ">" not in content
    assert unescape(content) == raw


# --------------------------------------------------------------------------- #
# inject_login_info
# --------------------------------------------------------------------------- #

def test_injection_lands_immediately_before_head_close():
    out = inject_login_info(INDEX_HTML, MESSAGE).decode("utf-8")

    assert out.index(LOGIN_INFO_META_NAME) < out.index("</head>")
    assert out.endswith("</html>")
    assert "<title>t</title>" in out, "the original head must be preserved"


@pytest.mark.parametrize("close_tag", ["</head>", "</HEAD>", "</head >"])
def test_head_close_is_matched_case_insensitively_and_loosely(close_tag):
    html = f"<html><head>{close_tag}<body></body></html>".encode()

    assert LOGIN_INFO_META_NAME in inject_login_info(html, MESSAGE).decode()


def test_only_the_first_head_close_is_used():
    html = b"<html><head></head><body></head></body></html>"

    out = inject_login_info(html, MESSAGE).decode()

    assert out.count(LOGIN_INFO_META_NAME) == 1


def test_html_without_a_head_close_is_returned_unchanged_with_a_warning(caplog):
    html = b"<html><body><div id='root'></div></body></html>"

    with caplog.at_level(logging.WARNING):
        out = inject_login_info(html, MESSAGE)

    assert out == html
    assert "</head>" in caplog.text


# --------------------------------------------------------------------------- #
# LoginInfoPage
# --------------------------------------------------------------------------- #

def test_no_message_builds_an_inert_page(bundle):
    page = LoginInfoPage.build(bundle, None)

    assert page.active is False
    assert page.response_for_fallback(_FakeRequest(), "no-cache") is None
    assert (
        page.response_for_asset(_FakeRequest(), bundle / "index.html", "no-cache")
        is None
    )


def test_a_missing_entry_point_builds_an_inert_page(tmp_path):
    """A bare checkout with no bundle must not raise at startup."""
    page = LoginInfoPage.build(tmp_path / "missing", MESSAGE)

    assert page.active is False
    assert page.response_for_fallback(_FakeRequest(), "no-cache") is None


def test_an_active_page_serves_the_injected_bytes(bundle):
    page = LoginInfoPage.build(bundle, MESSAGE)
    assert page.active is True

    resp = page.response_for_fallback(_FakeRequest(), "no-cache, must-revalidate")

    assert resp is not None
    assert LOGIN_INFO_META_NAME in resp.body.decode()
    assert resp.headers["cache-control"] == "no-cache, must-revalidate"
    assert resp.headers["content-type"].startswith("text/html")


def test_the_asset_branch_matches_only_the_entry_point(bundle):
    """A hashed asset must keep its FileResponse — hence None here."""
    page = LoginInfoPage.build(bundle, MESSAGE)
    request = _FakeRequest()

    assert (
        page.response_for_asset(request, (bundle / "index.html").resolve(), "c")
        is not None
    )
    assert page.response_for_asset(request, bundle / "app-abc123.js", "c") is None


def test_a_second_html_file_is_not_served_the_entry_points_bytes(bundle):
    """Only index.html has a pre-rendered copy; another .html must not get it."""
    other = bundle / "other.html"
    other.write_text("<html><head></head><body>other</body></html>")
    page = LoginInfoPage.build(bundle, MESSAGE)

    assert page.response_for_asset(_FakeRequest(), other.resolve(), "c") is None


def test_head_reports_the_get_length_without_a_body(bundle):
    page = LoginInfoPage.build(bundle, MESSAGE)

    get = page.response_for_fallback(_FakeRequest("GET"), "c")
    head = page.response_for_fallback(_FakeRequest("HEAD"), "c")

    assert get is not None and head is not None
    assert head.body == b""
    assert head.headers["content-length"] == str(len(get.body))

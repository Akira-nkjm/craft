"""Unit tests for core/concurrency.py — resolve_expected_etag."""

import pytest

from craft.core.errors import PreconditionRequired
from craft.core.surface_ops.concurrency import resolve_expected_etag


def test_provided_etag_returned_directly():
    result = resolve_expected_etag('W/"sha256:abc"', "required", fetch=lambda: "should-not-call")
    assert result == 'W/"sha256:abc"'


def test_provided_etag_returned_in_auto_mode():
    result = resolve_expected_etag('W/"sha256:abc"', "auto", fetch=lambda: "should-not-call")
    assert result == 'W/"sha256:abc"'


def test_required_mode_no_etag_raises():
    with pytest.raises(PreconditionRequired, match="ETag is required"):
        resolve_expected_etag(None, "required", fetch=lambda: "fetched")


def test_auto_mode_no_etag_calls_fetch():
    result = resolve_expected_etag(None, "auto", fetch=lambda: 'W/"sha256:fetched"')
    assert result == 'W/"sha256:fetched"'


def test_auto_mode_fetch_exception_propagates():
    class CustomError(Exception):
        pass

    with pytest.raises(CustomError):
        resolve_expected_etag(
            None, "auto", fetch=lambda: (_ for _ in ()).throw(CustomError("boom"))
        )


def test_fetch_not_called_in_required_mode():
    called = []

    def tracking_fetch() -> str:
        called.append(True)
        return "etag"

    with pytest.raises(PreconditionRequired):
        resolve_expected_etag(None, "required", fetch=tracking_fetch)

    assert called == [], "fetch should not be called in required mode"


def test_required_mode_error_message_is_actionable():
    with pytest.raises(PreconditionRequired) as exc_info:
        resolve_expected_etag(None, "required", fetch=lambda: "")
    assert "--auto-etag" in str(exc_info.value)

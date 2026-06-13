"""Tests for Config model validation and defaults.

Imports Config + MissingAPIKeyError inside each test function (NOT at module
level) because importing the plugin's config module triggers NoneBot side effects
that require a running runtime.
"""

from __future__ import annotations

import pytest


def test_empty_api_key_raises_validation_error() -> None:
    """Config(apex_api_key="") must raise a ValidationError.

    Pydantic v2 wraps field-validator exceptions in ``ValidationError``
    with error type ``value_error``.  The original ``MissingAPIKeyError``
    (a ``ValueError`` subclass) is caught and converted by Pydantic;
    the chained exception is *not* preserved on ``ValidationError``.
    """
    from pydantic import ValidationError

    from nonebot_plugin_apex_api_query.config import Config

    with pytest.raises(ValidationError) as exc_info:
        Config(apex_api_key="")
    errors = exc_info.value.errors()
    assert len(errors) == 1
    assert errors[0]["type"] == "value_error"
    assert errors[0]["input"] == ""


def test_valid_api_key_succeeds() -> None:
    """Config(apex_api_key="valid-key") must construct without error."""
    from nonebot_plugin_apex_api_query.config import Config

    cfg = Config(apex_api_key="valid-key")
    assert cfg.apex_api_key == "valid-key"


def test_whitespace_only_key_passes() -> None:
    """Config(apex_api_key="   ") must NOT raise — truthiness edge case.

    The validator uses ``if not v:``, and a whitespace-only string is truthy
    in Python.  This is an intentional edge case: the plugin does not strip or
    otherwise sanitise the key beyond the empty check.
    """
    from nonebot_plugin_apex_api_query.config import Config

    cfg = Config(apex_api_key="   ")
    assert cfg.apex_api_key == "   "


def test_default_apex_api_url() -> None:
    """Default apex_api_url must be https://api.mozambiquehe.re."""
    from nonebot_plugin_apex_api_query.config import Config

    cfg = Config(apex_api_key="k")
    assert cfg.apex_api_url == "https://api.mozambiquehe.re"


def test_default_apex_map_api_url() -> None:
    """Default apex_map_api_url must be https://api.apexlegendsstatus.com."""
    from nonebot_plugin_apex_api_query.config import Config

    cfg = Config(apex_api_key="k")
    assert cfg.apex_map_api_url == "https://api.apexlegendsstatus.com"


def test_default_apex_only_text_is_false() -> None:
    """Default apex_only_text must be False."""
    from nonebot_plugin_apex_api_query.config import Config

    cfg = Config(apex_api_key="k")
    assert cfg.apex_only_text is False

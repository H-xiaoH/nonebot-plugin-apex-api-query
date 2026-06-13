"""Tests for nonebot_plugin_apex_api_query.data — convert() and constants.

All plugin imports are inside test functions because the plugin's __init__.py
has module-level side effects (get_driver(), etc.) that require a running
NoneBot runtime.
"""

from __future__ import annotations


# --------------------------------------------------------------------------- #
# convert() tests
# --------------------------------------------------------------------------- #

def test_convert_known_map() -> None:
    """Known map key returns the correct Chinese translation."""
    from nonebot_plugin_apex_api_query.data import convert

    assert convert("Kings Canyon") == "诸王峡谷"


def test_convert_unknown_key_returns_original() -> None:
    """Key not in any translation table returns the original value unchanged."""
    from nonebot_plugin_apex_api_query.data import convert

    assert convert("not_exist") == "not_exist"


def test_convert_none_returns_none() -> None:
    """None is not in TRANSLATIONS, so convert() returns None as-is."""
    from nonebot_plugin_apex_api_query.data import convert

    assert convert(None) is None


def test_convert_empty_string_returns_empty_string() -> None:
    """Empty string is not in TRANSLATIONS, so it returns unchanged."""
    from nonebot_plugin_apex_api_query.data import convert

    assert convert("") == ""


def test_convert_int_one_returns_yes() -> None:
    """Integer 1 matches BOOLEAN_TRANSLATIONS key and returns '是'."""
    from nonebot_plugin_apex_api_query.data import convert

    assert convert(1) == "是"


def test_convert_int_zero_returns_no() -> None:
    """Integer 0 matches BOOLEAN_TRANSLATIONS key and returns '否'."""
    from nonebot_plugin_apex_api_query.data import convert

    assert convert(0) == "否"


# --------------------------------------------------------------------------- #
# Constants tests
# --------------------------------------------------------------------------- #

def test_valid_platforms() -> None:
    """VALID_PLATFORMS contains the four supported platform identifiers."""
    from nonebot_plugin_apex_api_query.data import VALID_PLATFORMS

    assert VALID_PLATFORMS == ["PC", "PS4", "X1", "SWITCH"]


def test_default_platform() -> None:
    """DEFAULT_PLATFORM is 'PC'."""
    from nonebot_plugin_apex_api_query.data import DEFAULT_PLATFORM

    assert DEFAULT_PLATFORM == "PC"


# --------------------------------------------------------------------------- #
# _to_int() tests
# --------------------------------------------------------------------------- #

def test_to_int_with_valid_int() -> None:
    """_to_int(42) returns 42."""
    from nonebot_plugin_apex_api_query import _to_int

    assert _to_int(42) == 42


def test_to_int_with_non_numeric_string_returns_default() -> None:
    """_to_int('abc') returns default 0."""
    from nonebot_plugin_apex_api_query import _to_int

    assert _to_int("abc") == 0


def test_to_int_with_none_returns_default() -> None:
    """_to_int(None) returns default 0."""
    from nonebot_plugin_apex_api_query import _to_int

    assert _to_int(None) == 0


def test_to_int_with_invalid_string_and_custom_default() -> None:
    """_to_int('abc', 99) returns custom default 99."""
    from nonebot_plugin_apex_api_query import _to_int

    assert _to_int("abc", 99) == 99


def test_to_int_with_float_truncates() -> None:
    """_to_int(3.14) truncates to 3."""
    from nonebot_plugin_apex_api_query import _to_int

    assert _to_int(3.14) == 3


# --------------------------------------------------------------------------- #
# _to_int_optional() tests
# --------------------------------------------------------------------------- #

def test_to_int_optional_with_valid_int() -> None:
    """_to_int_optional(42) returns 42."""
    from nonebot_plugin_apex_api_query import _to_int_optional

    assert _to_int_optional(42) == 42


def test_to_int_optional_with_none_returns_none() -> None:
    """_to_int_optional(None) returns None."""
    from nonebot_plugin_apex_api_query import _to_int_optional

    assert _to_int_optional(None) is None


def test_to_int_optional_with_non_numeric_string_returns_none() -> None:
    """_to_int_optional('abc') returns None."""
    from nonebot_plugin_apex_api_query import _to_int_optional

    assert _to_int_optional("abc") is None


def test_to_int_optional_with_empty_string_returns_none() -> None:
    """_to_int_optional('') returns None."""
    from nonebot_plugin_apex_api_query import _to_int_optional

    assert _to_int_optional("") is None

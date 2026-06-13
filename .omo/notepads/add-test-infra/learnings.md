# Learnings — add-test-infra

## 2025-06-14: conftest.py module-level import pitfall

**Problem**: Importing `from nonebot_plugin_apex_api_query.models import PlayerStats` at
module level in `conftest.py` triggers a cascade:
1. Python resolves `nonebot_plugin_apex_api_query` package → executes `__init__.py`
2. `__init__.py:7-8` calls `require("nonebot_plugin_alconna")` and `require("nonebot_plugin_orm")`
3. `nonebot_plugin_orm` calls `get_driver()` via `get_plugin_config()`
4. `get_driver()` raises `ValueError: NoneBot has not been initialized.`
5. pytest fails to load the conftest → entire test suite broken

**Root cause**: `pytest_configure` runs during config loading, but `nonebot.init()`
only happens later in the `_nonebot_init` fixture (session scope). Any import that
touches the plugin's `__init__.py` at module level will fail.

**Fix**: Use `from __future__ import annotations` + `TYPE_CHECKING` guard:
```python
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from nonebot_plugin_apex_api_query.models import PlayerStats
```
Since `from __future__ import annotations` makes all annotations lazy strings,
`PlayerStats` in function signatures is never evaluated at runtime. The import
is only needed for static type checkers.

**Rule**: NO plugin imports at module level in conftest.py. Ever. All
`nonebot_plugin_apex_api_query` imports must happen inside test functions
(after `_nonebot_init` fixture has completed).

## 2025-06-14: Additional dependency needed

- `nonebot-adapter-console` was not installed. Added via `poetry add --group dev nonebot-adapter-console`.
  Required for the `ConsoleAdapter` registration in `after_nonebot_init`.

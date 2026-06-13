# 实现 preview.py 的 --previous 对比功能

## TL;DR
解析 `--previous` 参数，用 `format_comparison` 对比当前数据，文字加变化标记，图片传 changes 参数。

## Context
`--previous "level=500,score=14500,rank=白金,div=1"` 已被正确解析为 `pos_args` 不受干扰，但解析后没有任何作用。需要实现和插件一致的对比逻辑。

## TODOs

- [x] 1. 在 scripts/preview.py 实现 --previous 对比

  **What to do**:
  1. 解析 `--previous` 字符串：
     ```python
     prev_str = None
     it = iter(sys.argv)
     for a in it:
         if a == "--previous":
             prev_str = next(it, None)
     ```
  2. 如果有 `prev_str`，解析成 dict：
     ```python
     prev_data = {}
     for kv in prev_str.split(","):
         k, v = kv.strip().split("=", 1)
         prev_data[k.strip()] = v.strip()
     ```
  3. 构造 `PlayerStatsData`：
     ```python
     from nonebot_plugin_apex_api_query.storage import PlayerStatsData, format_comparison
     previous = PlayerStatsData(
         level=int(prev_data.get("level", 0)),
         rank_score=int(prev_data.get("score", 0)),
         rank_name=prev_data.get("rank", ""),
         rank_div=int(prev_data["div"]) if "div" in prev_data else None,
     )
     current = PlayerStatsData(
         level=data.get("level", 0), rank_score=data.get("rank_score", 0),
         rank_name=data.get("rank_name", ""), rank_div=data.get("rank_div"),
     )
     ```
  4. 调用 `format_comparison(current, previous)` 得到变化字典
  5. 把变化拼到文字里（和插件 `__init__.py:112-120` 一样）
  6. 传给 `render_player_card(data, changes, score_diff)`

  **Must NOT do**:
  - 不访问数据库
  - 不修改现有 arg 解析逻辑

  **Recommended Agent Profile**:
  - **Category**: `quick` — 纯逻辑追加，30 行以内

  **QA Scenarios**:
  ```
  Scenario: --previous 显示变化
    Tool: Bash
    Steps:
      1. APEX_API_KEY="dummy" poetry run python scripts/preview.py player test --previous "level=100,score=5000,rank=黄金,div=2" --text
    Expected Result: 输出包含 (↑N) 或 (↓N) 之类的变化标记（API 返回 dummy 数据所以内容任意），但脚本不崩溃
    Evidence: .omo/evidence/preview-previous.txt
  ```

  **Commit**: YES
  - Message: `✨ feat: --previous 支持对比历史数据并显示变化标记`
  - Files: `scripts/preview.py`

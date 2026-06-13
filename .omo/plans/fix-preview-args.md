# 修复 preview.py --previous 被当作平台参数

## TL;DR
`--previous` 没被过滤，被当成平台传给 API。

## Context
用户执行 `python preview.py player hx1aoh --previous "..."` 时报 `Invalid platform`。

## TODOs

- [x] 1. 修复 scripts/preview.py 的 pos_args 过滤逻辑

  **What to do**:
  - 第 156 行 `pos_args` 过滤加上 `--previous` 及其值：
    ```python
    pos_args = [a for a in sys.argv[2:] if a not in ("--text", "--previous") and not (len(sys.argv) > 2 and sys.argv[sys.argv.index(a)-1] == "--previous")]
    ```
    或更简单的：收集所有不含 `--` 开头的参数。

  **Commit**: YES
  - Message: `🐛 fix: --previous 参数被误当作平台传给 API`
  - Files: `scripts/preview.py`

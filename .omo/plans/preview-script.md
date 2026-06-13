# 创建预览脚本

## TL;DR

> **Quick Summary**: 创建 `scripts/preview.py`，支持通过真实 API Key 运行 4 种查询（玩家/地图/服务器/顶猎），命令行指定输出图片路径和文本输出。
>
> **Deliverables**:
> - `scripts/preview.py`
>
> **Estimated Effort**: Quick
> **Parallel Execution**: NO - single task

---

## Context

### Original Request
用户想用真实 API Key 预览插件生成的图片和文字效果，不走 NoneBot 机器人。

## Work Objectives

### Core Objective
创建独立脚本，加载真实 API 数据并输出图片文件 + 文本到终端。

### Must Have
- 通过环境变量 `APEX_API_KEY` 读取真实 key
- 支持 4 种查询模式：player / map / server / predator
- player 模式接收玩家名 + 可选平台
- 图片输出为 PNG 文件
- 文本输出到 stdout

### Must NOT Have
- 不启动 NoneBot 机器人
- 不引入新依赖

---

## TODOs

- [x] 1. Create scripts/preview.py

  **What to do**:
  - 创建 `scripts/preview.py`
  - 使用 `argparse` 或 `sys.argv` 支持命令行：
    ```bash
    python scripts/preview.py player <玩家名> [平台]     # 默认 PC
    python scripts/preview.py map
    python scripts/preview.py server
    python scripts/preview.py predator
    ```
  - 从环境变量读取 `APEX_API_KEY`，缺则报错退出
  - 调用 `data_source` 获取数据 → 打印文本
  - 调用 `image` 渲染 → 保存为 `preview_<mode>.png`
  - 调用 `config.apex_only_text` 支持 `--text` 参数跳过渲染
  - `asyncio.run(main())` 驱动

  **Must NOT do**:
  - 不启动 NoneBot
  - 不需要数据库

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 单文件脚本，逻辑简单，调用已有模块

  **Acceptance Criteria**:
  - [ ] `python scripts/preview.py map` 输出地图轮换文字 + 生成 preview_map.png
  - [ ] `python scripts/preview.py player <玩家名>` 输出玩家数据文字 + 生成 preview_player.png
  - [ ] 缺 `APEX_API_KEY` 时报错退出（非崩溃）
  - [ ] `--text` 参数跳过图片渲染

  **QA Scenarios**:
  ```
  Scenario: 脚本语法正确，可 --help
    Tool: Bash
    Steps:
      1. python scripts/preview.py --help
    Expected Result: 显示用法，exit 0
    Evidence: .omo/evidence/preview-help.txt

  Scenario: 缺 key 时报错
    Tool: Bash
    Steps:
      1. APEX_API_KEY="" python scripts/preview.py map
    Expected Result: 输出错误信息，exit 非 0
    Evidence: .omo/evidence/preview-no-key.txt
  ```

  **Commit**: YES
  - Message: `🔧 chore: 添加预览脚本，支持真实 API Key 预览效果`
  - Files: `scripts/preview.py`

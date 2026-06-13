# 移除图片变化标记和 Data From 脚注

## TL;DR
1. scripts/preview.py：`render_player_card` 不传 changes/score_diff
2. image.py：player/map/predator 去掉 `_draw_footer`（仅 server 保留）

## TODOs

- [x] 1. scripts/preview.py：render_player_card 不传 changes
- [x] 2. image.py：去掉 player/map/predator 的 _draw_footer

**Commit**: `🎨 style: 移除图片变化标记和 Data From 脚注`

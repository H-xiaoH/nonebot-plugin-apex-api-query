import io
import logging
from contextlib import suppress
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
import numpy as np
from nonebot_plugin_localstore import get_plugin_data_dir
from PIL import Image, ImageDraw, ImageFont, ImageOps

from .data import convert

logger = logging.getLogger(__name__)

_SECONDS_PER_MINUTE = 60
_UTC_PLUS_8 = timezone(timedelta(hours=8))
_PRED_LOW_THRESHOLD = 15000
_CARD_BG = (24, 24, 24, 255)
_ACCENT = (218, 49, 52, 255)


def _text_size(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> tuple[int, int]:
    bb = draw.textbbox((0, 0), text, font=font)
    return int(bb[2] - bb[0]), int(bb[3] - bb[1])


def _draw_footer(
    draw: ImageDraw.ImageDraw, card_w: int, card_h: int, footer_h: int, offset: int = 4
) -> None:
    text = "Data from apexlegendsstatus.com"
    font = _load_font(18)
    w, _ = _text_size(draw, text, font)
    draw.text(
        ((card_w - w) // 2, card_h - footer_h + offset),
        text, font=font, fill=(110, 118, 130),
    )


def _draw_panel_bg(  # noqa: PLR0913
    draw: ImageDraw.ImageDraw,
    x: int, y: int, w: int, h: int,
    accent_color: tuple[int, int, int] | None = None,
    outline_color: tuple[int, int, int, int] = (60, 64, 72, 120),
) -> None:
    draw.rounded_rectangle(
        [x, y, x + w, y + h], radius=8, fill=(18, 20, 24, 255),
        outline=outline_color, width=1,
    )
    if accent_color is None:
        accent_color = _ACCENT[:3]
    draw.rectangle([x, y, x + 4, y + h], fill=accent_color)


CARD_W = 900
ACCENT_H = 4
SECTION_H = 200
NEXT_H = 60
GAP = 6
FOOTER_H = 36
CARD_H = 3 * (ACCENT_H + SECTION_H + NEXT_H) + 2 * GAP
RING_RADIUS = 56
RING_CENTER_X = 820
RING_CENTER_Y_OFFSET = 100

TEXT_WHITE = (255, 255, 255, 255)
TEXT_GRAY = (170, 178, 190, 255)
TEXT_SHADOW = (0, 0, 0, 160)
RING_GREEN = (47, 161, 108, 255)
RING_ORANGE = (194, 137, 24, 255)
RING_RED = (194, 20, 20, 255)
RING_BG = (0, 0, 0, 180)
RING_WARNING = 900
RING_ALERT = 300

MODE_LABELS: dict[str, str] = {
    "battle_royale": "大逃杀",
    "ranked": "排位赛",
    "ltm": "混录带",
}

FONT_PATHS = [
    str(Path(__file__).parent / "fonts" / "NotoSansSC-VariableFont_wght.ttf"),
]

_image_cache: dict[str, Image.Image] = {}
_font_cache: dict[tuple[int, int], ImageFont.FreeTypeFont | ImageFont.ImageFont] = {}
_map_cache_dir: Path | None = None


def _get_map_cache_dir() -> Path:
    global _map_cache_dir  # noqa: PLW0603
    if _map_cache_dir is None:
        _map_cache_dir = get_plugin_data_dir() / "map_images"
        _map_cache_dir.mkdir(parents=True, exist_ok=True)
    return _map_cache_dir


def _load_font(
    size: int, weight: int = 600
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """加载指定字号和字重的字体，支持变量字重缓存。"""
    cache_key = (size, weight)
    if cache_key in _font_cache:
        return _font_cache[cache_key]
    for path in FONT_PATHS:
        if Path(path).exists():
            f = ImageFont.truetype(path, size)
            with suppress(Exception):
                f.font.setvaraxes([weight])
            _font_cache[cache_key] = f
            return f
    _font_cache[cache_key] = ImageFont.load_default()
    return _font_cache[cache_key]


def _fmt_remaining(seconds: int) -> str:
    """格式化剩余秒数为 HH:MM:SS 或 MM:SS。"""
    if seconds <= 0:
        return "00:00"
    mins, secs = divmod(seconds, _SECONDS_PER_MINUTE)
    if mins >= _SECONDS_PER_MINUTE:
        hours, mins = divmod(mins, _SECONDS_PER_MINUTE)
        return f"{hours:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"


async def _download_image(url: str) -> Image.Image | None:
    """下载图片，优先磁盘缓存再 HTTP，失败返回 None。"""
    if url in _image_cache:
        return _image_cache[url]
    cache_key = url.rsplit("/", 1)[-1]
    disk_path = _get_map_cache_dir() / cache_key
    try:
        if disk_path.exists():
            img = Image.open(disk_path)
            if img.mode != "RGBA":
                img = img.convert("RGBA")
            img.load()
            _image_cache[url] = img
            return img
    except Exception:
        logger.exception(f"Failed to load cached map image: {disk_path}")
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            img = Image.open(io.BytesIO(resp.content))
            if img.mode != "RGBA":
                img = img.convert("RGBA")
            img.load()
            _image_cache[url] = img
            with suppress(OSError):
                img.save(disk_path, format="PNG")
            return img
    except httpx.HTTPStatusError as e:
        logger.debug(f"HTTP {e.response.status_code} for image: {url}")
        return None
    except Exception:
        logger.exception(f"Failed to download image: {url}")
        return None


def _cover_fit(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """缩放并居中裁剪图片以填充目标尺寸。"""
    return ImageOps.fit(img, (target_w, target_h), Image.Resampling.LANCZOS)


def _gradient_overlay(
    w: int, h: int, alpha1: float = 0.52, alpha2: float = 0.28
) -> Image.Image:
    """生成 135° 对角线渐变遮罩，alpha1(左上)→alpha2(右下)。"""
    xs = np.linspace(0, 1, w, dtype=np.float32)
    ys = np.linspace(0, 1, h, dtype=np.float32)
    t = (xs[None, :] + ys[:, None]) / 2
    alpha = alpha1 * (1 - t) + alpha2 * t
    overlay = np.zeros((h, w, 4), dtype=np.uint8)
    overlay[:, :, 3] = (alpha * 255).astype(np.uint8)
    return Image.fromarray(overlay, "RGBA")


def _draw_shadow_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: tuple[int, int, int],
) -> None:
    draw.text((xy[0] + 2, xy[1] + 2), text, font=font, fill=TEXT_SHADOW[:3])
    draw.text(xy, text, font=font, fill=fill)


def _draw_progress_ring(
    draw: ImageDraw.ImageDraw,
    cx: int, cy: int,
    remaining_secs: int, duration_secs: int,
) -> None:
    """绘制倒计时圆环（暗底 + 绿/橙/红进度弧 + 时间文字）。"""
    radius = RING_RADIUS
    stroke = 7
    bbox = [cx - radius, cy - radius, cx + radius, cy + radius]
    draw.pieslice(bbox, 0, 360, fill=RING_BG[:3])
    if duration_secs <= 0:
        return
    fraction = max(0, min(1, remaining_secs / duration_secs))
    if remaining_secs <= RING_ALERT:
        color = RING_RED
    elif remaining_secs <= RING_WARNING:
        color = RING_ORANGE
    else:
        color = RING_GREEN
    start = 90
    end = 90 + int(360 * fraction)
    arc_bbox = [
        bbox[0] + stroke, bbox[1] + stroke,
        bbox[2] - stroke + 1, bbox[3] - stroke + 1,
    ]
    draw.arc(arc_bbox, start=start, end=end, fill=color[:3], width=stroke)
    time_text = _fmt_remaining(remaining_secs)
    max_w = (radius - stroke) * 2 - 12
    for size in range(26, 10, -2):
        font = _load_font(size)
        if draw.textbbox((0, 0), time_text, font=font)[2] <= max_w:
            break
    else:
        font = _load_font(12)
    tw, th = _text_size(draw, time_text, font)
    ty = int(cy - th)
    _draw_shadow_text(draw, (cx - tw // 2, ty), time_text, font, (255, 255, 255))


def _parse_time_str(readable: str) -> str:
    """从 'YYYY-MM-DD HH:MM:SS' 格式字符串中提取 HH:MM。"""
    parts = readable.split(" ")
    return parts[1][:5] if len(parts) > 1 else readable


def _draw_mode_section(  # noqa: PLR0915
    canvas: Image.Image, y: int,
    mode_key: str, mode_data: dict[str, Any],
) -> int:
    """绘制一个地图模式段（当前 + 下次），返回新的 y 坐标。"""
    label = MODE_LABELS.get(mode_key, mode_key)
    current = mode_data.get("current", {})
    next_data = mode_data.get("next", {})

    draw = ImageDraw.Draw(canvas)
    draw.rectangle([0, y, CARD_W, y + ACCENT_H], fill=_ACCENT[:3])
    del draw
    y += ACCENT_H
    section_y = y

    asset_url = current.get("asset", "")
    map_img = _image_cache.get(asset_url) if asset_url else None
    if map_img:
        map_bg = _cover_fit(map_img, CARD_W, SECTION_H)
        canvas.paste(map_bg, (0, section_y), map_bg)
    overlay = _gradient_overlay(CARD_W, SECTION_H)
    canvas.paste(overlay, (0, section_y), overlay)

    draw = ImageDraw.Draw(canvas)
    _draw_shadow_text(draw, (24, section_y + 24), label, _load_font(22), (218, 49, 52))

    map_name = current.get("map", "未知")
    map_name_zh = convert(map_name)
    if mode_key == "ltm" and current.get("eventName"):
        map_name_zh = f"{map_name_zh} · {convert(current['eventName'])}"
    name_font = _load_font(48)
    _draw_shadow_text(
        draw, (24, section_y + 52), map_name_zh, name_font, (255, 255, 255),
    )

    start_str = current.get("readableDate_start", "")
    end_str = current.get("readableDate_end", "")
    if current.get("start") and current.get("end"):
        dt_start = datetime.fromtimestamp(int(current["start"]), tz=_UTC_PLUS_8)
        dt_end = datetime.fromtimestamp(int(current["end"]), tz=_UTC_PLUS_8)
        time_text = f"从 {dt_start:%H:%M} 到 {dt_end:%H:%M}"
    elif start_str and end_str:
        time_text = f"从 {_parse_time_str(start_str)} 到 {_parse_time_str(end_str)}"
    else:
        time_text = current.get("remainingTimer", "")
    time_font = _load_font(22)
    _draw_shadow_text(
        draw, (24, section_y + 126), time_text, time_font, (200, 208, 220),
    )

    remaining = int(current.get("remainingSecs", 0))
    duration = int(current.get("DurationInSecs", 0))
    _draw_progress_ring(
        draw, RING_CENTER_X, section_y + RING_CENTER_Y_OFFSET, remaining, duration,
    )

    del draw
    y += SECTION_H

    if next_data:
        draw = ImageDraw.Draw(canvas)
        draw.rectangle([0, y, CARD_W, y + NEXT_H], fill=(12, 14, 18, 255))
        next_map = next_data.get("map", "未知")
        next_map_zh = convert(next_map)
        if mode_key == "ltm" and next_data.get("eventName"):
            next_map_zh = f"{next_map_zh} · {convert(next_data['eventName'])}"
        next_text = f"▶  下次: {next_map_zh}"
        next_font = _load_font(24)
        _draw_shadow_text(draw, (24, y + 12), next_text, next_font, (255, 255, 255))

        next_start = next_data.get("readableDate_start", "")
        next_end = next_data.get("readableDate_end", "")
        if next_data.get("start") and next_data.get("end"):
            ns = datetime.fromtimestamp(int(next_data["start"]), tz=_UTC_PLUS_8)
            ne = datetime.fromtimestamp(int(next_data["end"]), tz=_UTC_PLUS_8)
            time_str = f"{ns:%H:%M}  -  {ne:%H:%M}"
        elif next_start and next_end:
            time_str = f"{_parse_time_str(next_start)}  -  {_parse_time_str(next_end)}"
        else:
            time_str = ""
        if time_str:
            time_small = _load_font(20)
            tw, _ = _text_size(draw, time_str, time_small)
            draw.text(
                (CARD_W - tw - 24, y + 12),
                time_str, font=time_small, fill=TEXT_GRAY[:3],
            )
        del draw

    y += NEXT_H + GAP
    return y


async def render_map_card(data: dict[str, Any]) -> bytes:
    """渲染三模式合并的地图轮换卡片，返回 PNG 字节。"""
    for mode_key in ("battle_royale", "ranked", "ltm"):
        mode_data = data.get(mode_key, {})
        for entry in (mode_data.get("current", {}), mode_data.get("next", {})):
            asset_url = entry.get("asset", "")
            if asset_url and asset_url not in _image_cache:
                await _download_image(asset_url)

    canvas = Image.new("RGBA", (CARD_W, CARD_H), _CARD_BG)
    draw: ImageDraw.ImageDraw = ImageDraw.Draw(canvas)

    y = 0
    for mode_key in ("battle_royale", "ranked", "ltm"):
        mode_data = data.get(mode_key, {})
        if not mode_data.get("current"):
            continue
        y = _draw_mode_section(canvas, y, mode_key, mode_data)

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    return buf.getvalue()


STATUS_COLORS: dict[str, tuple[int, int, int]] = {
    "UP": (47, 161, 108),
    "DOWN": (194, 20, 20),
    "SLOW": (194, 137, 24),
    "OVERLOADED": (194, 20, 20),
}

COLS = 2
COL_W = 310
ROW_H = 42
SEC_HEAD_H = 28
SEC_GAP = 4
SERV_CARD_W = 700
SERV_HEADER_H = 56
SERV_FOOTER_H = 26


def _draw_status_pill(
    draw: ImageDraw.ImageDraw, x: int, y: int, status: str,
) -> None:
    """绘制彩色圆角状态标签（绿/橙/红）。"""
    status_zh = convert(status)
    color = STATUS_COLORS.get(status, (110, 118, 130))
    font = _load_font(20)
    tw, th = _text_size(draw, status_zh, font)
    pw = tw + 24
    ph = th + 10
    pill_x = x
    pill_y = y + (ROW_H - ph) // 2 + 4
    draw.rounded_rectangle(
        [pill_x, pill_y, pill_x + pw, pill_y + ph],
        radius=6, fill=(*color, 40), outline=(*color, 180), width=1,
    )
    draw.text(
        (pill_x + 12, pill_y + (ph - th) // 2 - 6),
        status_zh, font=font, fill=color,
    )


def _compute_server_card_height(sections: list[dict[str, Any]]) -> int:
    """根据段落数据计算服务器状态卡片总高度。"""
    height = SERV_HEADER_H + SERV_FOOTER_H
    for sec in sections:
        rows = sec.get("rows", [])
        if not rows:
            continue
        num_rows = (len(rows) + COLS - 1) // COLS
        height += SEC_HEAD_H + num_rows * ROW_H + SEC_GAP
    return max(height, 200)


async def render_server_card(sections: list[dict[str, Any]]) -> bytes:
    """渲染服务器状态卡片，返回 PNG 字节。"""
    card_h = _compute_server_card_height(sections)
    canvas = Image.new("RGBA", (SERV_CARD_W, card_h), _CARD_BG)
    draw: ImageDraw.ImageDraw = ImageDraw.Draw(canvas)

    draw.text((24, 8), "Apex 服务器状态", font=_load_font(38), fill=(255, 255, 255))
    _draw_footer(draw, SERV_CARD_W, card_h, SERV_FOOTER_H, 0)

    y = SERV_HEADER_H
    for sec in sections:
        rows = sec.get("rows", [])
        if not rows:
            continue
        sec_name = sec["section_name"]
        draw.rectangle([0, y, 4, y + SEC_HEAD_H + 12], fill=_ACCENT[:3])
        draw.text((20, y + 4), sec_name, font=_load_font(28), fill=(255, 255, 255))
        y += SEC_HEAD_H
        for row_idx in range(0, len(rows), COLS):
            row_y = y
            for col in range(COLS):
                idx = row_idx + col
                if idx >= len(rows):
                    break
                item = rows[idx]
                col_x = 28 + col * COL_W
                draw.text(
                    (col_x, row_y + 11), item["name"],
                    font=_load_font(20), fill=(255, 255, 255),
                )
                sfont = _load_font(20)
                sw, _ = _text_size(draw, convert(item["status"]), sfont)
                pill_w = sw + 24
                pill_x = col_x + COL_W - pill_w - 12
                _draw_status_pill(draw, pill_x, row_y, str(item["status"]))
                rt = item.get("response_time", -1)
                if rt is not None and rt >= 0:
                    rt_text = f"{rt}ms"
                    rt_font = _load_font(18)
                    rtw, _ = _text_size(draw, rt_text, rt_font)
                    draw.text(
                        (pill_x - rtw - 8, row_y + 10),
                        rt_text, font=rt_font, fill=(140, 150, 165),
                    )
            y += ROW_H
        y += SEC_GAP

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    return buf.getvalue()


PRED_CARD_W = 350
PRED_CELL_W = 294
PRED_CELL_PAD = 20
PRED_ROW_H = 34
PRED_HEADER_H = 56
PRED_FOOTER_H = 26
PRED_SECTION_GAP = 14
PRED_GREEN = (47, 161, 108)


def _fmt_num(value: int) -> str:
    """格式化数字，0 或负数显示 '暂无'，否则千分位。"""
    return f"{value:,}" if value > 0 else "暂无"


def _draw_pred_cell(
    canvas: Image.Image, x: int, y: int, platform: dict[str, Any],
) -> None:
    """绘制猎杀者卡片中的单个平台面板。"""
    draw = ImageDraw.Draw(canvas)
    panel_w = PRED_CELL_W
    panel_h = PRED_ROW_H * 3 + PRED_CELL_PAD * 2
    _draw_panel_bg(draw, x, y, panel_w, panel_h)
    draw.text(
        (x + 18, y + 16), platform["name"], font=_load_font(28), fill=(255, 255, 255),
    )

    row_y = y + PRED_CELL_PAD + PRED_ROW_H
    rows = [
        ("猎杀底分", f"{_fmt_num(platform.get('val', 0))} RP"),
        ("大师人数", _fmt_num(platform.get("total_masters", 0))),
    ]
    label_font = _load_font(20)
    val_font = _load_font(22)
    for label, value in rows:
        draw.text(
            (x + 18, row_y + 3), label, font=label_font, fill=(140, 148, 160),
        )
        if label == "猎杀底分" and platform.get("val", 0) > 0:
            vc = (
                PRED_GREEN if platform["val"] <= _PRED_LOW_THRESHOLD
                else (255, 255, 255)
            )
        elif label == "大师人数" and platform.get("total_masters", 0) <= 0:
            vc = (140, 148, 160)
        else:
            vc = (255, 255, 255)
        vw, _ = _text_size(draw, value, val_font)
        draw.text((x + panel_w - vw - 18, row_y + 4), value, font=val_font, fill=vc)
        row_y += PRED_ROW_H


async def render_predator_card(data: dict[str, Any]) -> bytes:
    """渲染猎杀者排行卡片，返回 PNG 字节。"""
    platforms = [
        data.get("PC", {}), data.get("PS4", {}),
        data.get("X1", {}), data.get("SWITCH", {}),
    ]
    active = [p for p in platforms if p]
    cell_h = PRED_ROW_H * 3 + PRED_CELL_PAD * 2
    card_h = (
        PRED_HEADER_H + len(active) * (cell_h + PRED_SECTION_GAP)
    )

    canvas = Image.new("RGBA", (PRED_CARD_W, card_h), _CARD_BG)
    draw: ImageDraw.ImageDraw = ImageDraw.Draw(canvas)
    draw.text((24, 8), "Apex 猎杀者", font=_load_font(38), fill=(255, 255, 255))

    start_x = (PRED_CARD_W - PRED_CELL_W) // 2
    y = PRED_HEADER_H + 16
    for idx, platform in enumerate(active):
        cy = y + idx * (cell_h + PRED_SECTION_GAP)
        _draw_pred_cell(canvas, start_x, cy, platform)

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    return buf.getvalue()


PLAYER_CARD_W = 400
PLAYER_HEADER_H = 48
PLAYER_FOOTER_H = 26
PLAYER_PANEL_PAD = 18
PLAYER_ROW_H = 34
PLAYER_SECTION_GAP = 14

async def _load_and_paste(
    canvas: Image.Image, url: str, dest_x: int, dest_y: int, size: int,
) -> None:
    """下载图片并以指定尺寸贴到画布上。"""
    if not url:
        return
    if url not in _image_cache:
        await _download_image(url)
    img = _image_cache.get(url)
    if img:
        resized = img.resize((size, size), Image.Resampling.LANCZOS)
        canvas.paste(resized, (dest_x, dest_y), resized)


async def render_player_card(  # noqa: PLR0915
    player: dict[str, Any],
    changes: dict[str, str] | None = None,
    score_diff: int | None = None,
) -> bytes:
    """渲染玩家信息卡片，返回 PNG 字节。"""
    ban_active = player.get("ban_is_active")
    rank_h = 140
    data_rows = 7
    num_sections = 3 + (1 if ban_active else 0) + (1 if changes else 0)
    card_h = (
        110 + rank_h + 28 + data_rows * PLAYER_ROW_H + 24
        + (2 if changes else 0) * PLAYER_ROW_H + (20 if not changes else -28)
        + (2 * PLAYER_ROW_H + 20 if ban_active else 0)
        + num_sections * PLAYER_SECTION_GAP
    )

    canvas = Image.new("RGBA", (PLAYER_CARD_W, card_h), _CARD_BG)
    draw: ImageDraw.ImageDraw = ImageDraw.Draw(canvas)

    draw.text((24, 8), "Apex 玩家信息", font=_load_font(38), fill=(255, 255, 255))

    name = str(player.get("name", "未知"))
    draw.text(
        (28, PLAYER_HEADER_H + 10),
        name, font=_load_font(36), fill=(255, 255, 255),
    )
    sub_font = _load_font(20)
    uid = str(player.get("uid", ""))
    draw.text(
        (32, PLAYER_HEADER_H + 50), f"UID: {uid or '未知'}",
        font=sub_font, fill=(170, 178, 190),
    )
    plat = str(player.get("platform", ""))
    draw.text(
        (32, PLAYER_HEADER_H + 76),
        f"平台: {plat or '未知'}", font=sub_font, fill=(170, 178, 190),
    )

    y = PLAYER_HEADER_H + 110

    _draw_panel_bg(draw, 28, y, PLAYER_CARD_W - 56, rank_h + 28)
    rank_img_url = str(player.get("rank_img", ""))
    await _load_and_paste(canvas, rank_img_url, 44, y + 10, 150)

    rank_name = str(player.get("rank_name", ""))
    rank_div = player.get("rank_div")
    rank_disp = f"{rank_name} {rank_div}" if rank_div else rank_name
    score = _fmt_num(int(player.get("rank_score", 0)))
    score_text = f"{score} 分"
    rn_font = _load_font(30)
    sf_font = _load_font(22)
    rn_w, _ = _text_size(draw, rank_disp, rn_font)
    sf_w, _ = _text_size(draw, score_text, sf_font)
    right_x = PLAYER_CARD_W - 48
    draw.text((right_x - rn_w, y + 40), rank_disp, font=rn_font, fill=(255, 255, 255))
    draw.text((right_x - sf_w, y + 78), score_text, font=sf_font, fill=(47, 161, 108))
    if score_diff is not None and score_diff != 0:
        diff_sign = "+" if score_diff > 0 else ""
        diff_text = f"{diff_sign}{score_diff}"
        diff_color = (47, 161, 108) if score_diff > 0 else (194, 20, 20)
        diff_font = _load_font(22)
        dw, _ = _text_size(draw, diff_text, diff_font)
        draw.text(
            (right_x - dw, y + 78 + 26),
            diff_text, font=diff_font, fill=diff_color,
        )
    y += rank_h + 28 + PLAYER_SECTION_GAP

    level = player.get("level", 0)
    to_next = player.get("to_next_level_pct")
    lvl_text = f"{level}{f'  ({to_next}%)' if to_next is not None else ''}"
    legend = str(player.get("selected_legend", "")) or "未知"
    state = str(player.get("current_state", "")) or "离线"
    state_text = str(player.get("state_as_text", ""))
    lobby = str(player.get("lobby_state", "")) or "未知"
    is_online = str(player.get("is_online", "")) or "否"
    can_join = str(player.get("can_join", "")) or "否"
    party_full = str(player.get("party_full", "")) or "否"

    _draw_panel_bg(draw, 28, y, PLAYER_CARD_W - 56, data_rows * PLAYER_ROW_H + 24)
    data_items: list[tuple[str, str]] = [
        ("等级", lvl_text), ("传奇", legend), ("大厅", lobby),
        ("在线", is_online), ("可加入", can_join), ("群满员", party_full),
        ("状态", state_text or state),
    ]
    data_y = y + 20
    lfont = _load_font(20)
    vfont = _load_font(22)
    for label, value in data_items:
        draw.text((48, data_y), label, font=lfont, fill=(140, 148, 160))
        vw, _ = _text_size(draw, value, vfont)
        vx = PLAYER_CARD_W - 28 - vw - 18
        if label == "状态":
            vc = (
                (47, 161, 108)
                if state in ("在线", "在大厅", "比赛中") else (194, 20, 20)
            )
        elif label in ("在线", "可加入", "群满员"):
            vc = (47, 161, 108) if value == "是" else (140, 148, 160)
        else:
            vc = (255, 255, 255)
        draw.text((vx, data_y), value, font=vfont, fill=vc)
        data_y += PLAYER_ROW_H
    y += data_rows * PLAYER_ROW_H + 24 + PLAYER_SECTION_GAP

    if ban_active:
        ban_h = 2 * PLAYER_ROW_H + 20
        _draw_panel_bg(
            draw, 28, y, PLAYER_CARD_W - 56, ban_h,
            accent_color=(194, 20, 20), outline_color=(120, 30, 30, 120),
        )
        draw.text((48, y + 10), "封禁", font=_load_font(22), fill=(194, 130, 130))
        ban_secs = player.get("ban_remaining_secs", 0)
        ban_reason = str(player.get("ban_reason", ""))
        draw.text((48, y + 38), "状态: 是", font=vfont, fill=(255, 200, 200))
        ban_line2 = "剩余: " + (_fmt_remaining(int(ban_secs)) if ban_secs else "未知")
        if ban_reason:
            ban_line2 += f" · 原因: {ban_reason}"
        draw.text((48, y + 58), ban_line2, font=vfont, fill=(255, 200, 200))
        y += ban_h + PLAYER_SECTION_GAP


    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    return buf.getvalue()

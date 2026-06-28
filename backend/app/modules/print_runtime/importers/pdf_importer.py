"""UDPE PDF 模板导入器: PDF → schemaJson.

核心能力:
- 使用 PyMuPDF (fitz) 提取每页文本块及其位置信息
- 根据字号识别标题 (fontSize > 16)、正文 (10-16) 等结构
- 识别表格区域 (多行对齐文本块) → grid 组件
- 横线区域 → line 组件
- 空白区域 → spacer 组件
- 页间插入 pagebreak 组件

V1 限制:
- 不支持复杂 PDF 表单
- 不支持图片、矢量图形提取
- 不支持加密/受保护的 PDF
- 表格识别基于文本块对齐启发式, 复杂排版可能不准确
"""
import io
import logging
import math

import fitz
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ── 字号阈值 ──
TITLE_FONT_SIZE_THRESHOLD = 16.0  # 大于此值视为标题
TEXT_FONT_SIZE_MIN = 10.0         # 正文最小字号
SPACER_THRESHOLD = 20.0           # 垂直间距超过此值 (pt) 视为 spacer
LINE_THRESHOLD = 2.0              # 横线高度阈值 (pt)
TABLE_ROW_TOLERANCE = 3.0         # 行对齐容差 (pt)
TABLE_COL_TOLERANCE = 5.0         # 列对齐容差 (pt)


def _extract_page_blocks(page) -> list[dict]:
    """提取单页的文本块, 包含位置和字号信息.

    Returns:
        [{"text": "...", "x0": float, "y0": float, "x1": float, "y1": float,
          "fontSize": float, "fontNames": [...], "blockType": int}, ...]
    """
    blocks = []
    # 获取详细文本信息 (dict 格式)
    text_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)

    for block in text_dict.get("blocks", []):
        block_type = block.get("type", 0)

        if block_type == 1:
            # 图片块 — 跳过
            continue

        # 文本块
        lines = block.get("lines", [])
        if not lines:
            continue

        # 合并所有行的文本
        full_text_parts = []
        max_font_size = 0.0
        font_names = set()

        for line in lines:
            line_text_parts = []
            for span in line.get("spans", []):
                text = span.get("text", "")
                if text.strip():
                    line_text_parts.append(text)
                    # 跟踪最大字号
                    span_size = span.get("size", 0)
                    if span_size > max_font_size:
                        max_font_size = span_size
                    fname = span.get("font", "")
                    if fname:
                        font_names.add(fname)
            if line_text_parts:
                full_text_parts.append("".join(line_text_parts))

        full_text = "\n".join(full_text_parts).strip()
        if not full_text:
            continue

        # 位置信息
        bbox = block.get("bbox", (0, 0, 0, 0))

        blocks.append({
            "text": full_text,
            "x0": round(bbox[0], 2),
            "y0": round(bbox[1], 2),
            "x1": round(bbox[2], 2),
            "y1": round(bbox[3], 2),
            "fontSize": round(max_font_size, 1),
            "fontNames": sorted(font_names),
            "blockType": block_type,
        })

    return blocks


def _detect_lines(page) -> list[dict]:
    """检测页面中的横线 (画线路径).

    Returns:
        [{"y": float, "x0": float, "x1": float}, ...]
    """
    lines = []
    drawings = page.get_drawings()

    for path in drawings:
        for item in path.get("items", []):
            if item[0] == "l":  # 直线
                p1, p2 = item[1], item[2]
                y_diff = abs(p2.y - p1.y)
                x_diff = abs(p2.x - p1.x)
                # 水平线: y 差很小, x 差较大
                if y_diff < LINE_THRESHOLD and x_diff > 20:
                    y_mid = (p1.y + p2.y) / 2
                    x_start = min(p1.x, p2.x)
                    x_end = max(p1.x, p2.x)
                    lines.append({
                        "y": round(y_mid, 2),
                        "x0": round(x_start, 2),
                        "x1": round(x_end, 2),
                    })

    return lines


def _detect_tables(blocks: list[dict]) -> list[dict]:
    """启发式表格检测: 多行对齐的文本块 → grid 结构.

    策略:
    1. 按 y 坐标聚类为行 (容差 TABLE_ROW_TOLERANCE)
    2. 如果 >= 2 行, 每行 >= 2 列, 且列位置大致对齐 → 判定为表格
    3. 返回表格区域信息 (起止索引, 行列结构)

    Returns:
        [{"start_idx": int, "end_idx": int, "rows": [[block_idx, ...], ...],
          "col_positions": [float, ...]}, ...]
    """
    if len(blocks) < 2:
        return []

    # 按 y 中心聚类
    sorted_indices = sorted(range(len(blocks)), key=lambda i: (blocks[i]["y0"], blocks[i]["x0"]))

    # 将块按行分组
    rows: list[list[int]] = []
    current_row: list[int] = []
    current_y: Optional[float] = None

    for idx in sorted_indices:
        block = blocks[idx]
        y_center = (block["y0"] + block["y1"]) / 2

        if current_y is None or abs(y_center - current_y) > TABLE_ROW_TOLERANCE:
            if current_row:
                rows.append(current_row)
            current_row = [idx]
            current_y = y_center
        else:
            current_row.append(idx)

    if current_row:
        rows.append(current_row)

    # 筛选: >= 2 行, 每行 >= 2 个块
    multi_col_rows = [r for r in rows if len(r) >= 2]
    if len(multi_col_rows) < 2:
        return []

    # 尝试识别连续的表格区域
    tables = []
    consecutive: list[list[int]] = [multi_col_rows[0]]

    for i in range(1, len(multi_col_rows)):
        # 检查列数一致性 (允许 +-1 的容差)
        prev_len = len(consecutive[-1])
        curr_len = len(multi_col_rows[i])
        if abs(curr_len - prev_len) <= 1:
            consecutive.append(multi_col_rows[i])
        else:
            if len(consecutive) >= 2:
                tables.append(consecutive)
            consecutive = [multi_col_rows[i]]

    if len(consecutive) >= 2:
        tables.append(consecutive)

    return tables


def _build_spacer(height_pt: float) -> Optional[dict]:
    """构建 spacer 组件, 高度转为 mm."""
    height_mm = max(2, round(height_pt * 0.353))
    if height_mm < 4:
        return None
    return {"type": "spacer", "height": height_mm}


def _block_to_component(block: dict) -> dict:
    """单个文本块 → schemaJson 组件."""
    text = block["text"].strip()
    font_size = block["fontSize"]

    # 标题
    if font_size > TITLE_FONT_SIZE_THRESHOLD:
        align = "left"
        # 居中文本块: x0 接近页面中心时视为居中
        # (外部调用时可能注入 page_width 做更精确判断, 这里默认 left)
        return {
            "type": "title",
            "text": text,
            "fontSize": round(font_size),
            "align": align,
        }

    # 检查是否为粗体 (通过字体名判断)
    is_bold = any(
        "bold" in fn.lower() or "heavy" in fn.lower() or "black" in fn.lower()
        for fn in block.get("fontNames", [])
    )

    # 正文
    component = {
        "type": "text",
        "text": text,
        "fontSize": round(font_size) if font_size >= TEXT_FONT_SIZE_MIN else 11,
    }
    if is_bold:
        component["bold"] = True
    return component


def _blocks_to_table_component(row_indices: list[int], blocks: list[dict]) -> dict:
    """一组行索引 → grid 组件."""
    # 计算列数 (取最大列数)
    col_count = max(len(row) for row in row_indices)

    grid_rows = []
    for row_block_indices in row_indices:
        cells = []
        for idx in row_block_indices:
            block = blocks[idx]
            is_bold = any(
                "bold" in fn.lower() or "heavy" in fn.lower()
                for fn in block.get("fontNames", [])
            )
            cell = {
                "text": block["text"].strip(),
                "span": 1,
                "bold": is_bold,
            }
            if block["fontSize"]:
                cell["fontSize"] = round(block["fontSize"])
            cells.append(cell)

        # 补齐列 (span=1 空 cell)
        while len(cells) < col_count:
            cells.append({"text": "", "span": 1, "bold": False})

        grid_rows.append({"height": 14, "cells": cells})

    return {
        "type": "grid",
        "colCount": col_count,
        "border": True,
        "borderColor": "#000000",
        "borderWidth": 1,
        "rows": grid_rows,
    }


def _process_page_blocks(
    blocks: list[dict],
    line_info: list[dict],
    page_rect=None,
) -> list[dict]:
    """将一页的文本块和线条转换为 schemaJson body 组件列表."""
    components: list[dict] = []
    used_indices: set[int] = set()

    # 页面宽度 (用于判断居中)
    page_width = page_rect.width if page_rect else 595  # A4 默认

    # 表格检测
    table_groups = _detect_tables(blocks)
    for table_rows in table_groups:
        # 记录已使用的块索引
        for row_indices in table_rows:
            for idx in row_indices:
                used_indices.add(idx)
        grid = _blocks_to_table_component(table_rows, blocks)
        components.append(grid)

    # 按 y 坐标排序处理非表格块
    remaining = [
        (i, b) for i, b in enumerate(blocks) if i not in used_indices
    ]
    remaining.sort(key=lambda x: x[1]["y0"])

    last_y1 = 0.0
    for idx, block in remaining:
        # 检查间距 → spacer
        gap = block["y0"] - last_y1
        if gap > SPACER_THRESHOLD and last_y1 > 0:
            spacer = _build_spacer(gap)
            if spacer:
                components.append(spacer)

        # 检查是否有横线在此块之前
        for line in line_info:
            if last_y1 < line["y"] < block["y0"]:
                components.append({"type": "line"})

        # 居中检测: 文本块水平中心 vs 页面中心
        block_center = (block["x0"] + block["x1"]) / 2
        if abs(block_center - page_width / 2) < 30 and block["fontSize"] > TITLE_FONT_SIZE_THRESHOLD:
            # 大字号 + 居中 → 标题居中
            comp = _block_to_component(block)
            comp["align"] = "center"
        else:
            comp = _block_to_component(block)

        components.append(comp)
        last_y1 = block["y1"]

    # 页末横线
    for line in line_info:
        if line["y"] > last_y1:
            components.append({"type": "line"})

    return components


def _build_schema_json(pages_data: list[dict]) -> dict:
    """所有页面数据 → 完整 schemaJson."""
    body: list[dict] = []

    for i, page_data in enumerate(pages_data):
        body.extend(page_data["components"])

        # 页间插入 pagebreak (最后一页不需要)
        if i < len(pages_data) - 1:
            body.append({"type": "pagebreak"})

    return {"body": body}


def _parse_pdf_sync(file_bytes: bytes) -> dict:
    """同步解析 PDF (核心逻辑).

    Returns:
        {
            "pages": [{"pageNum": 1, "text": "页面文本", "blocks": [...]}],
            "schemaJson": {"body": [...]},
            "pageCount": 3,
            "summary": "解析结果摘要",
        }
    """
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages_data = []
    all_text_parts = []
    total_blocks = 0
    total_tables = 0

    for page_num in range(len(doc)):
        page = doc[page_num]
        page_idx = page_num + 1

        # 提取文本块
        blocks = _extract_page_blocks(page)
        total_blocks += len(blocks)

        # 提取页面纯文本
        page_text = page.get_text("text").strip()
        all_text_parts.append(page_text)

        # 检测横线
        line_info = _detect_lines(page)

        # 转换为组件
        components = _process_page_blocks(blocks, line_info, page.rect)

        # 统计表格数
        table_count = sum(1 for c in components if c.get("type") == "grid")
        total_tables += table_count

        pages_data.append({
            "pageNum": page_idx,
            "text": page_text,
            "blocks": [
                {
                    "text": b["text"],
                    "x0": b["x0"], "y0": b["y0"],
                    "x1": b["x1"], "y1": b["y1"],
                    "fontSize": b["fontSize"],
                    "fontNames": b["fontNames"],
                }
                for b in blocks
            ],
            "components": components,
        })

    doc.close()

    # 构建 schemaJson
    schema_json = _build_schema_json(pages_data)

    # 计算总组件数
    component_count = len(schema_json.get("body", []))

    # 构建摘要
    page_count = len(pages_data)
    summary_parts = [
        f"共 {page_count} 页",
        f"{total_blocks} 个文本块",
        f"{total_tables} 个表格",
        f"{component_count} 个组件",
    ]
    # 统计组件类型分布
    type_counts: dict[str, int] = {}
    for comp in schema_json.get("body", []):
        t = comp.get("type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1
    if type_counts:
        type_summary = ", ".join(f"{k}×{v}" for k, v in sorted(type_counts.items()))
        summary_parts.append(f"组件分布: {type_summary}")

    # 返回时去掉 components (只在内部使用), 保留 pages 的 text 和 blocks
    pages_out = []
    for pd in pages_data:
        pages_out.append({
            "pageNum": pd["pageNum"],
            "text": pd["text"],
            "blocks": pd["blocks"],
        })

    return {
        "pages": pages_out,
        "schemaJson": schema_json,
        "pageCount": page_count,
        "summary": " | ".join(summary_parts),
    }


def _apply_adjustments(schema_json: dict, adjustments: dict) -> dict:
    """根据用户调整参数修改 schemaJson.

    支持的调整:
    - forceTitleIndices: list[int]  → 指定 body 索引为 title 类型
    - forceTextIndices: list[int]   → 指定 body 索引为 text 类型
    - removeIndices: list[int]      → 移除指定索引的组件
    - mergeConsecutive: bool        → 合并连续的同类型 text 组件
    """
    if not adjustments:
        return schema_json

    body = list(schema_json.get("body", []))

    # 移除指定索引 (从后往前删, 避免索引偏移)
    remove_indices = set(adjustments.get("removeIndices", []))
    if remove_indices:
        body = [comp for i, comp in enumerate(body) if i not in remove_indices]

    # 强制设置为 title
    force_title = set(adjustments.get("forceTitleIndices", []))
    for idx in force_title:
        if 0 <= idx < len(body):
            comp = body[idx]
            if comp.get("type") in ("text", "title"):
                body[idx] = {
                    "type": "title",
                    "text": comp.get("text", ""),
                    "fontSize": comp.get("fontSize", 18),
                    "align": comp.get("align", "left"),
                }

    # 强制设置为 text
    force_text = set(adjustments.get("forceTextIndices", []))
    for idx in force_text:
        if 0 <= idx < len(body):
            comp = body[idx]
            if comp.get("type") in ("text", "title"):
                new_comp = {
                    "type": "text",
                    "text": comp.get("text", ""),
                    "fontSize": comp.get("fontSize", 11),
                }
                if comp.get("bold"):
                    new_comp["bold"] = True
                body[idx] = new_comp

    # 合并连续同类型 text
    if adjustments.get("mergeConsecutive"):
        merged: list[dict] = []
        for comp in body:
            if (
                merged
                and merged[-1].get("type") == "text"
                and comp.get("type") == "text"
                and merged[-1].get("fontSize") == comp.get("fontSize")
                and merged[-1].get("bold") == comp.get("bold")
            ):
                merged[-1]["text"] += "\n" + comp.get("text", "")
            else:
                merged.append(comp)
        body = merged

    schema_json["body"] = body
    return schema_json


async def preview_pdf_import(file_bytes: bytes) -> dict:
    """预览 PDF 导入结果.

    Args:
        file_bytes: PDF 文件的字节流

    Returns:
        {
            "pages": [{"pageNum": 1, "text": "页面文本", "blocks": [...]}],
            "schemaJson": {"body": [...]},
            "pageCount": 3,
            "summary": "解析结果摘要"
        }
    """
    if not file_bytes:
        raise ValueError("PDF 文件内容为空")

    # 基本校验: PDF 文件头
    if not file_bytes[:5].startswith(b"%PDF"):
        raise ValueError("不是有效的 PDF 文件")

    try:
        result = _parse_pdf_sync(file_bytes)
    except Exception as e:
        logger.exception("[UDPE] PDF 解析失败")
        raise RuntimeError(f"PDF 解析失败: {e}")

    logger.info(
        f"[UDPE] PDF 预览完成: {result['pageCount']} 页, "
        f"{len(result['schemaJson'].get('body', []))} 组件"
    )
    return result


async def confirm_pdf_import(file_bytes: bytes, adjustments: dict = None) -> dict:
    """确认导入 PDF (可带调整参数).

    Args:
        file_bytes: PDF 文件字节流
        adjustments: 可选的调整参数 (如指定哪些文本块是标题等)

    Returns:
        {
            "schemaJson": {"body": [...]},
            "pageCount": 3,
            "componentCount": 15
        }
    """
    if not file_bytes:
        raise ValueError("PDF 文件内容为空")

    if not file_bytes[:5].startswith(b"%PDF"):
        raise ValueError("不是有效的 PDF 文件")

    try:
        result = _parse_pdf_sync(file_bytes)
    except Exception as e:
        logger.exception("[UDPE] PDF 解析失败")
        raise RuntimeError(f"PDF 解析失败: {e}")

    # 应用调整
    schema_json = _apply_adjustments(result["schemaJson"], adjustments or {})
    component_count = len(schema_json.get("body", []))

    logger.info(
        f"[UDPE] PDF 确认导入: {result['pageCount']} 页, "
        f"{component_count} 组件"
        + (f", 调整参数: {adjustments}" if adjustments else "")
    )

    return {
        "schemaJson": schema_json,
        "pageCount": result["pageCount"],
        "componentCount": component_count,
    }

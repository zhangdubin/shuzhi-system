"""UDPE 模板多语言支持。

设计思路：
1. 模板组件的 text 字段可以是字符串或 locale 对象
2. 渲染时根据 locale 参数选择对应语言版本
3. 支持 fallback：指定语言 → 默认语言 → 原始 text

示例（组件 text 支持多语言）：
  {
    "type": "title",
    "text": {"zh": "合同摘要", "en": "Contract Summary", "ja": "契約概要"},
    "locale": "zh",  // 可选，组件级默认语言
    "fontSize": 20,
    "align": "center"
  }

  或使用 locales 字段（兼容旧格式）：
  {
    "type": "title",
    "text": "合同摘要",
    "locales": {
      "en": "Contract Summary",
      "ja": "契約概要"
    },
    "fontSize": 20
  }

数据绑定也支持多语言：
  {{ contract.name }} → 数据中的 contract.name 可以是 {"zh": "...", "en": "..."}
  渲染器会根据当前 locale 选择对应值
"""
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# 默认语言
DEFAULT_LOCALE = "zh"

# 支持的语言列表
SUPPORTED_LOCALES = ["zh", "en", "ja", "ko", "fr", "de", "es"]


def resolve_locale_text(
    text: Any,
    locale: str = DEFAULT_LOCALE,
    fallback_locale: str = DEFAULT_LOCALE,
) -> str:
    """解析多语言文本。

    Args:
        text: 可以是：
            - str: 直接返回
            - dict: locale → text 映射，如 {"zh": "你好", "en": "Hello"}
            - 其他: 转为字符串返回
        locale: 期望的语言
        fallback_locale: 兜底语言

    Returns:
        解析后的纯文本字符串
    """
    if text is None:
        return ""

    # 纯字符串直接返回
    if isinstance(text, str):
        return text

    # dict 格式：locale → text
    if isinstance(text, dict):
        # 优先精确匹配
        if locale in text:
            return str(text[locale])
        # 尝试语言前缀匹配（如 "zh-CN" 匹配 "zh"）
        lang = locale.split("-")[0].split("_")[0]
        if lang in text:
            return str(text[lang])
        # fallback
        if fallback_locale in text:
            return str(text[fallback_locale])
        # 取第一个可用值
        if text:
            return str(next(iter(text.values())))
        return ""

    return str(text)


def resolve_locale_value(
    value: Any,
    locale: str = DEFAULT_LOCALE,
    fallback_locale: str = DEFAULT_LOCALE,
) -> Any:
    """解析多语言数据值。

    与 resolve_locale_text 类似，但保留非字符串类型的原始值（数字、列表等）。
    仅当值是 dict 且包含 locale key 时才做语言选择。
    """
    if value is None:
        return None

    if not isinstance(value, dict):
        return value

    # 检查是否是 locale 映射（key 都是语言代码）
    if value and all(isinstance(k, str) and len(k) <= 5 for k in value.keys()):
        # 看起来像 locale 映射
        if locale in value:
            return value[locale]
        lang = locale.split("-")[0].split("_")[0]
        if lang in value:
            return value[lang]
        if fallback_locale in value:
            return value[fallback_locale]
        if value:
            return next(iter(value.values()))
        return None

    # 不是 locale 映射，原样返回
    return value


def apply_locale_to_component(comp: dict, locale: str) -> dict:
    """将多语言组件转换为单语言组件。

    处理两种格式：
    1. text 是 dict → 根据 locale 选择
    2. 有 locales 字段 → 合并到 text

    Args:
        comp: 组件 dict
        locale: 目标语言

    Returns:
        处理后的组件 dict（浅拷贝）
    """
    result = dict(comp)

    # 处理 text 字段
    text = result.get("text")
    if isinstance(text, dict):
        result["text"] = resolve_locale_text(text, locale)
    elif isinstance(text, str) and "locales" in comp:
        locales = comp["locales"]
        if isinstance(locales, dict) and locale in locales:
            result["text"] = locales[locale]
        elif isinstance(locales, dict):
            # 尝试语言前缀匹配
            lang = locale.split("-")[0].split("_")[0]
            if lang in locales:
                result["text"] = locales[lang]

    # 处理 label 字段（qrcode/barcode 的标签）
    label = result.get("label")
    if isinstance(label, dict):
        result["label"] = resolve_locale_text(label, locale)
    elif isinstance(label, str) and "labelLocales" in comp:
        label_locales = comp["labelLocales"]
        if isinstance(label_locales, dict) and locale in label_locales:
            result["label"] = label_locales[locale]

    # 处理 headers（table 组件的表头）
    headers = result.get("headers")
    if isinstance(headers, list):
        new_headers = []
        for h in headers:
            if isinstance(h, dict):
                new_headers.append(resolve_locale_text(h, locale))
            elif isinstance(h, str):
                # 检查是否有 headersLocales
                new_headers.append(h)
            else:
                new_headers.append(str(h))
        # 如果有 headersLocales，替换对应的表头
        if "headersLocales" in comp:
            hlocales = comp["headersLocales"]
            if isinstance(hlocales, dict) and locale in hlocales:
                locale_headers = hlocales[locale]
                if isinstance(locale_headers, list):
                    new_headers = locale_headers
        result["headers"] = new_headers

    # 处理 columns（table 组件的列定义）
    columns = result.get("columns")
    if isinstance(columns, list):
        new_columns = []
        for c in columns:
            if isinstance(c, dict):
                col = dict(c)
                label_val = col.get("label")
                if isinstance(label_val, dict):
                    col["label"] = resolve_locale_text(label_val, locale)
                new_columns.append(col)
            else:
                new_columns.append(c)
        result["columns"] = new_columns

    # 递归处理 grid 的 rows → cells
    rows = result.get("rows")
    if isinstance(rows, list):
        new_rows = []
        for row in rows:
            if isinstance(row, dict):
                new_row = dict(row)
                cells = new_row.get("cells", [])
                new_cells = []
                for cell in cells:
                    if isinstance(cell, dict):
                        new_cell = dict(cell)
                        cell_text = new_cell.get("text")
                        if isinstance(cell_text, dict):
                            new_cell["text"] = resolve_locale_text(cell_text, locale)
                        elif isinstance(cell_text, str) and "locales" in cell:
                            cell_locales = cell["locales"]
                            if isinstance(cell_locales, dict) and locale in cell_locales:
                                new_cell["text"] = cell_locales[locale]
                        # 递归处理 children
                        children = new_cell.get("children")
                        if isinstance(children, list):
                            new_cell["children"] = [
                                apply_locale_to_component(ch, locale) for ch in children
                            ]
                        new_cells.append(new_cell)
                    else:
                        new_cells.append(cell)
                new_row["cells"] = new_cells
                new_rows.append(new_row)
            else:
                new_rows.append(row)
        result["rows"] = new_rows

    return result


def apply_locale_to_schema(schema_json: dict, locale: str) -> dict:
    """将整个模板 schema 转换为指定语言版本。

    Args:
        schema_json: 模板的 schemaJson
        locale: 目标语言

    Returns:
        处理后的 schemaJson（浅拷贝）
    """
    if not locale or locale == DEFAULT_LOCALE:
        return schema_json

    result = dict(schema_json)
    body = result.get("body", [])
    new_body = [apply_locale_to_component(comp, locale) for comp in body]
    result["body"] = new_body
    return result

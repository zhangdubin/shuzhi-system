"""
UDPE 多语言国际化测试

覆盖:
- resolve_locale_text: 文本解析
- resolve_locale_value: 数据值解析
- apply_locale_to_component: 组件语言切换
- apply_locale_to_schema: 整个 schema 语言切换
"""
import pytest
from app.modules.print_runtime.i18n import (
    resolve_locale_text,
    resolve_locale_value,
    apply_locale_to_component,
    apply_locale_to_schema,
    DEFAULT_LOCALE,
)


class TestResolveLocaleText:
    """resolve_locale_text 测试"""

    def test_plain_string(self):
        assert resolve_locale_text("hello") == "hello"

    def test_dict_exact_match(self):
        d = {"zh": "你好", "en": "Hello", "ja": "こんにちは"}
        assert resolve_locale_text(d, locale="en") == "Hello"
        assert resolve_locale_text(d, locale="zh") == "你好"
        assert resolve_locale_text(d, locale="ja") == "こんにちは"

    def test_dict_language_prefix(self):
        d = {"zh": "你好", "en": "Hello"}
        # zh-CN 应匹配 zh
        assert resolve_locale_text(d, locale="zh-CN") == "你好"
        assert resolve_locale_text(d, locale="en-US") == "Hello"

    def test_dict_fallback(self):
        d = {"zh": "你好", "en": "Hello"}
        # 请求 fr 不存在，fallback 到 zh
        assert resolve_locale_text(d, locale="fr", fallback_locale="zh") == "你好"

    def test_dict_first_value(self):
        d = {"zh": "你好"}
        # 请求 en 不存在，fallback 也不存在，取第一个值
        assert resolve_locale_text(d, locale="fr", fallback_locale="de") == "你好"

    def test_none_value(self):
        assert resolve_locale_text(None) == ""

    def test_number_value(self):
        assert resolve_locale_text(42) == "42"


class TestResolveLocaleValue:
    """resolve_locale_value 测试"""

    def test_non_dict_passthrough(self):
        assert resolve_locale_value(42) == 42
        assert resolve_locale_value("hello") == "hello"
        assert resolve_locale_value([1, 2]) == [1, 2]

    def test_dict_locale_mapping(self):
        d = {"zh": 100, "en": 200}
        assert resolve_locale_value(d, locale="zh") == 100
        assert resolve_locale_value(d, locale="en") == 200

    def test_non_locale_dict_passthrough(self):
        # 普通对象（key 不是语言代码）应原样返回
        d = {"name": "test", "amount": 100}
        assert resolve_locale_value(d) == d

    def test_none_value(self):
        assert resolve_locale_value(None) is None


class TestApplyLocaleToComponent:
    """apply_locale_to_component 测试"""

    def test_title_with_dict_text(self):
        comp = {
            "type": "title",
            "text": {"zh": "合同摘要", "en": "Contract Summary"},
            "fontSize": 20,
            "align": "center",
        }
        result = apply_locale_to_component(comp, "en")
        assert result["text"] == "Contract Summary"
        assert result["fontSize"] == 20  # 其他字段保留

    def test_title_with_locales_field(self):
        comp = {
            "type": "title",
            "text": "合同摘要",
            "locales": {"en": "Contract Summary", "ja": "契約概要"},
            "fontSize": 20,
        }
        result = apply_locale_to_component(comp, "ja")
        assert result["text"] == "契約概要"

    def test_text_component(self):
        comp = {
            "type": "text",
            "text": {"zh": "打印时间", "en": "Print Time"},
            "fontSize": 10,
        }
        result = apply_locale_to_component(comp, "en")
        assert result["text"] == "Print Time"

    def test_grid_cells_locale(self):
        comp = {
            "type": "grid",
            "colCount": 2,
            "rows": [{
                "height": 14,
                "cells": [
                    {"text": {"zh": "甲方", "en": "Party A"}, "span": 1},
                    {"text": {"zh": "乙方", "en": "Party B"}, "span": 1},
                ]
            }]
        }
        result = apply_locale_to_component(comp, "en")
        cells = result["rows"][0]["cells"]
        assert cells[0]["text"] == "Party A"
        assert cells[1]["text"] == "Party B"

    def test_plain_text_unchanged(self):
        comp = {"type": "text", "text": "固定文本", "fontSize": 10}
        result = apply_locale_to_component(comp, "en")
        assert result["text"] == "固定文本"  # 无 locales，保持原样

    def test_zh_locale_noop(self):
        comp = {
            "type": "title",
            "text": {"zh": "你好", "en": "Hello"},
            "fontSize": 20,
        }
        # zh 是默认语言，直接取 zh 值
        result = apply_locale_to_component(comp, "zh")
        assert result["text"] == "你好"


class TestApplyLocaleToSchema:
    """apply_locale_to_schema 测试"""

    def test_full_schema_locale(self):
        schema = {
            "body": [
                {"type": "title", "text": {"zh": "合同", "en": "Contract"}, "fontSize": 20},
                {"type": "text", "text": {"zh": "编号", "en": "Code"}, "fontSize": 10},
                {"type": "spacer", "height": 6},
            ]
        }
        result = apply_locale_to_schema(schema, "en")
        assert result["body"][0]["text"] == "Contract"
        assert result["body"][1]["text"] == "Code"
        assert result["body"][2]["height"] == 6  # spacer 不受影响

    def test_zh_locale_returns_original(self):
        schema = {"body": [{"type": "text", "text": "你好"}]}
        result = apply_locale_to_schema(schema, "zh")
        assert result is schema  # zh 直接返回原对象

    def test_empty_locale_returns_original(self):
        schema = {"body": []}
        result = apply_locale_to_schema(schema, "")
        assert result is schema

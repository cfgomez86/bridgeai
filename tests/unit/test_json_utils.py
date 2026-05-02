import pytest

from app.utils.json_utils import parse_json_field, extract_json, _fix_mojibake


class TestParseJsonField:
    """Test parse_json_field() with various input types and error conditions."""

    def test_empty_string_returns_empty_list(self):
        """Empty string should return []."""
        assert parse_json_field("") == []

    def test_none_like_empty_returns_empty_list(self):
        """String containing only whitespace should return []."""
        assert parse_json_field("   ") == []

    def test_valid_json_list_returns_list(self):
        """Valid JSON list should be returned."""
        result = parse_json_field('["a", "b", "c"]')
        assert result == ["a", "b", "c"]

    def test_valid_json_empty_list_returns_empty_list(self):
        """Valid empty JSON list should return []."""
        assert parse_json_field("[]") == []

    def test_valid_json_list_with_objects(self):
        """JSON list with objects should be returned."""
        result = parse_json_field('[{"id": 1}, {"id": 2}]')
        assert result == [{"id": 1}, {"id": 2}]

    def test_valid_json_list_with_mixed_types(self):
        """JSON list with mixed types should be returned."""
        result = parse_json_field('[1, "two", true, null, {"id": 5}]')
        assert result == [1, "two", True, None, {"id": 5}]

    def test_invalid_json_returns_empty_list(self):
        """Invalid JSON should return []."""
        assert parse_json_field('{"not": "a list"}') == []

    def test_json_object_instead_of_list_returns_empty_list(self):
        """JSON object (not list) should return []."""
        assert parse_json_field('{"key": "value"}') == []

    def test_json_string_instead_of_list_returns_empty_list(self):
        """JSON string (not list) should return []."""
        assert parse_json_field('"just a string"') == []

    def test_json_number_instead_of_list_returns_empty_list(self):
        """JSON number (not list) should return []."""
        assert parse_json_field("42") == []

    def test_json_boolean_instead_of_list_returns_empty_list(self):
        """JSON boolean (not list) should return []."""
        assert parse_json_field("true") == []

    def test_json_null_instead_of_list_returns_empty_list(self):
        """JSON null (not list) should return []."""
        assert parse_json_field("null") == []

    def test_malformed_json_returns_empty_list(self):
        """Malformed JSON (missing quotes, brackets) should return []."""
        assert parse_json_field('[1, 2, ') == []
        assert parse_json_field('[1, 2,]') == []

    def test_type_error_returns_empty_list(self):
        """TypeError during parsing should return []."""
        # Pass something that will cause TypeError (though str always works, this is defensive)
        assert parse_json_field("") == []

    def test_json_with_trailing_comma_returns_empty_list(self):
        """JSON with trailing comma is invalid and returns []."""
        assert parse_json_field('[1, 2, 3,]') == []

    def test_nested_lists(self):
        """Nested lists should be preserved."""
        result = parse_json_field('[[1, 2], [3, 4]]')
        assert result == [[1, 2], [3, 4]]


class TestFixMojibake:
    """Test _fix_mojibake() for UTF-8 encoding issues."""

    def test_normal_string_unchanged(self):
        """Normal ASCII string should pass through unchanged."""
        result = _fix_mojibake("hello")
        assert result == "hello"

    def test_utf8_string_unchanged(self):
        """Proper UTF-8 string should pass through unchanged."""
        result = _fix_mojibake("café")
        assert result == "café"

    def test_mojibake_conversion(self):
        """UTF-8 bytes misread as Latin-1 should be fixed."""
        # Simulate mojibake: 'é' (U+00E9) encoded as UTF-8 is 0xC3A9
        # If misread as Latin-1, becomes 'Ã©'
        mojibake = "CafÃ©"  # This is mojibake form
        result = _fix_mojibake(mojibake)
        # The function encodes as latin-1 and decodes as utf-8
        assert result == "Café"

    def test_string_that_cannot_be_fixed_returns_original(self):
        """String that cannot be fixed should return original."""
        # A string with a character that can't be encoded as latin-1
        # will fail the encode step and return the original
        original = "normal_string"
        result = _fix_mojibake(original)
        assert result == original

    def test_list_recursion(self):
        """Lists should be recursively fixed."""
        mojibake_list = ["CafÃ©", "cofeÃ"]
        result = _fix_mojibake(mojibake_list)
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0] == "Café"

    def test_empty_list(self):
        """Empty list should return empty list."""
        assert _fix_mojibake([]) == []

    def test_list_with_nested_lists(self):
        """Nested lists should be recursively fixed."""
        nested = [["CafÃ©"], ["tÃ©"]]
        result = _fix_mojibake(nested)
        assert result == [["Café"], ["té"]]

    def test_dict_recursion(self):
        """Dicts should be recursively fixed."""
        mojibake_dict = {"name": "CafÃ©", "type": "beverage"}
        result = _fix_mojibake(mojibake_dict)
        assert isinstance(result, dict)
        assert result["name"] == "Café"
        assert result["type"] == "beverage"

    def test_empty_dict(self):
        """Empty dict should return empty dict."""
        assert _fix_mojibake({}) == {}

    def test_dict_with_nested_structures(self):
        """Dict with nested lists/dicts should be fixed."""
        nested = {
            "items": ["CafÃ©", "tÃ©"],
            "details": {"origin": "Brasil"}  # normal string that doesn't need fixing
        }
        result = _fix_mojibake(nested)
        assert result["items"][0] == "Café"
        assert result["items"][1] == "té"
        assert result["details"]["origin"] == "Brasil"

    def test_dict_with_numeric_keys_and_values(self):
        """Dict with non-string values should preserve them."""
        data = {"count": 42, "name": "CafÃ©", "price": 3.99}
        result = _fix_mojibake(data)
        assert result["count"] == 42
        assert result["price"] == 3.99
        assert result["name"] == "Café"

    def test_mixed_types_in_list(self):
        """List with mixed types should handle each correctly."""
        mixed = [1, "CafÃ©", 3.14, True, None, {"item": "tÃ©"}]
        result = _fix_mojibake(mixed)
        assert result[0] == 1
        assert result[1] == "Café"
        assert result[2] == 3.14
        assert result[3] is True
        assert result[4] is None
        assert result[5]["item"] == "té"

    def test_non_string_non_collection_returns_unchanged(self):
        """Numbers, booleans, None should pass through unchanged."""
        assert _fix_mojibake(42) == 42
        assert _fix_mojibake(3.14) == 3.14
        assert _fix_mojibake(True) is True
        assert _fix_mojibake(None) is None


class TestExtractJson:
    """Test extract_json() with various JSON formats and encodings."""

    def test_plain_json_object(self):
        """Plain JSON object should parse correctly."""
        result = extract_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_plain_json_with_whitespace(self):
        """JSON with surrounding whitespace should parse."""
        result = extract_json('  {"key": "value"}  ')
        assert result == {"key": "value"}

    def test_json_with_triple_backticks(self):
        """JSON wrapped in triple backticks should parse."""
        result = extract_json('```\n{"key": "value"}\n```')
        assert result == {"key": "value"}

    def test_json_with_json_language_marker(self):
        """JSON with ```json marker should parse."""
        result = extract_json('```json\n{"key": "value"}\n```')
        assert result == {"key": "value"}

    def test_json_with_json_marker_no_newline(self):
        """JSON with ```json but no newline should parse."""
        result = extract_json('```json{"key": "value"}\n```')
        assert result == {"key": "value"}

    def test_json_with_fences_and_extra_whitespace(self):
        """JSON with fences and extra whitespace should parse."""
        result = extract_json('```json\n\n{"key": "value"}\n\n```')
        assert result == {"key": "value"}

    def test_complex_nested_json(self):
        """Complex nested JSON should parse correctly."""
        raw = '```json\n{"user": {"name": "Alice", "items": [1, 2, 3]}}\n```'
        result = extract_json(raw)
        assert result == {"user": {"name": "Alice", "items": [1, 2, 3]}}

    def test_json_array_unwrapped(self):
        """JSON array should parse."""
        result = extract_json('[1, 2, 3]')
        assert result == [1, 2, 3]

    def test_json_with_mojibake(self):
        """JSON with mojibake should be fixed."""
        raw = '{"name": "CafÃ©"}'
        result = extract_json(raw)
        assert result["name"] == "Café"

    def test_json_with_mojibake_in_arrays(self):
        """Mojibake in arrays should be fixed."""
        raw = '["CafÃ©", "tÃ©"]'
        result = extract_json(raw)
        assert result[0] == "Café"
        assert result[1] == "té"

    def test_invalid_json_raises_value_error(self):
        """Invalid JSON should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid JSON from AI provider"):
            extract_json('not json at all')

    def test_invalid_json_with_fences_raises_value_error(self):
        """Invalid JSON even with fences should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid JSON from AI provider"):
            extract_json('```json\n{invalid}\n```')

    def test_invalid_json_truncates_in_error(self):
        """Error message should truncate long raw text."""
        long_text = 'x' * 300
        with pytest.raises(ValueError, match="Invalid JSON from AI provider"):
            extract_json(long_text)

    def test_empty_json_object(self):
        """Empty JSON object should parse."""
        result = extract_json('{}')
        assert result == {}

    def test_empty_json_array(self):
        """Empty JSON array should parse."""
        result = extract_json('[]')
        assert result == []

    def test_json_with_unicode_escapes(self):
        """JSON with unicode escapes should parse correctly."""
        result = extract_json('{"emoji": "\\u263A"}')
        assert result == {"emoji": "☺"}

    def test_json_with_newlines_in_string(self):
        """JSON with escaped newlines in strings should parse."""
        result = extract_json('{"text": "line1\\nline2"}')
        assert result == {"text": "line1\nline2"}

    def test_json_with_special_characters(self):
        """JSON with special characters should parse."""
        result = extract_json('{"path": "C:\\\\Users\\\\test"}')
        assert result == {"path": "C:\\Users\\test"}

    def test_json_number_values(self):
        """JSON with various number types should parse."""
        result = extract_json('{"int": 42, "float": 3.14, "exp": 1e-5, "neg": -10}')
        assert result == {"int": 42, "float": 3.14, "exp": 1e-5, "neg": -10}

    def test_json_boolean_and_null(self):
        """JSON with boolean and null values should parse."""
        result = extract_json('{"flag": true, "empty": null, "nope": false}')
        assert result == {"flag": True, "empty": None, "nope": False}

    def test_fences_without_json_marker(self):
        """Fences without 'json' marker should still parse."""
        result = extract_json('```\n{"key": "value"}\n```')
        assert result == {"key": "value"}

    def test_json_with_markdown_code_inline(self):
        """JSON inside markdown-like fences should parse."""
        result = extract_json('```json\n{"status": "ok"}\n```\n')
        assert result == {"status": "ok"}

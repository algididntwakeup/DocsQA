"""Tests for stable OpenAPI schema normalization."""

from typing import Any

from scripts.export_openapi import PYDANTIC_DECIMAL_PATTERN, normalize_openapi_schema


def test_normalize_openapi_removes_only_generated_decimal_patterns() -> None:
    decimal_fields = ("computed_value", "stated_value", "delta", "tolerance")
    schema: dict[str, Any] = {
        "components": {
            "schemas": {
                "TableMathEvidence": {
                    "properties": {
                        field_name: {"type": "string", "pattern": PYDANTIC_DECIMAL_PATTERN}
                        for field_name in decimal_fields
                    }
                },
                "OtherSchema": {
                    "properties": {
                        "code": {"type": "string", "pattern": PYDANTIC_DECIMAL_PATTERN}
                    }
                },
            }
        }
    }

    normalize_openapi_schema(schema)

    table_math_properties = schema["components"]["schemas"]["TableMathEvidence"]["properties"]
    assert all("pattern" not in table_math_properties[field] for field in decimal_fields)
    unrelated_properties = schema["components"]["schemas"]["OtherSchema"]["properties"]
    assert unrelated_properties["code"]["pattern"] == PYDANTIC_DECIMAL_PATTERN

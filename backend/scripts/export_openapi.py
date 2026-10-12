"""Export the deterministic OpenAPI contract consumed by frontend tooling."""

import json
import sys
from pathlib import Path
from typing import Any

backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from main import app  # noqa: E402

PYDANTIC_DECIMAL_PATTERN = r"^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$"
TABLE_MATH_DECIMAL_FIELDS = ("computed_value", "stated_value", "delta", "tolerance")


def normalize_openapi_schema(schema: dict[str, Any]) -> None:
    """Remove Pydantic's version-specific default Decimal regex from the contract."""
    components = schema.get("components")
    if not isinstance(components, dict):
        return

    schemas = components.get("schemas")
    if not isinstance(schemas, dict):
        return

    table_math = schemas.get("TableMathEvidence")
    if not isinstance(table_math, dict):
        return

    properties = table_math.get("properties")
    if not isinstance(properties, dict):
        return

    for field_name in TABLE_MATH_DECIMAL_FIELDS:
        field_schema = properties.get(field_name)
        if (
            isinstance(field_schema, dict)
            and field_schema.get("pattern") == PYDANTIC_DECIMAL_PATTERN
        ):
            field_schema.pop("pattern")


def export_openapi() -> Path:
    """Write the current OpenAPI schema beside the backend application."""

    output_path = Path(__file__).resolve().parents[1] / "openapi.json"
    schema = app.openapi()
    normalize_openapi_schema(schema)
    output_path.write_text(
        json.dumps(schema, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return output_path


if __name__ == "__main__":
    print(export_openapi())

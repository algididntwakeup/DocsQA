"""Export the deterministic OpenAPI contract consumed by frontend tooling."""

import json
from pathlib import Path

from main import app


def export_openapi() -> Path:
    """Write the current OpenAPI schema beside the backend application."""

    output_path = Path(__file__).resolve().parents[1] / "openapi.json"
    output_path.write_text(
        json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path


if __name__ == "__main__":
    print(export_openapi())

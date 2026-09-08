"""Export the deterministic OpenAPI contract consumed by frontend tooling."""

import json
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from main import app  # noqa: E402


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

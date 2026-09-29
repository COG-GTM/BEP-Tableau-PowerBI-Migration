from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from jsonschema import RefResolver, ValidationError, validators


_SCHEMA_ROOT = Path(__file__).with_name("schemas")
_SCHEMA_URL_PREFIX = "https://developer.microsoft.com/json-schemas/"


@lru_cache(maxsize=1)
def _schema_store() -> dict[str, object]:
    store: dict[str, object] = {}
    for path in _SCHEMA_ROOT.rglob("*.json"):
        schema: object = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(schema, dict):
            continue
        schema_id = schema.get("$id")
        if isinstance(schema_id, str):
            store[schema_id] = schema
        relative = path.relative_to(_SCHEMA_ROOT).as_posix()
        if relative.startswith("fabric/"):
            store[f"{_SCHEMA_URL_PREFIX}{relative}"] = schema
    return store


def validate_json_documents(root: Path) -> list[Path]:
    store = _schema_store()
    validated: list[Path] = []
    candidates = sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and (path.suffix.casefold() == ".json" or path.name == ".platform")
    )
    for path in candidates:
        document: object = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(document, dict) or "$schema" not in document:
            continue
        schema_uri = document["$schema"]
        if not isinstance(schema_uri, str):
            raise ValueError(f"{path} has a non-string $schema value")
        schema = store.get(schema_uri)
        if not isinstance(schema, dict):
            raise ValueError(f"No vendored JSON schema found for {schema_uri}")
        validator_type = validators.validator_for(schema)
        resolver = RefResolver.from_schema(schema, store=store)
        try:
            validator_type(schema, resolver=resolver).validate(document)
        except ValidationError as error:
            raise ValueError(
                f"{path} does not satisfy {schema_uri}: {error.message}"
            ) from error
        except Exception as error:
            raise ValueError(
                f"Unable to resolve schema references for {path} ({schema_uri}): {error}"
            ) from error
        validated.append(path)
    return validated

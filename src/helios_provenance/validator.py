"""Thin :class:`jsonschema.Draft202012Validator` wrapper and CLI entry point.

The bundled JSON Schema lives at
``helios_provenance/_schema/helios-provenance-v0.1.json`` (shipped in the
wheel) and the source-tree copy is at ``schema/helios-provenance-v0.1.json``.

CLI:

.. code-block:: shell

    python -m helios_provenance.validator path/to/record.json [more.json ...]
    # or, after `pip install`:
    helios-provenance-validate path/to/record.json

Returns exit code 0 if every input file validates against the schema, 1
otherwise. A short per-file message is logged for human consumption.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections.abc import Mapping
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

logger = logging.getLogger(__name__)

SCHEMA_PATH = "helios_provenance/_schema/helios-provenance-v0.1.json"
"""Importable-resource path to the bundled JSON Schema."""


@lru_cache(maxsize=1)
def load_schema() -> dict[str, Any]:
    """Load and cache the bundled HELIOS provenance JSON Schema."""

    schema_file = resources.files("helios_provenance") / "_schema" / "helios-provenance-v0.1.json"
    raw = schema_file.read_text(encoding="utf-8")
    schema: dict[str, Any] = json.loads(raw)
    return schema


class HeliosProvenanceValidator:
    """Validate dicts / files against the HELIOS provenance schema.

    Example:
        >>> v = HeliosProvenanceValidator()
        >>> v.is_valid({"record_type": "HeliosDatasetRecord", ...})  # doctest: +SKIP
        True
    """

    def __init__(self, schema: Mapping[str, Any] | None = None) -> None:
        if schema is None:
            schema = load_schema()
        Draft202012Validator.check_schema(schema)
        self._validator = Draft202012Validator(dict(schema))

    @property
    def schema(self) -> Mapping[str, Any]:
        """Return the underlying JSON Schema dict."""

        return self._validator.schema  # type: ignore[no-any-return]

    def errors(self, instance: Mapping[str, Any]) -> list[ValidationError]:
        """Return all validation errors as a list (empty == valid)."""

        return sorted(self._validator.iter_errors(instance), key=lambda e: list(e.absolute_path))

    def is_valid(self, instance: Mapping[str, Any]) -> bool:
        """Return ``True`` iff ``instance`` validates."""

        return not self.errors(instance)

    def validate(self, instance: Mapping[str, Any]) -> None:
        """Raise the first :class:`jsonschema.ValidationError` if ``instance`` is invalid."""

        errs = self.errors(instance)
        if errs:
            raise errs[0]

    def validate_file(self, path: str | Path) -> list[ValidationError]:
        """Validate the JSON document at ``path``. Returns the error list."""

        text = Path(path).read_text(encoding="utf-8")
        instance = json.loads(text)
        return self.errors(instance)


def _format_error(err: ValidationError) -> str:
    location = "/".join(str(p) for p in err.absolute_path) or "<root>"
    return f"  at {location}: {err.message}"


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns process exit code."""

    parser = argparse.ArgumentParser(
        prog="helios-provenance-validate",
        description="Validate JSON files against the HELIOS provenance schema v0.1.",
    )
    parser.add_argument(
        "files",
        metavar="FILE",
        nargs="+",
        help="One or more JSON files (or '-' for stdin) to validate.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    validator = HeliosProvenanceValidator()
    overall_ok = True
    for filename in args.files:
        try:
            instance = _load_input(filename)
        except (OSError, json.JSONDecodeError) as exc:
            logger.error("%s: could not read JSON (%s)", filename, exc)
            overall_ok = False
            continue
        errs = validator.errors(instance)
        if errs:
            overall_ok = False
            logger.error("%s: INVALID (%d error%s)", filename, len(errs), "s" if len(errs) != 1 else "")
            for err in errs:
                logger.error("%s", _format_error(err))
        else:
            logger.info("%s: OK", filename)

    return 0 if overall_ok else 1


def _load_input(filename: str) -> Any:
    if filename == "-":
        return json.loads(sys.stdin.read())
    return json.loads(Path(filename).read_text(encoding="utf-8"))


if __name__ == "__main__":  # pragma: no cover — CLI entry point
    raise SystemExit(main())

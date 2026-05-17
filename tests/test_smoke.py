"""Smoke tests: import the package and confirm version is well-formed."""

from __future__ import annotations

import re

import helios_provenance


def test_version_is_semver() -> None:
    assert re.match(r"^\d+\.\d+\.\d+", helios_provenance.__version__)


def test_package_imports_clean() -> None:
    assert hasattr(helios_provenance, "__version__")
    assert helios_provenance.SCHEMA_VERSION == "0.1.0"


def test_public_api_surface() -> None:
    # Spot-check that the names promised in __all__ are actually exported.
    for name in helios_provenance.__all__:
        assert hasattr(helios_provenance, name), f"missing public symbol: {name}"

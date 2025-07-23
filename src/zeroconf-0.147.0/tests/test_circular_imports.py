"""Test to check for circular imports."""

from __future__ import annotations

import asyncio
import sys

import pytest


@pytest.mark.asyncio
@pytest.mark.timeout(30)  # cloud can take > 9s
@pytest.mark.parametrize(
    "module",
    [
        "zeroconf",
        "zeroconf.asyncio",
        "zeroconf._protocol.incoming",
        "zeroconf._protocol.outgoing",
        "zeroconf.const",
        "zeroconf._logger",
        "zeroconf._transport",
        "zeroconf._record_update",
        "zeroconf._services.browser",
        "zeroconf._services.info",
    ],
)
async def test_circular_imports(module: str) -> None:
    """Check that components can be imported without circular imports."""
    process = await asyncio.create_subprocess_exec(sys.executable, "-c", f"import {module}")
    await process.communicate()
    assert process.returncode == 0

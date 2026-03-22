# SPDX-License-Identifier: Apache-2.0
"""Shared pytest fixtures and configuration."""

import os
import pytest
from pathlib import Path


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (require hardware)"
    )


def pytest_collection_modifyitems(config, items):
    """Skip integration tests unless --integration flag is passed."""
    if config.getoption("--integration", default=False):
        return

    skip_integration = pytest.mark.skip(reason="need --integration option to run")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--integration",
        action="store_true",
        default=False,
        help="run integration tests (requires AMD GPU hardware)",
    )


@pytest.fixture
def temp_dir(tmp_path):
    """Provide a temporary directory for test outputs."""
    return tmp_path


@pytest.fixture
def sample_data():
    """Provide sample byte data for mutation tests."""
    return bytes(range(64))


@pytest.fixture
def zero_data():
    """Provide zero-filled byte data."""
    return b"\x00" * 64

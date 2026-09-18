"""Keep unit tests independent of the developer's saved credentials."""

from collections.abc import Iterator
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def isolated_service_keychain() -> Iterator[None]:
    """Never access real service credentials during unit tests."""
    with patch("mcp_atlassian.utils.credentials.get_password", return_value=None):
        yield

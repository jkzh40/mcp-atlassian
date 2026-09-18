"""Keychain precedence and service configuration integration."""

from unittest.mock import patch

import pytest
from keyring.errors import KeyringLocked, NoKeyringError

from mcp_atlassian.confluence.config import ConfluenceConfig
from mcp_atlassian.jira.config import JiraConfig
from mcp_atlassian.utils.credentials import get_service_credential
from mcp_atlassian.utils.environment import get_available_services


@pytest.mark.parametrize("name", ["JIRA_API_TOKEN", "CONFLUENCE_API_TOKEN"])
def test_keychain_precedes_environment(name: str) -> None:
    with (
        patch("mcp_atlassian.utils.credentials.sys.platform", "darwin"),
        patch("mcp_atlassian.utils.credentials.getpass.getuser", return_value="jack"),
        patch(
            "mcp_atlassian.utils.credentials.get_password", return_value="saved"
        ) as read,
        patch.dict("os.environ", {name: "environment"}, clear=True),
    ):
        assert get_service_credential(name) == "saved"
        read.assert_called_once_with("ATLASSIAN_API_TOKEN", "jack")


@pytest.mark.parametrize("missing_backend", [False, True])
def test_absent_item_or_backend_uses_environment(missing_backend: bool) -> None:
    with (
        patch("mcp_atlassian.utils.credentials.sys.platform", "darwin"),
        patch(
            "mcp_atlassian.utils.credentials.get_password",
            return_value=None,
            side_effect=NoKeyringError() if missing_backend else None,
        ),
        patch.dict("os.environ", {"JIRA_API_TOKEN": "environment"}, clear=True),
    ):
        assert get_service_credential("JIRA_API_TOKEN") == "environment"


def test_denied_keychain_does_not_fall_back() -> None:
    with (
        patch("mcp_atlassian.utils.credentials.sys.platform", "darwin"),
        patch(
            "mcp_atlassian.utils.credentials.get_password", side_effect=KeyringLocked()
        ),
        patch.dict("os.environ", {"JIRA_API_TOKEN": "environment"}, clear=True),
        pytest.raises(
            RuntimeError, match="Cannot read Keychain item ATLASSIAN_API_TOKEN"
        ),
    ):
        get_service_credential("JIRA_API_TOKEN")


def test_other_platforms_do_not_read_keychain() -> None:
    with (
        patch("mcp_atlassian.utils.credentials.sys.platform", "linux"),
        patch("mcp_atlassian.utils.credentials.get_password") as read,
        patch.dict("os.environ", {"JIRA_API_TOKEN": "environment"}, clear=True),
    ):
        assert get_service_credential("JIRA_API_TOKEN") == "environment"
        read.assert_not_called()


def test_keychain_only_enables_and_configures_both_services() -> None:
    items = {
        "ATLASSIAN_SITE_URL": "https://example.atlassian.net/",
        "ATLASSIAN_EMAIL": "test@example.com",
        "ATLASSIAN_API_TOKEN": "saved-token",
    }
    with (
        patch("mcp_atlassian.utils.credentials.sys.platform", "darwin"),
        patch(
            "mcp_atlassian.utils.credentials.get_password",
            side_effect=lambda item, account: items[item],
        ),
        patch.dict("os.environ", {}, clear=True),
    ):
        assert get_available_services() == {"jira": True, "confluence": True}
        jira = JiraConfig.from_env()
        confluence = ConfluenceConfig.from_env()
        assert jira.url.rstrip("/") == "https://example.atlassian.net"
        assert confluence.url == "https://example.atlassian.net/wiki"
        for config in (jira, confluence):
            assert config.auth_type == "basic"
            assert config.username == "test@example.com"
            assert config.api_token == "saved-token"

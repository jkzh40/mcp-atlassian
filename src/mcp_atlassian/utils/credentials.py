"""Resolve shared macOS Keychain credentials before service environment values."""

import getpass
import os
import sys

from keyring import get_password
from keyring.errors import KeyringError, NoKeyringError

_KEYCHAIN_ITEMS = {
    "JIRA_URL": "ATLASSIAN_SITE_URL",
    "CONFLUENCE_URL": "ATLASSIAN_SITE_URL",
    "JIRA_USERNAME": "ATLASSIAN_EMAIL",
    "CONFLUENCE_USERNAME": "ATLASSIAN_EMAIL",
    "JIRA_API_TOKEN": "ATLASSIAN_API_TOKEN",
    "CONFLUENCE_API_TOKEN": "ATLASSIAN_API_TOKEN",
}


def get_service_credential(name: str) -> str | None:
    """Read a shared Keychain item, falling back to the service's environment.

    Keychain items use the local login name as their account. Only absent items
    or an unavailable backend permit fallback; denied access must not silently
    select different credentials. Non-macOS hosts retain environment-only auth.
    """
    item = _KEYCHAIN_ITEMS[name]
    value = None
    if sys.platform == "darwin":
        try:
            value = get_password(item, getpass.getuser())
        except NoKeyringError:
            # Hosts without a usable backend retain environment-based setup.
            pass
        except KeyringError as exc:
            raise RuntimeError(
                f"Cannot read Keychain item {item}; unlock Keychain and allow "
                "access for this process."
            ) from exc
    if value is None:
        return os.getenv(name)
    if name == "CONFLUENCE_URL":
        return value.rstrip("/") + "/wiki"
    return value

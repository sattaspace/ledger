"""Configuration for the Sattabase SDK."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SattabaseConfig:
    """Sattabase SDK configuration.

    Attributes:
        base_url: Sattabase API base URL (e.g. ``https://sattabase.tld/api/v1``).
        service_domain: Identifies this service domain (e.g. ``finance.sattabase.tld``).
        api_key: Service credential raw key (format: ``sb_live_{token_urlsafe(32)}``).
                 Stored in memory only — never persisted to disk.
        timeout: HTTP request timeout in seconds.
        auto_refresh: Enable automatic token refresh on 401.
        max_retries: Max retries after token refresh (total attempts = 1 + max_retries).
        debug: When True, allows http:// base_url and relaxes validation.
    """

    base_url: str
    service_domain: str
    api_key: str
    timeout: float = 10.0
    auto_refresh: bool = True
    max_retries: int = 1
    debug: bool = False

    def __post_init__(self) -> None:
        if not self.api_key.startswith("sb_live_"):
            raise ValueError(
                f"Invalid API key format: must start with 'sb_live_', "
                f"got '{self.api_key[:12]}...'"
            )
        if not self.debug and not self.base_url.startswith("https://"):
            raise ValueError(
                f"base_url must use HTTPS in production (set debug=True to override). "
                f"Got: {self.base_url}"
            )

    @property
    def app_base_url(self) -> str:
        """Derive the Sattabase app base URL from the API base URL.

        Strips ``/api/v1`` (and trailing slash) to get the frontend root.
        Example: ``https://sattabase.tld/api/v1`` → ``https://sattabase.tld``
        """
        url = self.base_url.rstrip("/")
        if url.endswith("/api/v1"):
            url = url[: -len("/api/v1")]
        return url

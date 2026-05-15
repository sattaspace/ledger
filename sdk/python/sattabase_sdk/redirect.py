"""Redirect module — URL constructors for billing flows.

Zero API calls. These methods only construct URL strings.
Actual ``return_url`` validation happens server-side in ``validate_return_url()`` (Phase 6.5).
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urlencode, parse_qs, urlparse

if TYPE_CHECKING:
    from .client import SattabaseClient


class BillingRedirectModule:
    """Billing redirect URL constructors.

    These methods build URLs for redirecting users to Sattabase's billing
    pages. The actual server-side validation of ``return_url`` is handled
    by the Sattabase backend (Phase 6.5).
    """

    def __init__(self, client: SattabaseClient) -> None:
        self._client = client

    def _build_url(self, path: str, return_url: str | None = None) -> str:
        """Build a redirect URL with optional return_url parameter."""
        from urllib.parse import quote

        base = self._client.config.app_base_url
        url = f"{base}{path}"

        if return_url:
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}return_url={quote(return_url, safe='')}"

        return url

    def manage_subscription(
        self,
        product_slug: str,
        return_url: str | None = None,
    ) -> str:
        """Build URL to manage a subscription (view plans, upgrade, cancel).

        Args:
            product_slug: The product slug (e.g. ``"finance"``).
            return_url: URL to redirect back to after billing action.
                         If None, Sattabase uses its own default.

        Returns:
            Full URL string.

        Example::

            url = client.billing.manage_subscription(
                "finance",
                "https://finance.sattabase.tld/settings",
            )
            # → "https://sattabase.tld/billing/finance?return_url=..."
        """
        return self._build_url(f"/dashboard/billing/plans/{product_slug}", return_url)

    def upgrade(
        self,
        product_slug: str,
        return_url: str | None = None,
    ) -> str:
        """Build URL for the upgrade/plan selection page.

        Args:
            product_slug: The product slug.
            return_url: URL to redirect back to after checkout.

        Returns:
            Full URL string.
        """
        return self._build_url(f"/dashboard/billing/plans/{product_slug}", return_url)

    def portal(self, return_url: str | None = None) -> str:
        """Build URL for the Stripe Customer Portal.

        Args:
            return_url: URL to redirect back to after portal session.

        Returns:
            Full URL string.
        """
        return self._build_url("/dashboard/billing", return_url)

    @staticmethod
    def detect_billing_update(url: str) -> tuple[bool, int | None]:
        """Parse a URL for the ``billing_updated`` query parameter.

        Sister domains call this on page load to detect return from a
        billing redirect (Phase 6.5.11).

        Args:
            url: The URL to parse (can include query params).

        Returns:
            Tuple of ``(detected, value)``:
            - ``(True, 1)`` for ``?billing_updated=1`` (success)
            - ``(True, 0)`` for ``?billing_updated=0`` (cancel/failure)
            - ``(False, None)`` if parameter not present

        Example::

            ok, val = BillingRedirectModule.detect_billing_update(request.url)
            if ok and val == 1:
                await refresh_user_access()
        """
        parsed = urlparse(url)
        params = parse_qs(parsed.query)

        if "billing_updated" not in params:
            return (False, None)

        raw = params["billing_updated"][0]
        try:
            return (True, int(raw))
        except ValueError:
            return (True, None)

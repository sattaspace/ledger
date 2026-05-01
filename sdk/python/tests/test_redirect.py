"""Tests for redirect module."""

from __future__ import annotations

from sattabase_sdk.redirect import BillingRedirectModule


class TestBillingRedirect:
    """Tests for billing URL construction."""

    def _make_module(self, app_base_url: str = "https://sattabase.tld"):
        """Create a minimal BillingRedirectModule for testing."""
        from unittest.mock import MagicMock
        mock_client = MagicMock()
        mock_client.config.app_base_url = app_base_url
        return BillingRedirectModule(mock_client)

    def test_manage_subscription(self):
        """Build manage subscription URL."""
        module = self._make_module()
        url = module.manage_subscription("finance", "https://finance.sattabase.tld/settings")
        assert url.startswith("https://sattabase.tld/dashboard/billing/plans/finance")
        assert "return_url=" in url
        assert "finance.sattabase.tld" in url

    def test_manage_subscription_no_return_url(self):
        """Build manage subscription URL without return_url."""
        module = self._make_module()
        url = module.manage_subscription("finance")
        assert url == "https://sattabase.tld/dashboard/billing/plans/finance"

    def test_upgrade(self):
        """Build upgrade URL."""
        module = self._make_module()
        url = module.upgrade("analytics", "https://analytics.sattabase.tld/billing")
        assert url.startswith("https://sattabase.tld/dashboard/billing/plans/analytics")
        assert "return_url=" in url

    def test_portal(self):
        """Build portal URL."""
        module = self._make_module()
        url = module.portal("https://sattabase.tld/dashboard")
        assert url.startswith("https://sattabase.tld/dashboard/billing")
        assert "return_url=" in url

    def test_portal_no_return_url(self):
        """Build portal URL without return_url."""
        module = self._make_module()
        url = module.portal()
        assert url == "https://sattabase.tld/dashboard/billing"


class TestDetectBillingUpdate:
    """Tests for billing_updated query param detection."""

    def test_billing_updated_success(self):
        """Detect billing_updated=1."""
        result = BillingRedirectModule.detect_billing_update(
            "https://finance.sattabase.tld/dashboard?billing_updated=1"
        )
        assert result == (True, 1)

    def test_billing_updated_cancel(self):
        """Detect billing_updated=0."""
        result = BillingRedirectModule.detect_billing_update(
            "https://finance.sattabase.tld/dashboard?billing_updated=0"
        )
        assert result == (True, 0)

    def test_billing_updated_not_present(self):
        """Return (False, None) when billing_updated is absent."""
        result = BillingRedirectModule.detect_billing_update(
            "https://finance.sattabase.tld/dashboard"
        )
        assert result == (False, None)

    def test_billing_updated_with_other_params(self):
        """Detect billing_updated among other query params."""
        result = BillingRedirectModule.detect_billing_update(
            "https://finance.sattabase.tld/dashboard?tab=settings&billing_updated=1&page=2"
        )
        assert result == (True, 1)

    def test_billing_updated_invalid_value(self):
        """Handle invalid billing_updated value."""
        result = BillingRedirectModule.detect_billing_update(
            "https://finance.sattabase.tld/dashboard?billing_updated=abc"
        )
        assert result == (True, None)

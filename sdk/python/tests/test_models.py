"""Tests for model helper methods."""

from sattabase_sdk.models import AuthMeResponse, SubscriptionInfo, User


class TestUser:
    """Tests for User model."""

    def test_display_property_with_display_name(self):
        user = User(id=1, slug="rahim", display_name="Rahim", full_name="Rahim Uddin", email="test@example.com")
        assert user.display == "Rahim"

    def test_display_property_fallback_to_full_name(self):
        user = User(id=2, slug="rahim2", display_name="", full_name="Rahim Uddin", email="test@example.com")
        assert user.display == "Rahim Uddin"

    def test_display_property_fallback_to_email(self):
        user = User(id=3, slug="userx", display_name="", full_name="", email="user@example.com")
        assert user.display == "user"


class TestAuthMeResponse:
    """Tests for AuthMeResponse helper methods."""

    def _make_auth_me(self, access: dict) -> AuthMeResponse:
        return AuthMeResponse(
            user=User(id=1, slug="abc", email="test@example.com"),
            access=access,
        )

    def test_has_access_boolean_true(self):
        auth_me = self._make_auth_me({"reports": True})
        assert auth_me.has_access("reports") is True

    def test_has_access_boolean_false(self):
        auth_me = self._make_auth_me({"reports": False})
        assert auth_me.has_access("reports") is False

    def test_has_access_string_true(self):
        """String 'true' is coerced to True."""
        auth_me = self._make_auth_me({"reports": "true"})
        assert auth_me.has_access("reports") is True

    def test_has_access_string_false(self):
        """String 'false' is coerced to False."""
        auth_me = self._make_auth_me({"reports": "false"})
        assert auth_me.has_access("reports") is False

    def test_has_access_string_yes(self):
        """String 'yes' is coerced to True."""
        auth_me = self._make_auth_me({"reports": "yes"})
        assert auth_me.has_access("reports") is True

    def test_has_access_string_1(self):
        """String '1' is coerced to True."""
        auth_me = self._make_auth_me({"reports": "1"})
        assert auth_me.has_access("reports") is True

    def test_has_access_integer_nonzero(self):
        """Non-zero integer is coerced to True."""
        auth_me = self._make_auth_me({"max_accounts": 5})
        assert auth_me.has_access("max_accounts") is True

    def test_has_access_integer_zero(self):
        """Zero integer is coerced to False."""
        auth_me = self._make_auth_me({"max_accounts": 0})
        assert auth_me.has_access("max_accounts") is False

    def test_has_access_missing_key(self):
        """Missing key returns False."""
        auth_me = self._make_auth_me({})
        assert auth_me.has_access("nonexistent") is False

    def test_has_access_none_value(self):
        """None value returns False."""
        auth_me = self._make_auth_me({"reports": None})
        assert auth_me.has_access("reports") is False

    def test_get_access(self):
        auth_me = self._make_auth_me({"max_accounts": 5})
        assert auth_me.get_access("max_accounts") == 5
        assert auth_me.get_access("missing", "default") == "default"

    def test_access_keys(self):
        auth_me = self._make_auth_me({"dashboard": True, "reports": False, "api": True})
        keys = auth_me.access_keys
        assert "dashboard" in keys
        assert "reports" in keys
        assert len(keys) == 3

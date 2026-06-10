"""
DEALERCORE v3.0 — Dealer App Models
-------------------------------------
Dealer configuration (user preferences, currency, locale).
`username` is the natural primary key — NOT auto-incremented.
"""

from django.db import models


class DealerConfig(models.Model):
    """Dealer-level settings. One record per dealer account.
    `username` serves as the natural primary key."""

    CURRENCIES = [
        ("INR", "INR"),
        ("USD", "USD"),
        ("EUR", "EUR"),
        ("GBP", "GBP"),
        ("AED", "AED"),
        ("JPY", "JPY"),
        ("CAD", "CAD"),
        ("AUD", "AUD"),
        ("SGD", "SGD"),
    ]

    username = models.CharField(max_length=150, primary_key=True)
    full_name = models.CharField(max_length=255)
    role = models.CharField(max_length=100, default="Dealer")
    business_name = models.CharField(max_length=255, blank=True, default="")
    address = models.TextField(blank=True, default="")
    phone_number = models.CharField(max_length=20, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    gst_number = models.CharField(max_length=20, blank=True, default="")
    google_map_url = models.URLField(blank=True, default="")
    communication_number = models.CharField(max_length=20, blank=True, default="")
    default_currency = models.CharField(
        max_length=3, choices=CURRENCIES, default="INR"
    )
    default_locale = models.CharField(max_length=10, default="en-IN")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["username"]
        verbose_name = "Dealer Configuration"
        verbose_name_plural = "Dealer Configurations"

    def __str__(self):
        return f"{self.full_name} (@{self.username})"

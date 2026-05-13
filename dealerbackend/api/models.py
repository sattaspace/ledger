from django.db import models


class TestNote(models.Model):
    """Test model to verify Sattabase SDK integration.

    Uses ``user_id`` as an integer FK pointing to the Sattabase User.id
    — the single integer that ties all sister domain data to a Sattabase user.
    No Django FK because the User model lives in the Sattabase backend, not here.
    """

    user_id = models.PositiveIntegerField(
        db_index=True,
        help_text="Sattabase User.id — the central identity FK",
    )
    title = models.CharField(max_length=200)
    content = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        db_table = "api_test_note"

    def __str__(self) -> str:
        return f"TestNote(user_id={self.user_id}, title={self.title!r})"

"""Category and Tag models for transaction classification.

Categories: Hierarchical, mutually exclusive (one per transaction).
Tags: Flat, additive (many per transaction).
"""

from django.db import models

from common.models import UserOwnedModel


class Category(UserOwnedModel):
    """Transaction category with optional hierarchy.

    Supports nested subcategories via parent FK.
    is_income determines whether the category represents income (True) or expense (False).

    Examples:
      - Food (parent=None, is_income=False)
        - Groceries (parent=Food, is_income=False)
        - Dining Out (parent=Food, is_income=False)
      - Salary (parent=None, is_income=True)
      - Freelance (parent=None, is_income=True)
    """

    name = models.CharField(max_length=50)
    icon = models.CharField(
        max_length=50, blank=True, help_text="Icon name from icon library"
    )
    color = models.CharField(
        max_length=7, blank=True, help_text="Hex color for charts and UI"
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="subcategories",
    )
    is_income = models.BooleanField(default=False)
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = "categories_category"
        ordering = ["sort_order", "name"]
        verbose_name_plural = "categories"
        unique_together = [("user_id", "name", "parent")]

    def __str__(self) -> str:
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name


class Tag(UserOwnedModel):
    """Flat, cross-cutting label for transactions.

    Unlike categories (hierarchical, mutually exclusive), tags are flat and
    additive. A transaction has ONE category but can have MANY tags.

    Examples: #vacation2026, #tax-deductible, #business, #reimbursable
    """

    name = models.CharField(max_length=50)
    color = models.CharField(max_length=7, blank=True)

    class Meta:
        db_table = "categories_tag"
        ordering = ["name"]
        unique_together = [("user_id", "name")]

    def __str__(self) -> str:
        return f"#{self.name}"


class TransactionTag(UserOwnedModel):
    """Many-to-many link between Transaction and Tag.

    Why not Django's ManyToManyField?
    Because we need user_id on the through table for consistent ownership
    queries and soft-delete support.
    """

    transaction = models.ForeignKey(
        "api.Transaction",
        on_delete=models.CASCADE,
        related_name="tag_links",
    )
    tag = models.ForeignKey(
        Tag,
        on_delete=models.CASCADE,
        related_name="transaction_links",
    )

    class Meta:
        db_table = "categories_transaction_tag"
        unique_together = [("transaction", "tag")]

    def __str__(self) -> str:
        return f"{self.transaction} ← {self.tag}"

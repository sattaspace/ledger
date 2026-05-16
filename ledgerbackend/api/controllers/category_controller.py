"""Category controller — CRUD + tree structure for hierarchical categories."""

import logging

from ninja import Query
from ninja_extra import api_controller, route

from api.models import Category
from api.schemas.categories import (
    CategoryCreate,
    CategoryFilter,
    CategoryListOut,
    CategoryOut,
    CategoryTreeOut,
    CategoryUpdate,
)
from api.schemas.common import MessageOut, PaginatedResponse

from .base import LedgerControllerBase

logger = logging.getLogger(__name__)


@api_controller("/categories", tags=["Categories"])
class CategoryController(LedgerControllerBase):

    # ── List ──────────────────────────────────────────────────────────────

    @route.get("", response=PaginatedResponse[CategoryOut])
    def list_categories(self, request, filters: CategoryFilter = Query(...)):
        """List all categories for the authenticated user, with pagination and filters."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "categories")
        qs = Category.objects.filter(user_id=user_id).select_related("parent")
        qs, limit, offset = self.apply_filters(qs, filters)
        return self.paginate(qs, limit, offset)

    @route.get("/dropdown", response=list[CategoryListOut])
    def list_dropdown(self, request):
        """Lightweight list for dropdown/select components."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "categories")
        return list(Category.objects.filter(user_id=user_id).select_related("parent"))

    # ── Tree ──────────────────────────────────────────────────────────────

    @route.get("/tree", response=list[CategoryTreeOut])
    def category_tree(self, request):
        """Get categories as a tree structure for hierarchical display.

        Returns only top-level categories (parent=None) with nested subcategories.
        """
        user_id = self.require_user_id(request)
        self.require_feature(request, "categories")
        all_categories = Category.objects.filter(
            user_id=user_id,
        ).select_related("parent")

        # Build a lookup: parent_id -> list of children
        children_map: dict[int | None, list[Category]] = {}
        for cat in all_categories:
            parent_id = cat.parent_id
            children_map.setdefault(parent_id, []).append(cat)

        # Build tree recursively
        def build_tree(parent_id=None) -> list[dict]:
            children = children_map.get(parent_id, [])
            result = []
            for cat in children:
                node = {
                    "id": cat.id,
                    "name": cat.name,
                    "icon": cat.icon,
                    "color": cat.color,
                    "is_income": cat.is_income,
                    "sort_order": cat.sort_order,
                    "subcategories": build_tree(cat.id),
                }
                result.append(node)
            return result

        return build_tree(None)

    # ── Get ───────────────────────────────────────────────────────────────

    @route.get("/{int:category_id}", response=CategoryOut)
    def get_category(self, request, category_id: int):
        """Get a single category by ID."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "categories")
        return self.get_or_404(Category, user_id, category_id)

    # ── Create ────────────────────────────────────────────────────────────

    @route.post("", response=CategoryOut)
    def create_category(self, request, payload: CategoryCreate):
        """Create a new category. Use parent_id for subcategories."""
        user_id = self.require_user_id(request)
        self.require_subscription_active(request)
        self.require_feature(request, "categories")
        self.check_plan_limit(request, "max_categories",
                            Category.objects.filter(user_id=user_id).count())
        data = payload.model_dump()
        # Validate FK ownership — parent category must belong to this user
        if "parent_id" in data and data["parent_id"] is not None:
            self.validate_fk_ownership(request, Category, data["parent_id"])
            data["parent_id"] = data.pop("parent_id")
        else:
            data.pop("parent_id", None)
        obj = Category.objects.create(user_id=user_id, **data)
        logger.info("Category created: id=%s user_id=%s name=%s", obj.id, user_id, obj.name)
        return obj

    # ── Update ────────────────────────────────────────────────────────────

    @route.patch("/{int:category_id}", response=CategoryOut)
    def update_category(self, request, category_id: int, payload: CategoryUpdate):
        """Update an existing category. Only provided fields are changed."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "categories")
        obj = self.get_or_404(Category, user_id, category_id)
        self.update_object(obj, payload, fk_map={
            "parent_id": (Category, request),
        })
        return obj

    # ── Soft Delete ───────────────────────────────────────────────────────

    @route.delete("/{int:category_id}", response=MessageOut)
    def soft_delete_category(self, request, category_id: int):
        """Soft-delete a category."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "categories")
        obj = self.get_or_404(Category, user_id, category_id)
        obj.soft_delete()
        logger.info("Category soft-deleted: id=%s user_id=%s", obj.id, user_id)
        return {"detail": "Category deleted."}

    # ── Restore ───────────────────────────────────────────────────────────

    @route.post("/{int:category_id}/restore", response=MessageOut)
    def restore_category(self, request, category_id: int):
        """Restore a soft-deleted category."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "categories")
        self.require_subscription_active(request)
        self.check_plan_limit(request, "max_categories",
                            Category.objects.filter(user_id=user_id).count())
        obj = self.get_with_deleted_or_404(Category, user_id, category_id)
        obj.restore()
        return {"detail": "Category restored."}

    # ── Activate / Deactivate ─────────────────────────────────────────────

    @route.post("/{int:category_id}/activate", response=MessageOut)
    def activate_category(self, request, category_id: int):
        """Activate a category."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "categories")
        obj = self.get_or_404(Category, user_id, category_id)
        obj.activate()
        return {"detail": "Category activated."}

    @route.post("/{int:category_id}/deactivate", response=MessageOut)
    def deactivate_category(self, request, category_id: int):
        """Deactivate a category."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "categories")
        obj = self.get_or_404(Category, user_id, category_id)
        obj.deactivate()
        return {"detail": "Category deactivated."}

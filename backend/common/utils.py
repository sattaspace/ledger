"""Utility functions for the common app.

Provides both synchronous and asynchronous pagination helpers for use
with Django's ORM. Use async versions in async controller/service methods
to avoid blocking the event loop.
"""

import math
from typing import Any, List, Tuple, TypeVar

from django.db import models

T = TypeVar("T")


def get_paginated_data(
    queryset: models.QuerySet, page: int, page_size: int
) -> Tuple[List[Any], dict]:
    """Paginate a Django queryset and return results with metadata.

    Args:
        queryset: The Django queryset to paginate.
        page: Current page number (1-indexed).
        page_size: Number of items per page.

    Returns:
        A tuple of (results_list, metadata_dict).
    """
    total_items = queryset.count()
    total_pages = math.ceil(total_items / page_size) if total_items > 0 else 1

    # Clamp page to valid range
    page = max(1, min(page, total_pages))

    offset = (page - 1) * page_size
    results = list(queryset[offset : offset + page_size])

    meta = {
        "total_items": total_items,
        "total_pages": total_pages,
        "current_page": page,
        "page_size": page_size,
        "has_next": page < total_pages,
        "has_previous": page > 1,
    }

    return results, meta


async def get_paginated_data_async(
    queryset: models.QuerySet, page: int, page_size: int
) -> Tuple[List[Any], dict]:
    """Async version of get_paginated_data().

    Uses Django's async ORM methods (acount, async iteration) so the event
    loop is not blocked while waiting for database I/O.

    Args:
        queryset: The Django queryset to paginate.
        page: Current page number (1-indexed).
        page_size: Number of items per page.

    Returns:
        A tuple of (results_list, metadata_dict).

    Example::

        @http_get("/list")
        async def list_items(self, request, pagination: PaginationInput = Query(...)):
            qs = Item.objects.all().order_by("-created_at")
            results, meta = await get_paginated_data_async(qs, pagination.page, pagination.page_size)
            return {"meta": meta, "results": results}
    """
    total_items = await queryset.acount()
    total_pages = math.ceil(total_items / page_size) if total_items > 0 else 1

    # Clamp page to valid range
    page = max(1, min(page, total_pages))

    offset = (page - 1) * page_size
    paginated_qs = queryset[offset : offset + page_size]

    # Evaluate the queryset asynchronously
    results = [item async for item in paginated_qs.aiterator()]

    meta = {
        "total_items": total_items,
        "total_pages": total_pages,
        "current_page": page,
        "page_size": page_size,
        "has_next": page < total_pages,
        "has_previous": page > 1,
    }

    return results, meta

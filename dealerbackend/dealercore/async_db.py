"""
DEALERCORE v3.0 — Async Database Utilities
-------------------------------------------
Provides async-compatible wrappers for Django's transaction system
and async-safe queryset helpers.

CRITICAL FINDING:
  Django (including 5.1, 5.2, 6.0) does NOT support
  `async with transaction.atomic()`. The `Atomic` class only
  implements `__enter__` / `__exit__`, not `__aenter__` / `__aexit__`.

  Using `async with transaction.atomic()` will always raise:
    AttributeError: __aenter__

SOLUTION — `aatomic()`:
  An async context manager that provides TRUE transaction atomicity
  by managing the synchronous `transaction.atomic()` lifecycle
  through `sync_to_async` calls.

  How it works:
  1. `sync_to_async(transaction.atomic().__enter__)` starts the transaction
  2. The async code inside the `async with` block runs normally
  3. On success: `sync_to_async(transaction.atomic().__exit__)(None, None, None)`
     commits the transaction
  4. On exception: `sync_to_async(transaction.atomic().__exit__)(exc_type, exc_val, tb)`
     rolls back the transaction

  This works because Django's async ORM methods (aget, asave, acreate, etc.)
  internally use `sync_to_async` to run in the same thread as the event loop,
  and the transaction context is tracked per-database-connection, which is
  maintained correctly as long as we enter/exit the Atomic context manager
  in the same synchronous thread.

  IMPORTANT: For proper race-condition safety, use `select_for_update()`
  on rows that are read-then-modified (e.g. Product stock during sales).
  This acquires a database-level row lock within the transaction,
  preventing concurrent reads from seeing stale data.

ASYNC-SAFE QUERYSET HELPERS:
  `async_aggregate()` and `async_exists()` — sync_to_async wrapped
  versions of `aggregate()` and `exists()` that work on ALL Django
  versions >= 3.1. These are the recommended way to perform aggregate
  and existence checks in async controller code.

USAGE:
  from dealercore.async_db import aatomic, async_aggregate, async_exists

  async def my_view(self, payload):
      async with aatomic():
          # select_for_update() locks the row for this transaction
          product = await Product.objects.select_for_update().aget(id=pid)

          # Validate then modify — safe under concurrency
          if product.stock < payload.quantity:
              raise HttpError(400, "Insufficient stock")

          product.stock = F("stock") - payload.quantity
          await product.asave()

          sale = await SaleRecord.objects.acreate(...)
          # If asave() fails, stock decrement is also rolled back
"""

import warnings
from contextlib import asynccontextmanager

from asgiref.sync import sync_to_async
from django.db import transaction


# ─── Async-safe Queryset Helpers ─────────────────────────────────────────
# These work on ALL Django versions >= 3.1 by wrapping synchronous
# queryset methods with sync_to_async.


async def async_aggregate(queryset, **kwargs):
    """Async-compatible queryset.aggregate() — works on all Django versions.

    Usage:
        result = await async_aggregate(
            Product.objects.filter(id__startswith="prod"),
            _max=Max("id"),
        )
        max_id = result.get("_max")

    This wraps the synchronous `aggregate()` call in `sync_to_async`,
    avoiding the `aaggregate()` method which is only available in
    Django 4.2+ and may cause `TypeError: 'coroutine' object is not
    subscriptable` on some configurations.
    """
    @sync_to_async
    def _do():
        return queryset.aggregate(**kwargs)
    return await _do()


async def async_exists(queryset):
    """Async-compatible queryset.exists() — works on all Django versions.

    Usage:
        exists = await async_exists(
            Product.objects.filter(id="prod-1"),
        )

    This wraps the synchronous `exists()` call in `sync_to_async`,
    avoiding the `aexists()` method which is only available in
    Django 4.2+.
    """
    @sync_to_async
    def _do():
        return queryset.exists()
    return await _do()


# ─── Async Transaction Wrapper ───────────────────────────────────────────
#
# Django does NOT natively support `async with transaction.atomic()`.
# The Atomic class only has __enter__/__exit__, never __aenter__/__aexit__.
#
# This async context manager provides proper transaction atomicity by:
# 1. Entering the synchronous Atomic context via sync_to_async
# 2. Running the async body code (which uses async ORM methods internally)
# 3. Exiting the Atomic context via sync_to_async (commit or rollback)
#
# The key insight: Django's async ORM methods (aget, asave, acreate, etc.)
# internally call their sync counterparts via sync_to_async, which means
# they execute in the same database connection context. As long as we
# properly enter/exit the Atomic context manager in sync land, the
# transaction boundary is respected.

@asynccontextmanager
async def aatomic(using=None):
    """Async-compatible atomic transaction context manager.

    Provides TRUE multi-statement transaction atomicity for async code:
    - All database operations within the block are committed together
    - If any operation raises an exception, ALL changes are rolled back
    - Works with select_for_update() for row-level locking

    This works by managing the synchronous `transaction.atomic()` context
    manager lifecycle through sync_to_async calls. Django's async ORM
    methods (aget, asave, acreate, etc.) internally use sync_to_async,
    so they execute within the same transaction context.

    Usage:
        async with aatomic():
            product = await Product.objects.select_for_update().aget(id=pid)
            product.stock = F("stock") - quantity
            await product.asave()
            await SaleRecord.objects.acreate(...)
            # Both operations commit together, or neither does
    """
    # Create the Atomic context manager
    atomic_ctx = transaction.atomic(using=using)

    # Enter the transaction (synchronous __enter__)
    await sync_to_async(atomic_ctx.__enter__)()

    try:
        yield
    except Exception:
        # Exception occurred — rollback the transaction
        import sys
        exc_type, exc_val, exc_tb = sys.exc_info()
        await sync_to_async(atomic_ctx.__exit__)(exc_type, exc_val, exc_tb)
        raise
    else:
        # No exception — commit the transaction
        await sync_to_async(atomic_ctx.__exit__)(None, None, None)

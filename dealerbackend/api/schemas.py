"""Ninja schemas for the test model."""

from datetime import datetime
from typing import Optional

from ninja import Schema


class TestNoteCreate(Schema):
    title: str
    content: str = ""


class TestNoteUpdate(Schema):
    title: Optional[str] = None
    content: Optional[str] = None


class TestNoteOut(Schema):
    id: int
    user_id: int
    title: str
    content: str
    created_at: datetime
    updated_at: datetime

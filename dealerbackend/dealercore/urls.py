"""
DEALERCORE v3.0 — Project URL Configuration
----------------------------------------------
Mounts the NinjaAPI at /api/ and the Django admin at /admin/.

Required INSTALLED_APPS:
    - django.contrib.admin
    - django.contrib.auth
    - django.contrib.contenttypes
    - django.contrib.sessions
    - django.contrib.messages
    - django.contrib.staticfiles
    - ninja
    - inventory
    - sales
    - dsr
    - supplier
    - dealer
    - reports

Required packages:
    pip install django ninja pydantic
"""

from django.contrib import admin
from django.urls import path

from dealercore.api import api

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),
]

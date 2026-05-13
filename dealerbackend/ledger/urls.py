"""
URL configuration for ledger project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings
from api.views import api

# Import the api instance

admin.site.site_header = "Satta Ledger admin"
admin.site.site_title = "Satta Ledger admin"
# admin.site.site_url = ''
admin.site.index_title = "Satta Ledger administration"
# admin.empty_value_display = '**Empty**'

admin.autodiscover()
# admin.site.login = secure_admin_login(admin.site.login)  # type: ignore

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", api.urls, name="base"),  # Optional but recommended
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
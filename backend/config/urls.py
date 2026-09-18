"""URL configuration."""

# Import admin UI customizations before exposing admin.site.urls.
import core.admin  # noqa: F401

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from config.api import api

urlpatterns = [
    path("admin/", admin.site.urls),
    path("_nested_admin/", include("nested_admin.urls")),
    path("api/", api.urls),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [
        path("__debug__/", include(debug_toolbar.urls)),
    ]
    # MEDIA_URL may be absolute (e.g. http://localhost:12001/media/) in some setups,
    # but Django URL patterns need a path prefix. Always serve at /media/ for dev.
    urlpatterns += static("/media/", document_root=settings.MEDIA_ROOT)

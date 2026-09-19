from django.contrib import admin
from django.urls import include, path
from drf_spectacular.renderers import OpenApiJsonRenderer
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView

from config import health

urlpatterns = [
    path("", health.root, name="root"),
    path("admin/", admin.site.urls),
    path("health/", health.live, name="health"),
    path("health/live/", health.live, name="health-live"),
    path("health/ready/", health.ready, name="health-ready"),
    path(
        "api/v1/auth/token/",
        TokenObtainPairView.as_view(permission_classes=[AllowAny]),
        name="token-obtain",
    ),
    path(
        "api/v1/auth/token/refresh/",
        TokenRefreshView.as_view(permission_classes=[AllowAny]),
        name="token-refresh",
    ),
    path(
        "api/v1/auth/token/verify/",
        TokenVerifyView.as_view(permission_classes=[AllowAny]),
        name="token-verify",
    ),
    path("api/v1/", include("apps.scheduling.urls")),
    path(
        "api/schema/",
        SpectacularAPIView.as_view(
            permission_classes=[AllowAny],
            renderer_classes=[OpenApiJsonRenderer],
        ),
        name="schema",
    ),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema", permission_classes=[AllowAny]),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema", permission_classes=[AllowAny]),
        name="redoc",
    ),
]

handler400 = "config.exceptions.json_bad_request"
handler404 = "config.exceptions.json_not_found"
handler500 = "config.exceptions.json_server_error"

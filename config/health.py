"""Dependency-free liveness and database readiness probes."""

from django.db import connection
from django.http import JsonResponse
from django.views.decorators.cache import never_cache


@never_cache
def live(request):
    if request.method not in {"GET", "HEAD"}:
        return method_not_allowed()
    return JsonResponse({"status": "ok"})


@never_cache
def ready(request):
    if request.method not in {"GET", "HEAD"}:
        return method_not_allowed()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        return JsonResponse({"status": "unavailable", "database": "down"}, status=503)
    return JsonResponse({"status": "ok", "database": "up"})


def root(request):
    if request.method not in {"GET", "HEAD"}:
        return method_not_allowed()
    return JsonResponse(
        {
            "name": "Lacrei Saúde - API de Consultas",
            "version": "1.0.0",
            "health": "/health/ready/",
            "documentation": "/api/docs/",
        }
    )


def method_not_allowed():
    response = JsonResponse(
        {
            "error": {
                "code": "method_not_allowed",
                "message": "Método HTTP não permitido.",
            }
        },
        status=405,
    )
    response["Allow"] = "GET, HEAD"
    return response

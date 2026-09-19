"""Consistent, non-leaky JSON error responses."""

from __future__ import annotations

import logging

from django.http import JsonResponse
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    request = context.get("request")
    request_id = getattr(request, "request_id", None)

    if response is None:
        logger.error(
            "unhandled_api_error",
            exc_info=(type(exc), exc, exc.__traceback__),
            extra={"request_id": request_id},
        )
        return Response(
            {
                "error": {
                    "code": "internal_error",
                    "message": "Ocorreu um erro interno.",
                    "request_id": request_id,
                }
            },
            status=500,
        )

    code = getattr(exc, "default_code", "request_error")
    message = "Não foi possível processar a requisição."
    if isinstance(response.data, dict) and set(response.data) == {"detail"}:
        message = str(response.data["detail"])

    response.data = {
        "error": {
            "code": str(code),
            "message": message,
            "details": response.data,
            "request_id": request_id,
        }
    }
    return response


def json_not_found(request, exception=None):
    return JsonResponse(
        {
            "error": {
                "code": "not_found",
                "message": "Recurso não encontrado.",
                "request_id": getattr(request, "request_id", None),
            }
        },
        status=404,
    )


def json_bad_request(request, exception=None):
    return JsonResponse(
        {
            "error": {
                "code": "bad_request",
                "message": "Requisição inválida.",
                "request_id": getattr(request, "request_id", None),
            }
        },
        status=400,
    )


def json_server_error(request):
    logger.error(
        "unhandled_server_error",
        extra={"request_id": getattr(request, "request_id", None)},
    )
    return JsonResponse(
        {
            "error": {
                "code": "internal_error",
                "message": "Ocorreu um erro interno.",
                "request_id": getattr(request, "request_id", None),
            }
        },
        status=500,
    )

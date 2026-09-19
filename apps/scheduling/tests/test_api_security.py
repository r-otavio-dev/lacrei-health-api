from __future__ import annotations

import json
import uuid
from unittest.mock import patch

from django.http import HttpResponse
from django.test import RequestFactory, override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.scheduling.tests.base import AuthenticatedAPITestCase
from config.exceptions import api_exception_handler, json_bad_request, json_server_error
from config.middleware import AccessLogMiddleware


class AuthenticationTests(AuthenticatedAPITestCase):
    def test_valid_jwt_authenticates_api_request(self) -> None:
        self.client.force_authenticate(user=None)
        token_response = self.client.post(
            "/api/v1/auth/token/",
            {"username": self.user.username, "password": self.password},
            format="json",
        )

        self.assertEqual(token_response.status_code, status.HTTP_200_OK)
        self.assertIn("access", token_response.data)
        self.assertIn("refresh", token_response.data)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token_response.data['access']}")
        response = self.client.get("/api/v1/professionals/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_invalid_jwt_returns_json_error(self) -> None:
        self.client.force_authenticate(user=None)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer invalid-token")

        response = self.client.get("/api/v1/professionals/")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertEqual(response.data["error"]["code"], "token_not_valid")


class OperationalEndpointTests(APITestCase):
    def test_liveness_and_readiness_are_public_json(self) -> None:
        live_response = self.client.get("/health/live/")
        ready_response = self.client.get("/health/ready/")

        self.assertEqual(live_response.status_code, status.HTTP_200_OK)
        self.assertEqual(live_response.json(), {"status": "ok"})
        self.assertEqual(ready_response.status_code, status.HTTP_200_OK)
        self.assertEqual(ready_response.json()["database"], "up")

    def test_root_describes_service(self) -> None:
        response = self.client.get("/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["version"], "1.0.0")

    @override_settings(CORS_ALLOWED_ORIGINS=["https://app.example.com"])
    def test_cors_preflight_allows_only_configured_origin(self) -> None:
        response = self.client.options(
            "/api/v1/professionals/",
            HTTP_ORIGIN="https://app.example.com",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response["Access-Control-Allow-Origin"],
            "https://app.example.com",
        )

    def test_request_id_is_echoed_and_bounded(self) -> None:
        response = self.client.get("/health/live/", HTTP_X_REQUEST_ID="trace-123")

        self.assertEqual(response["X-Request-ID"], "trace-123")

    def test_request_id_is_sanitized_or_generated(self) -> None:
        sanitized = self.client.get(
            "/health/live/",
            HTTP_X_REQUEST_ID=" trace value! ",
        )
        generated = self.client.get("/health/live/", HTTP_X_REQUEST_ID="!!!")

        self.assertEqual(sanitized["X-Request-ID"], "tracevalue")
        uuid.UUID(generated["X-Request-ID"])

    def test_health_endpoints_reject_unsupported_methods_as_json(self) -> None:
        for path in ("/", "/health/live/", "/health/ready/"):
            with self.subTest(path=path):
                response = self.client.post(path, {}, format="json")
                self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
                self.assertEqual(response["Content-Type"], "application/json")
                self.assertEqual(response.json()["error"]["code"], "method_not_allowed")

    @patch("config.health.connection.cursor", side_effect=RuntimeError("database down"))
    def test_readiness_reports_database_failure(self, _cursor) -> None:
        response = self.client.get("/health/ready/")

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(response.json(), {"status": "unavailable", "database": "down"})

    def test_openapi_schema_is_public_json(self) -> None:
        response = self.client.get("/api/schema/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("json", response["Content-Type"])
        self.assertEqual(response.json()["info"]["title"], "Lacrei Saúde - API de Consultas")

    def test_unknown_api_route_is_json(self) -> None:
        response = self.client.get("/api/v1/does-not-exist/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertEqual(response.json()["error"]["code"], "not_found")


class ErrorAndMiddlewareTests(APITestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()

    def test_unhandled_api_exception_is_hidden(self) -> None:
        request = self.factory.get("/api/v1/failure/")
        request.request_id = "error-trace"

        with self.assertLogs("config.exceptions", level="ERROR"):
            response = api_exception_handler(RuntimeError("sensitive detail"), {"request": request})

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.data["error"]["code"], "internal_error")
        self.assertNotIn("sensitive detail", str(response.data))

    def test_plain_django_error_handlers_return_json(self) -> None:
        request = self.factory.get("/broken/")
        request.request_id = "handler-trace"

        bad_request = json_bad_request(request)
        with self.assertLogs("config.exceptions", level="ERROR"):
            server_error = json_server_error(request)

        self.assertEqual(bad_request.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(server_error.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(
            json.loads(bad_request.content)["error"]["request_id"],
            "handler-trace",
        )
        self.assertEqual(
            json.loads(server_error.content)["error"]["request_id"],
            "handler-trace",
        )

    def test_access_log_middleware_logs_and_reraises_exception(self) -> None:
        request = self.factory.get("/explode/")

        def explode(_request):
            raise RuntimeError("boom")

        middleware = AccessLogMiddleware(explode)
        with (
            patch("config.middleware.access_logger.exception") as log_exception,
            self.assertRaises(RuntimeError),
        ):
            middleware(request)

        log_exception.assert_called_once()

    def test_access_log_middleware_accepts_plain_response(self) -> None:
        request = self.factory.get("/ok/")
        middleware = AccessLogMiddleware(lambda _request: HttpResponse(status=204))

        response = middleware(request)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        uuid.UUID(response["X-Request-ID"])

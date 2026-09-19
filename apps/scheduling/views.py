from __future__ import annotations

import uuid

from django.db import IntegrityError
from django.db.models.deletion import ProtectedError
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .models import Appointment, Professional
from .serializers import AppointmentSerializer, ProfessionalSerializer


@extend_schema_view(
    list=extend_schema(description="Lista profissionais de saúde."),
    create=extend_schema(description="Cadastra uma pessoa profissional de saúde."),
    retrieve=extend_schema(description="Obtém uma pessoa profissional pelo UUID."),
    update=extend_schema(description="Substitui os dados de uma pessoa profissional."),
    partial_update=extend_schema(
        description="Atualiza parte dos dados de uma pessoa profissional."
    ),
    destroy=extend_schema(description="Exclui uma pessoa profissional sem consultas vinculadas."),
)
class ProfessionalViewSet(viewsets.ModelViewSet):
    queryset = Professional.objects.all()
    serializer_class = ProfessionalSerializer

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            self.perform_destroy(instance)
        except ProtectedError:
            return Response(
                {
                    "error": {
                        "code": "professional_has_appointments",
                        "message": (
                            "Não é possível excluir um profissional com consultas vinculadas."
                        ),
                        "details": {"appointments": instance.appointments.count()},
                        "request_id": getattr(request, "request_id", None),
                    }
                },
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        description="Lista as consultas vinculadas a uma pessoa profissional.",
        responses={200: AppointmentSerializer(many=True)},
    )
    @action(detail=True, methods=["get"], url_path="appointments")
    def appointments(self, request, pk=None):
        professional = self.get_object()
        queryset = professional.appointments.select_related("professional").all()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = AppointmentSerializer(page, many=True, context={"request": request})
            return self.get_paginated_response(serializer.data)
        return Response(AppointmentSerializer(queryset, many=True).data)


@extend_schema_view(
    list=extend_schema(
        description="Lista consultas; filtre por professional ou professional_id.",
        parameters=[
            OpenApiParameter(
                name="professional",
                type=uuid.UUID,
                location=OpenApiParameter.QUERY,
                description="UUID da pessoa profissional.",
                required=False,
            ),
            OpenApiParameter(
                name="professional_id",
                type=uuid.UUID,
                location=OpenApiParameter.QUERY,
                description="Alias para professional.",
                required=False,
            ),
        ],
    ),
    create=extend_schema(description="Agenda uma consulta futura."),
    retrieve=extend_schema(description="Obtém uma consulta pelo UUID."),
    update=extend_schema(description="Substitui os dados de uma consulta."),
    partial_update=extend_schema(description="Atualiza parte de uma consulta."),
    destroy=extend_schema(description="Exclui uma consulta."),
)
class AppointmentViewSet(viewsets.ModelViewSet):
    queryset = Appointment.objects.select_related("professional").all()
    serializer_class = AppointmentSerializer

    def perform_create(self, serializer):
        try:
            serializer.save()
        except IntegrityError:
            raise ValidationError(
                {"date": "Esse profissional já possui uma consulta nesse horário."}
            ) from None

    def perform_update(self, serializer):
        try:
            serializer.save()
        except IntegrityError:
            raise ValidationError(
                {"date": "Esse profissional já possui uma consulta nesse horário."}
            ) from None

    def get_queryset(self):
        queryset = super().get_queryset()
        professional_id = self.request.query_params.get(
            "professional", self.request.query_params.get("professional_id")
        )
        if not professional_id:
            return queryset
        try:
            parsed_id = uuid.UUID(professional_id)
        except (ValueError, TypeError, AttributeError):
            raise ValidationError({"professional": "Informe um UUID válido."}) from None
        return queryset.filter(professional_id=parsed_id)

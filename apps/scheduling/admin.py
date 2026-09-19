from django.contrib import admin

from .models import Appointment, Professional


@admin.register(Professional)
class ProfessionalAdmin(admin.ModelAdmin):
    list_display = ("social_name", "profession", "contact", "created_at")
    search_fields = ("social_name", "profession", "contact")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("date", "professional", "created_at")
    list_filter = ("date",)
    search_fields = ("professional__social_name",)
    autocomplete_fields = ("professional",)
    readonly_fields = ("id", "created_at", "updated_at")

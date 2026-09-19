from rest_framework.routers import DefaultRouter

from .views import AppointmentViewSet, ProfessionalViewSet

app_name = "scheduling"
router = DefaultRouter()
router.register("professionals", ProfessionalViewSet, basename="professional")
router.register("appointments", AppointmentViewSet, basename="appointment")

urlpatterns = router.urls

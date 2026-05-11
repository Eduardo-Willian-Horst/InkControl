from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AppointmentChangeRequestViewSet,
    AppointmentViewSet,
    ClientHealthFormViewSet,
    ClientViewSet,
    InAppNotificationViewSet,
    LinkTattooerProfileView,
    LoginView,
    LogoutView,
    MeView,
    RegisterView,
    StudioSettingsView,
    TattooerViewSet,
    health,
)

router = DefaultRouter()
router.register("clients", ClientViewSet, basename="client")
router.register("tattooers", TattooerViewSet, basename="tattooer")
router.register("appointments", AppointmentViewSet, basename="appointment")
router.register(
    "appointment-change-requests",
    AppointmentChangeRequestViewSet,
    basename="appointment-change-request",
)
router.register("notifications", InAppNotificationViewSet, basename="notification")
router.register("health-forms", ClientHealthFormViewSet, basename="health-form")

urlpatterns = [
    path("health/", health, name="health"),
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/me/", MeView.as_view(), name="me"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/link-tattooer-profile/", LinkTattooerProfileView.as_view(), name="link-tattooer-profile"),
    path("studio-settings/", StudioSettingsView.as_view(), name="studio-settings"),
    path("", include(router.urls)),
]

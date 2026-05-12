from django.db.models import Q
from rest_framework import permissions, viewsets

from studio.models import Appointment, Client, UserProfile
from studio.permissions import RoleByActionPermission, get_user_role
from studio.serializers import ClientSerializer


class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    permission_classes = [permissions.IsAuthenticated, RoleByActionPermission]
    role_permissions = {
        "list": {UserProfile.ROLE_STUDIO, UserProfile.ROLE_TATTOOER},
        "retrieve": {UserProfile.ROLE_STUDIO, UserProfile.ROLE_TATTOOER},
        "create": {UserProfile.ROLE_STUDIO},
        "update": {UserProfile.ROLE_STUDIO},
        "partial_update": {UserProfile.ROLE_STUDIO},
        "destroy": {UserProfile.ROLE_STUDIO},
    }

    def perform_destroy(self, instance):
        from rest_framework.exceptions import ValidationError

        if instance.appointments.exclude(status=Appointment.STATUS_CANCELLED).exists():
            raise ValidationError(
                "Nao e possivel excluir cliente com agendamentos que nao estejam cancelados."
            )
        super().perform_destroy(instance)

    def get_queryset(self):
        queryset = super().get_queryset()
        q = self.request.query_params.get("q")
        is_active = self.request.query_params.get("is_active")

        if q:
            queryset = queryset.filter(
                Q(name__icontains=q) | Q(phone__icontains=q) | Q(email__icontains=q)
            )
        if is_active in {"true", "false"}:
            queryset = queryset.filter(is_active=(is_active == "true"))

        if get_user_role(self.request.user) == UserProfile.ROLE_TATTOOER:
            profile, _ = UserProfile.objects.select_related("tattooer").get_or_create(
                user=self.request.user
            )
            if profile.tattooer_id:
                queryset = queryset.filter(
                    appointments__tattooer_id=profile.tattooer_id
                ).distinct()
            else:
                queryset = queryset.none()
        return queryset


__all__ = ["ClientViewSet"]

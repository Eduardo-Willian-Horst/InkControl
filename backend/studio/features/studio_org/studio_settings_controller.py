from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from studio.models import StudioSettings, UserProfile
from studio.permissions import get_user_role
from studio.serializers import StudioSettingsSerializer


class StudioSettingsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        obj = StudioSettings.get_solo()
        return Response(StudioSettingsSerializer(obj).data)

    def patch(self, request):
        if get_user_role(request.user) != UserProfile.ROLE_STUDIO:
            return Response(status=status.HTTP_403_FORBIDDEN)
        obj = StudioSettings.get_solo()
        serializer = StudioSettingsSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


__all__ = ["StudioSettingsView"]

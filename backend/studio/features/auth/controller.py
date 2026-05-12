from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework import permissions, status
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from studio.models import Tattooer, UserProfile
from studio.permissions import get_user_role
from studio.serializers import LoginSerializer, RegisterSerializer

from .utils import get_or_create_client_for_app_user, serialize_auth_user


class RegisterThrottle(AnonRateThrottle):
    rate = "20/hour"


class LoginThrottle(AnonRateThrottle):
    rate = "30/hour"


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [RegisterThrottle]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {
                "token": token.key,
                "user": serialize_auth_user(user),
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [LoginThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"].lower()
        password = serializer.validated_data["password"]

        try:
            user_obj = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return Response(
                {"detail": "Credenciais invalidas."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate(username=user_obj.username, password=password)
        if user is None:
            return Response(
                {"detail": "Credenciais invalidas."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        token, _ = Token.objects.get_or_create(user=user)
        UserProfile.objects.get_or_create(user=user)
        return Response(
            {
                "token": token.key,
                "user": serialize_auth_user(user),
            }
        )


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(serialize_auth_user(request.user))

    def patch(self, request):
        profile, _ = UserProfile.objects.select_related("tattooer").get_or_create(
            user=request.user
        )
        if get_user_role(request.user) != UserProfile.ROLE_TATTOOER:
            return Response(
                {"detail": "Apenas perfil tatuador pode atualizar este campo."},
                status=status.HTTP_403_FORBIDDEN,
            )
        tid = request.data.get("tattooer")
        if tid in (None, ""):
            profile.tattooer = None
        else:
            try:
                tattooer = Tattooer.objects.get(pk=int(tid))
            except (ValueError, Tattooer.DoesNotExist):
                return Response(
                    {"detail": "Tatuador invalido."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            profile.tattooer = tattooer
        profile.save()
        return Response(serialize_auth_user(request.user))


class LinkTattooerProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if get_user_role(request.user) != UserProfile.ROLE_STUDIO:
            return Response(status=status.HTTP_403_FORBIDDEN)
        uid = request.data.get("user_id")
        tattooer_id = request.data.get("tattooer_id")
        try:
            target = User.objects.get(pk=int(uid))
            tattooer = Tattooer.objects.get(pk=int(tattooer_id))
        except (TypeError, ValueError, User.DoesNotExist, Tattooer.DoesNotExist):
            return Response(
                {"detail": "Usuario ou tatuador invalido."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        profile, _ = UserProfile.objects.get_or_create(user=target)
        if profile.role != UserProfile.ROLE_TATTOOER:
            return Response(
                {"detail": "O usuario precisa ter papel tatuador."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        profile.tattooer = tattooer
        profile.save()
        return Response({"user": serialize_auth_user(target)})


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


__all__ = [
    "RegisterView",
    "LoginView",
    "MeView",
    "LinkTattooerProfileView",
    "LogoutView",
]

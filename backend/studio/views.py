from datetime import datetime, time, timedelta

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from .booking_utils import (
    apply_accepted_change_request,
    can_respond_to_change_request,
    notify_change_request_created,
    user_appointment_scope_queryset,
)
from .models import (
    Appointment,
    AppointmentChangeRequest,
    Client,
    ClientHealthForm,
    InAppNotification,
    StudioSettings,
    Tattooer,
    UserProfile,
)
from .serializers import (
    AppointmentChangeRequestSerializer,
    AppointmentReadSerializer,
    AppointmentSerializer,
    ClientHealthFormSerializer,
    ClientSerializer,
    InAppNotificationSerializer,
    LoginSerializer,
    RegisterSerializer,
    StudioSettingsSerializer,
    TattooerSerializer,
)
from .permissions import RoleByActionPermission, get_user_role


def get_or_create_client_for_app_user(user):
    email = (user.email or "").strip().lower()
    if not email:
        return None
    found = Client.objects.filter(email__iexact=email).first()
    if found:
        return found
    name = (user.first_name or "").strip() or email.split("@")[0]
    try:
        return Client.objects.create(
            name=name[:120],
            email=email,
            phone="Nao informado",
            is_active=True,
        )
    except IntegrityError:
        return Client.objects.filter(email__iexact=email).first()


def serialize_auth_user(user):
    profile, _ = UserProfile.objects.select_related("tattooer").get_or_create(user=user)
    email = (user.email or "").strip()
    client = None
    if email:
        if profile.role == UserProfile.ROLE_CLIENT:
            client = get_or_create_client_for_app_user(user)
        else:
            client = Client.objects.filter(email__iexact=email.strip().lower()).first()
    unread = InAppNotification.objects.filter(user=user, read=False).count()
    return {
        "id": user.id,
        "name": user.first_name,
        "email": user.email,
        "role": profile.role,
        "client_id": client.id if client else None,
        "tattooer_id": profile.tattooer_id,
        "tattooer_linked": bool(profile.tattooer_id),
        "unread_notifications": unread,
    }


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def health(request):
    return Response({"status": "ok", "service": "inkcontrol-api"})


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

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


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


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


class TattooerViewSet(viewsets.ModelViewSet):
    queryset = Tattooer.objects.all()
    serializer_class = TattooerSerializer
    permission_classes = [permissions.IsAuthenticated, RoleByActionPermission]
    role_permissions = {
        "list": {
            UserProfile.ROLE_STUDIO,
            UserProfile.ROLE_TATTOOER,
            UserProfile.ROLE_CLIENT,
        },
        "retrieve": {
            UserProfile.ROLE_STUDIO,
            UserProfile.ROLE_TATTOOER,
            UserProfile.ROLE_CLIENT,
        },
        "create": {UserProfile.ROLE_STUDIO},
        "update": {UserProfile.ROLE_STUDIO},
        "partial_update": {UserProfile.ROLE_STUDIO},
        "destroy": {UserProfile.ROLE_STUDIO},
    }

    def get_queryset(self):
        queryset = super().get_queryset()
        q = self.request.query_params.get("q")
        is_active = self.request.query_params.get("is_active")

        if q:
            queryset = queryset.filter(
                Q(name__icontains=q)
                | Q(artistic_style__icontains=q)
                | Q(contact__icontains=q)
            )
        if is_active in {"true", "false"}:
            queryset = queryset.filter(is_active=(is_active == "true"))
        return queryset


class AppointmentViewSet(viewsets.ModelViewSet):
    queryset = Appointment.objects.select_related("client", "tattooer", "client__health_form")
    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated, RoleByActionPermission]
    role_permissions = {
        "list": {
            UserProfile.ROLE_STUDIO,
            UserProfile.ROLE_TATTOOER,
            UserProfile.ROLE_CLIENT,
        },
        "retrieve": {
            UserProfile.ROLE_STUDIO,
            UserProfile.ROLE_TATTOOER,
            UserProfile.ROLE_CLIENT,
        },
        "create": {UserProfile.ROLE_STUDIO, UserProfile.ROLE_CLIENT},
        "update": {
            UserProfile.ROLE_STUDIO,
            UserProfile.ROLE_TATTOOER,
            UserProfile.ROLE_CLIENT,
        },
        "partial_update": {
            UserProfile.ROLE_STUDIO,
            UserProfile.ROLE_TATTOOER,
            UserProfile.ROLE_CLIENT,
        },
        "destroy": {UserProfile.ROLE_STUDIO},
        "cancel": {
            UserProfile.ROLE_STUDIO,
            UserProfile.ROLE_TATTOOER,
            UserProfile.ROLE_CLIENT,
        },
    }

    def get_serializer_class(self):
        if getattr(self, "action", None) in ("list", "retrieve"):
            return AppointmentReadSerializer
        return AppointmentSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        if getattr(self, "action", None) == "create" and self.request.user.is_authenticated:
            ctx["client_booking"] = get_user_role(self.request.user) == UserProfile.ROLE_CLIENT
        return ctx

    def perform_create(self, serializer):
        if get_user_role(self.request.user) == UserProfile.ROLE_CLIENT:
            client = get_or_create_client_for_app_user(self.request.user)
            serializer.save(client=client)
        else:
            serializer.save()

    def perform_update(self, serializer):
        if get_user_role(self.request.user) == UserProfile.ROLE_CLIENT:
            client = get_or_create_client_for_app_user(self.request.user)
            serializer.save(client=client)
        else:
            serializer.save()

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        appointment = self.get_object()
        if not Appointment.can_transition(appointment.status, Appointment.STATUS_CANCELLED):
            return Response(
                {"detail": "Nao e possivel cancelar este agendamento."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        appointment.status = Appointment.STATUS_CANCELLED
        appointment.save(update_fields=["status", "updated_at"])
        serializer = AppointmentReadSerializer(appointment, context={"request": request})
        return Response(serializer.data)

    def get_queryset(self):
        queryset = super().get_queryset()
        q = self.request.query_params.get("q")
        status_filter = self.request.query_params.get("status")
        tattooer_filter = self.request.query_params.get("tattooer")
        client_filter = self.request.query_params.get("client")
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")
        period = self.request.query_params.get("period")
        base_date_raw = self.request.query_params.get("date")
        kind = self.request.query_params.get("appointment_kind")

        if kind in (Appointment.KIND_SERVICE, Appointment.KIND_CONSULTATION):
            queryset = queryset.filter(appointment_kind=kind)

        if q:
            queryset = queryset.filter(
                Q(description__icontains=q)
                | Q(client__name__icontains=q)
                | Q(tattooer__name__icontains=q)
            )
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if tattooer_filter and tattooer_filter.isdigit():
            queryset = queryset.filter(tattooer_id=int(tattooer_filter))
        if client_filter and client_filter.isdigit():
            if get_user_role(self.request.user) != UserProfile.ROLE_CLIENT:
                queryset = queryset.filter(client_id=int(client_filter))
        if date_from:
            parsed_from = parse_date(date_from)
            if parsed_from:
                tz = timezone.get_current_timezone()
                start_from = timezone.make_aware(datetime.combine(parsed_from, time.min), tz)
                queryset = queryset.filter(scheduled_at__gte=start_from)
        if date_to:
            parsed_to = parse_date(date_to)
            if parsed_to:
                tz = timezone.get_current_timezone()
                end_to = timezone.make_aware(
                    datetime.combine(parsed_to + timedelta(days=1), time.min), tz
                )
                queryset = queryset.filter(scheduled_at__lt=end_to)

        if period:
            base_date = parse_date(base_date_raw) if base_date_raw else timezone.localdate()
            if base_date is None:
                queryset = queryset.none()
            elif period == "day":
                start_date = base_date
                end_date = base_date + timedelta(days=1)
                tz = timezone.get_current_timezone()
                start_dt = timezone.make_aware(datetime.combine(start_date, time.min), tz)
                end_dt = timezone.make_aware(datetime.combine(end_date, time.min), tz)
                queryset = queryset.filter(scheduled_at__gte=start_dt, scheduled_at__lt=end_dt)
            elif period == "week":
                start_date = base_date - timedelta(days=base_date.weekday())
                end_date = start_date + timedelta(days=7)
                tz = timezone.get_current_timezone()
                start_dt = timezone.make_aware(datetime.combine(start_date, time.min), tz)
                end_dt = timezone.make_aware(datetime.combine(end_date, time.min), tz)
                queryset = queryset.filter(scheduled_at__gte=start_dt, scheduled_at__lt=end_dt)
            elif period == "month":
                start_date = base_date.replace(day=1)
                if start_date.month == 12:
                    end_date = start_date.replace(year=start_date.year + 1, month=1)
                else:
                    end_date = start_date.replace(month=start_date.month + 1)
                tz = timezone.get_current_timezone()
                start_dt = timezone.make_aware(datetime.combine(start_date, time.min), tz)
                end_dt = timezone.make_aware(datetime.combine(end_date, time.min), tz)
                queryset = queryset.filter(scheduled_at__gte=start_dt, scheduled_at__lt=end_dt)

        role = get_user_role(self.request.user)
        if role == UserProfile.ROLE_TATTOOER:
            profile, _ = UserProfile.objects.select_related("tattooer").get_or_create(
                user=self.request.user
            )
            if not profile.tattooer_id:
                queryset = queryset.none()
            else:
                queryset = queryset.filter(tattooer_id=profile.tattooer_id)
        elif role == UserProfile.ROLE_CLIENT:
            email = (self.request.user.email or "").strip()
            if email:
                queryset = queryset.filter(client__email__iexact=email)
            else:
                queryset = queryset.none()

        return queryset


class AppointmentChangeRequestViewSet(viewsets.ModelViewSet):
    http_method_names = ["get", "post", "head", "options"]
    queryset = AppointmentChangeRequest.objects.select_related(
        "appointment", "appointment__client", "appointment__tattooer", "requested_by"
    )
    serializer_class = AppointmentChangeRequestSerializer
    permission_classes = [permissions.IsAuthenticated, RoleByActionPermission]
    role_permissions = {
        "list": {
            UserProfile.ROLE_STUDIO,
            UserProfile.ROLE_TATTOOER,
            UserProfile.ROLE_CLIENT,
        },
        "retrieve": {
            UserProfile.ROLE_STUDIO,
            UserProfile.ROLE_TATTOOER,
            UserProfile.ROLE_CLIENT,
        },
        "create": {
            UserProfile.ROLE_STUDIO,
            UserProfile.ROLE_TATTOOER,
            UserProfile.ROLE_CLIENT,
        },
        "accept": {
            UserProfile.ROLE_STUDIO,
            UserProfile.ROLE_TATTOOER,
            UserProfile.ROLE_CLIENT,
        },
        "reject": {
            UserProfile.ROLE_STUDIO,
            UserProfile.ROLE_TATTOOER,
            UserProfile.ROLE_CLIENT,
        },
    }

    def get_queryset(self):
        scope = user_appointment_scope_queryset(self.request.user)
        qs = self.queryset.filter(appointment__in=scope)
        aid = self.request.query_params.get("appointment")
        if aid and aid.isdigit():
            qs = qs.filter(appointment_id=int(aid))
        return qs

    def perform_create(self, serializer):
        cr = serializer.save(requested_by=self.request.user)
        notify_change_request_created(cr)

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        cr = self.get_object()
        if not can_respond_to_change_request(request.user, cr):
            return Response(
                {"detail": "Sem permissao para aceitar esta solicitacao."},
                status=status.HTTP_403_FORBIDDEN,
            )
        appt_id = cr.appointment_id
        with transaction.atomic():
            try:
                apply_accepted_change_request(cr, request)
            except ValueError as exc:
                return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
            except serializers.ValidationError as exc:
                return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)
            cr.status = AppointmentChangeRequest.STATUS_ACCEPTED
            cr.save(update_fields=["status", "updated_at"])
            AppointmentChangeRequest.objects.filter(
                appointment_id=appt_id, status=AppointmentChangeRequest.STATUS_PENDING
            ).exclude(pk=cr.pk).update(status=AppointmentChangeRequest.STATUS_REJECTED)
        appt = Appointment.objects.select_related("client", "tattooer", "client__health_form").get(
            pk=appt_id
        )
        out = AppointmentReadSerializer(appt, context={"request": request})
        return Response({"appointment": out.data, "change_request": {"id": cr.id, "status": cr.status}})

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        cr = self.get_object()
        if not can_respond_to_change_request(request.user, cr):
            return Response(
                {"detail": "Sem permissao para recusar esta solicitacao."},
                status=status.HTTP_403_FORBIDDEN,
            )
        cr.status = AppointmentChangeRequest.STATUS_REJECTED
        cr.save(update_fields=["status", "updated_at"])
        return Response(
            AppointmentChangeRequestSerializer(cr, context={"request": request}).data
        )


class InAppNotificationViewSet(viewsets.ModelViewSet):
    queryset = InAppNotification.objects.all()
    http_method_names = ["get", "patch", "head", "options"]
    serializer_class = InAppNotificationSerializer
    permission_classes = [permissions.IsAuthenticated, RoleByActionPermission]
    role_permissions = {
        "list": {
            UserProfile.ROLE_STUDIO,
            UserProfile.ROLE_TATTOOER,
            UserProfile.ROLE_CLIENT,
        },
        "retrieve": {
            UserProfile.ROLE_STUDIO,
            UserProfile.ROLE_TATTOOER,
            UserProfile.ROLE_CLIENT,
        },
        "partial_update": {
            UserProfile.ROLE_STUDIO,
            UserProfile.ROLE_TATTOOER,
            UserProfile.ROLE_CLIENT,
        },
    }

    def get_queryset(self):
        return InAppNotification.objects.filter(user=self.request.user)


class ClientHealthFormViewSet(viewsets.ModelViewSet):
    queryset = ClientHealthForm.objects.select_related("client").all()
    serializer_class = ClientHealthFormSerializer
    permission_classes = [permissions.IsAuthenticated, RoleByActionPermission]
    role_permissions = {
        "list": {
            UserProfile.ROLE_STUDIO,
            UserProfile.ROLE_TATTOOER,
            UserProfile.ROLE_CLIENT,
        },
        "retrieve": {
            UserProfile.ROLE_STUDIO,
            UserProfile.ROLE_TATTOOER,
            UserProfile.ROLE_CLIENT,
        },
        "create": {UserProfile.ROLE_STUDIO, UserProfile.ROLE_CLIENT},
        "update": {UserProfile.ROLE_STUDIO, UserProfile.ROLE_CLIENT},
        "partial_update": {UserProfile.ROLE_STUDIO, UserProfile.ROLE_CLIENT},
        "destroy": {UserProfile.ROLE_STUDIO},
    }

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        if getattr(self, "action", None) == "create" and self.request.user.is_authenticated:
            ctx["client_health_booking"] = (
                get_user_role(self.request.user) == UserProfile.ROLE_CLIENT
            )
        return ctx

    def perform_create(self, serializer):
        if get_user_role(self.request.user) == UserProfile.ROLE_CLIENT:
            client = get_or_create_client_for_app_user(self.request.user)
            serializer.save(client=client)
        else:
            serializer.save()

    def perform_update(self, serializer):
        if get_user_role(self.request.user) == UserProfile.ROLE_CLIENT:
            client = get_or_create_client_for_app_user(self.request.user)
            serializer.save(client=client)
        else:
            serializer.save()

    def get_queryset(self):
        queryset = super().get_queryset()
        client_filter = self.request.query_params.get("client")
        q = self.request.query_params.get("q")
        if client_filter and client_filter.isdigit():
            if get_user_role(self.request.user) != UserProfile.ROLE_CLIENT:
                queryset = queryset.filter(client_id=int(client_filter))
        if q:
            queryset = queryset.filter(
                Q(client__name__icontains=q)
                | Q(allergies__icontains=q)
                | Q(chronic_diseases__icontains=q)
                | Q(healing_history__icontains=q)
            )
        if get_user_role(self.request.user) == UserProfile.ROLE_CLIENT:
            email = (self.request.user.email or "").strip()
            if email:
                queryset = queryset.filter(client__email__iexact=email)
        elif get_user_role(self.request.user) == UserProfile.ROLE_TATTOOER:
            profile, _ = UserProfile.objects.select_related("tattooer").get_or_create(
                user=self.request.user
            )
            if profile.tattooer_id:
                queryset = queryset.filter(
                    client__appointments__tattooer_id=profile.tattooer_id
                ).distinct()
            else:
                queryset = queryset.none()
        return queryset

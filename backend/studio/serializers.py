from django.contrib.auth.models import User
from django.utils.dateparse import parse_datetime
from rest_framework import serializers

from .booking_utils import (
    appointment_intervals_overlap,
    can_respond_to_change_request,
    user_appointment_scope_queryset,
    validate_scheduled_within_studio_hours,
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
from .permissions import get_user_role


class RegisterSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    role = serializers.ChoiceField(
        choices=[UserProfile.ROLE_CLIENT, UserProfile.ROLE_TATTOOER, UserProfile.ROLE_STUDIO],
        default=UserProfile.ROLE_CLIENT,
    )

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Este e-mail ja esta em uso.")
        return value.lower()

    def create(self, validated_data):
        email = validated_data["email"]
        user = User.objects.create_user(
            username=email,
            first_name=validated_data["name"],
            email=email,
            password=validated_data["password"],
        )
        UserProfile.objects.create(user=user, role=validated_data["role"])
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = [
            "id",
            "name",
            "phone",
            "email",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class TattooerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tattooer
        fields = [
            "id",
            "name",
            "artistic_style",
            "contact",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ClientBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ["id", "name", "phone", "email"]


class TattooerBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tattooer
        fields = ["id", "name", "artistic_style", "contact"]


class AppointmentReadSerializer(serializers.ModelSerializer):
    client = ClientBriefSerializer(read_only=True)
    tattooer = TattooerBriefSerializer(read_only=True)
    reference_image = serializers.SerializerMethodField()
    health_summary = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = [
            "id",
            "client",
            "tattooer",
            "scheduled_at",
            "description",
            "status",
            "appointment_kind",
            "duration_minutes",
            "reference_image",
            "health_summary",
            "created_at",
            "updated_at",
        ]

    def get_reference_image(self, obj):
        if not obj.reference_image:
            return None
        request = self.context.get("request")
        url = obj.reference_image.url
        if request:
            return request.build_absolute_uri(url)
        return url

    def get_health_summary(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        role = get_user_role(request.user)
        if role not in (UserProfile.ROLE_STUDIO, UserProfile.ROLE_TATTOOER):
            return None
        hf = getattr(obj.client, "health_form", None)
        if hf is None:
            return None
        allergies = (hf.allergies or "").strip()
        chronic = (hf.chronic_diseases or "").strip()
        return {
            "allergies_preview": allergies[:280],
            "chronic_diseases_preview": chronic[:280],
            "has_alerts": bool(allergies or chronic),
        }


AGENDA_FIELD_NAMES = frozenset(
    {
        "scheduled_at",
        "description",
        "appointment_kind",
        "tattooer",
        "client",
        "reference_image",
        "duration_minutes",
    }
)


class AppointmentSerializer(serializers.ModelSerializer):
    MAX_IMAGE_BYTES = 5 * 1024 * 1024

    class Meta:
        model = Appointment
        fields = [
            "id",
            "client",
            "tattooer",
            "scheduled_at",
            "description",
            "status",
            "appointment_kind",
            "duration_minutes",
            "reference_image",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        extra_kwargs = {
            "reference_image": {"required": False},
            "description": {"required": False},
            "appointment_kind": {"required": False},
            "duration_minutes": {"required": False},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        ctx = self.context or {}
        if self.instance is None and ctx.get("client_booking"):
            self.fields["client"].required = False

    def validate_reference_image(self, value):
        if not value:
            return value
        if value.size > self.MAX_IMAGE_BYTES:
            raise serializers.ValidationError("Arquivo muito grande (maximo 5MB).")
        ctype = getattr(value, "content_type", "") or ""
        if ctype and ctype not in {"image/jpeg", "image/png", "image/webp"}:
            raise serializers.ValidationError("Formato aceito: JPEG, PNG ou WebP.")
        return value

    def validate(self, attrs):
        request = self.context.get("request")
        if (
            request
            and self.instance
            and not self.context.get("applying_change_request_accept")
        ):
            role = get_user_role(request.user)
            if role in (UserProfile.ROLE_CLIENT, UserProfile.ROLE_TATTOOER):
                touched = AGENDA_FIELD_NAMES.intersection(attrs.keys())
                if touched:
                    raise serializers.ValidationError(
                        {
                            k: (
                                "Alteracao sujeita a aceite: envie uma solicitacao em "
                                "/api/appointment-change-requests/."
                            )
                            for k in sorted(touched)
                        }
                    )

        if self.instance and "status" in attrs:
            next_status = attrs["status"]
            if not Appointment.can_transition(self.instance.status, next_status):
                raise serializers.ValidationError(
                    {
                        "status": (
                            f"Transicao invalida de '{self.instance.status}' "
                            f"para '{next_status}'."
                        )
                    }
                )

        tattooer = attrs.get("tattooer", getattr(self.instance, "tattooer", None))
        scheduled_at = attrs.get("scheduled_at", getattr(self.instance, "scheduled_at", None))
        duration = attrs.get("duration_minutes", getattr(self.instance, "duration_minutes", None))
        if duration is None:
            duration = 60

        if tattooer is not None and scheduled_at is not None:
            try:
                validate_scheduled_within_studio_hours(scheduled_at)
            except ValueError as exc:
                raise serializers.ValidationError({"scheduled_at": str(exc)}) from exc

        if tattooer is None or scheduled_at is None:
            return attrs

        conflict_query = Appointment.objects.filter(tattooer=tattooer).exclude(
            status=Appointment.STATUS_CANCELLED
        )
        if self.instance:
            conflict_query = conflict_query.exclude(pk=self.instance.pk)

        for other in conflict_query.only("scheduled_at", "duration_minutes"):
            od = other.duration_minutes or 60
            if appointment_intervals_overlap(
                scheduled_at, duration, other.scheduled_at, od
            ):
                raise serializers.ValidationError(
                    {
                        "scheduled_at": (
                            "Conflito de horario com outra sessao deste tatuador "
                            "(intervalos sobrepostos)."
                        )
                    }
                )

        return attrs


class ClientHealthFormSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientHealthForm
        fields = [
            "id",
            "client",
            "allergies",
            "chronic_diseases",
            "healing_history",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        ctx = self.context or {}
        if self.instance is None and ctx.get("client_health_booking"):
            self.fields["client"].required = False


class StudioSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudioSettings
        fields = ["id", "opens_at", "closes_at"]
        read_only_fields = ["id"]


CHANGE_REQUEST_ALLOWED_KEYS = frozenset(
    {
        "scheduled_at",
        "description",
        "appointment_kind",
        "tattooer",
        "clear_reference_image",
        "duration_minutes",
    }
)


class AppointmentChangeRequestSerializer(serializers.ModelSerializer):
    requested_by_display = serializers.SerializerMethodField()
    you_requested = serializers.SerializerMethodField()
    can_respond = serializers.SerializerMethodField()
    proposed_changes = serializers.DictField(required=False, allow_empty=True, write_only=True)
    proposed_summary = serializers.SerializerMethodField()
    proposed_reference_image_url = serializers.SerializerMethodField()

    class Meta:
        model = AppointmentChangeRequest
        fields = [
            "id",
            "appointment",
            "requested_by_display",
            "you_requested",
            "can_respond",
            "proposed_scheduled_at",
            "proposed_payload",
            "proposed_changes",
            "proposed_summary",
            "proposed_reference_image",
            "proposed_reference_image_url",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "requested_by_display",
            "you_requested",
            "can_respond",
            "proposed_summary",
            "proposed_reference_image_url",
            "proposed_payload",
            "status",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {
            "appointment": {"required": True},
            "proposed_scheduled_at": {"required": False, "allow_null": True},
            "proposed_reference_image": {"required": False, "allow_null": True},
        }

    def get_requested_by_display(self, obj):
        u = obj.requested_by
        name = (u.first_name or "").strip()
        email = (u.email or "").strip()
        if name and email:
            return f"{name} ({email})"
        return email or name or ""

    def get_you_requested(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return obj.requested_by_id == request.user.id

    def get_can_respond(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return can_respond_to_change_request(request.user, obj)

    def get_proposed_summary(self, obj):
        parts = []
        payload = obj.proposed_payload or {}
        if payload.get("scheduled_at"):
            parts.append("Data/hora")
        if "description" in payload:
            parts.append("Descricao")
        if "appointment_kind" in payload:
            parts.append("Modalidade")
        if "tattooer" in payload:
            parts.append("Tatuador")
        if "duration_minutes" in payload:
            parts.append("Duracao")
        if payload.get("clear_reference_image"):
            parts.append("Remover imagem")
        if obj.proposed_reference_image:
            parts.append("Nova imagem")
        return ", ".join(parts) if parts else "Alteracao"

    def get_proposed_reference_image_url(self, obj):
        if not obj.proposed_reference_image:
            return None
        request = self.context.get("request")
        url = obj.proposed_reference_image.url
        if request:
            return request.build_absolute_uri(url)
        return url

    def validate_appointment(self, appointment):
        ctx = self.context or {}
        request = ctx.get("request")
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("Sessao invalida.")
        if not user_appointment_scope_queryset(request.user).filter(pk=appointment.pk).exists():
            raise serializers.ValidationError("Agendamento nao encontrado ou sem permissao.")
        return appointment

    def validate(self, attrs):
        appointment = attrs.get("appointment") or getattr(self.instance, "appointment", None)
        if appointment is None:
            raise serializers.ValidationError({"appointment": "Obrigatorio."})

        changes = dict(attrs.pop("proposed_changes", {}) or {})
        legacy_dt = attrs.pop("proposed_scheduled_at", None)
        if legacy_dt is not None:
            changes["scheduled_at"] = legacy_dt.isoformat()

        unknown = set(changes.keys()) - CHANGE_REQUEST_ALLOWED_KEYS
        if unknown:
            raise serializers.ValidationError(
                {"proposed_changes": f"Campos nao permitidos: {', '.join(sorted(unknown))}."}
            )

        ref_file = attrs.get("proposed_reference_image")
        if not changes and not ref_file:
            raise serializers.ValidationError(
                {"proposed_changes": "Informe alteracoes ou envie uma nova imagem de referencia."}
            )

        if "tattooer" in changes:
            try:
                tid = int(changes["tattooer"])
            except (TypeError, ValueError) as exc:
                raise serializers.ValidationError(
                    {"proposed_changes": "tattooer deve ser um id numerico."}
                ) from exc
            if not Tattooer.objects.filter(pk=tid).exists():
                raise serializers.ValidationError({"proposed_changes": "Tatuador invalido."})

        if "appointment_kind" in changes:
            if changes["appointment_kind"] not in (
                Appointment.KIND_SERVICE,
                Appointment.KIND_CONSULTATION,
            ):
                raise serializers.ValidationError({"proposed_changes": "Modalidade invalida."})

        if "duration_minutes" in changes:
            try:
                dm = int(changes["duration_minutes"])
            except (TypeError, ValueError) as exc:
                raise serializers.ValidationError(
                    {"proposed_changes": "duration_minutes invalido."}
                ) from exc
            if dm < 15 or dm > 480:
                raise serializers.ValidationError(
                    {"proposed_changes": "Duracao deve estar entre 15 e 480 minutos."}
                )

        if "clear_reference_image" in changes:
            changes["clear_reference_image"] = str(changes["clear_reference_image"]).lower() in (
                "1",
                "true",
                "yes",
            )

        scheduled_at = None
        if "scheduled_at" in changes:
            scheduled_at = parse_datetime(str(changes["scheduled_at"]))
            if scheduled_at is None:
                raise serializers.ValidationError(
                    {"proposed_changes": "scheduled_at invalido (use ISO 8601)."}
                )
            try:
                validate_scheduled_within_studio_hours(scheduled_at)
            except ValueError as exc:
                raise serializers.ValidationError({"proposed_changes": str(exc)}) from exc

        tattooer_pk = int(changes["tattooer"]) if "tattooer" in changes else appointment.tattooer_id
        duration = int(changes["duration_minutes"]) if "duration_minutes" in changes else (
            appointment.duration_minutes or 60
        )
        start = scheduled_at if scheduled_at is not None else appointment.scheduled_at

        conflict_qs = (
            Appointment.objects.filter(tattooer_id=tattooer_pk)
            .exclude(status=Appointment.STATUS_CANCELLED)
            .exclude(pk=appointment.pk)
            .only("scheduled_at", "duration_minutes")
        )
        for other in conflict_qs:
            od = other.duration_minutes or 60
            if appointment_intervals_overlap(start, duration, other.scheduled_at, od):
                raise serializers.ValidationError(
                    {
                        "proposed_changes": (
                            "Conflito de horario com outra sessao deste tatuador "
                            "(intervalos sobrepostos)."
                        )
                    }
                )

        attrs["proposed_payload"] = changes
        if scheduled_at is not None:
            attrs["proposed_scheduled_at"] = scheduled_at
        return attrs


class InAppNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = InAppNotification
        fields = ["id", "message", "read", "link", "created_at"]
        read_only_fields = ["id", "message", "link", "created_at"]

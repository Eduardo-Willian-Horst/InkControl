from django.contrib.auth.models import User
from django.db import IntegrityError

from studio.models import Client, InAppNotification, Tattooer, UserProfile


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


__all__ = ["get_or_create_client_for_app_user", "serialize_auth_user"]

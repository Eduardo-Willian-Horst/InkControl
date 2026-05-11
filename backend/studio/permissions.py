from .models import UserProfile
from rest_framework.permissions import BasePermission


def get_user_role(user):
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile.role


class RoleByActionPermission(BasePermission):
    """
    Expects `view.role_permissions = {"action": {"role_a", "role_b"}}`.
    If an action is not present in role_permissions, it is allowed.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        role_permissions = getattr(view, "role_permissions", {})
        allowed_roles = role_permissions.get(getattr(view, "action", None))
        if allowed_roles is None:
            return True

        user_role = get_user_role(request.user)
        return user_role in allowed_roles

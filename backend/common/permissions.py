from ninja_extra.permissions import BasePermission


class IsAuthenticated(BasePermission):
    """Allows access only to authenticated users."""

    def has_permission(self, request, view=None, controller=None, **kwargs):
        return bool(request.user and request.user.is_authenticated)


class IsAdmin(BasePermission):
    """Allows access only to admin/staff users."""

    def has_permission(self, request, view=None, controller=None, **kwargs):
        return bool(
            request.user and request.user.is_authenticated and request.user.is_staff
        )


class IsVerified(BasePermission):
    """Allows access only to users with verified email."""

    def has_permission(self, request, view=None, controller=None, **kwargs):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "is_email_verified", False)
        )


class IsSelfOrAdmin(BasePermission):
    """Allows access if the user is the object owner or an admin.

    Checks object-level permission using `user` attribute on the object.
    Must be used with has_object_permission.
    """

    def has_permission(self, request, view=None, controller=None, **kwargs):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj, controller=None, **kwargs):
        if request.user.is_staff:
            return True
        if hasattr(obj, "user"):
            return obj.user == request.user
        if hasattr(obj, "owner"):
            return obj.owner == request.user
        return obj == request.user

from rest_framework.permissions import BasePermission
from account.models import User

class IsSuperAdminn(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.is_super_admin
        )

class IsAdminOrSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.is_admin_or_super
        )
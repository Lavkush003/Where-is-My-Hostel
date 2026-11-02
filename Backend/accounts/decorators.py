"""Role-based access control decorators."""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def role_required(*allowed_roles):
    """Allow access only to authenticated users with one of the given roles."""

    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            user = request.user
            allowed = set(allowed_roles)
            if "admin" in allowed and user.is_platform_admin:
                return view_func(request, *args, **kwargs)
            if user.role not in allowed:
                raise PermissionDenied("You do not have permission to access this page.")
            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator


student_required = role_required("student")
owner_required = role_required("owner")
admin_required = role_required("admin")

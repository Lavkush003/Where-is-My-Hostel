"""Authentication backend that accepts an email address or username."""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


class EmailOrUsernameBackend(ModelBackend):
    """Authenticate users with either their email address or username."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        user_model = get_user_model()
        identifier = username or kwargs.get(user_model.USERNAME_FIELD) or kwargs.get("email")
        if not identifier or password is None:
            return None

        identifier = identifier.strip()
        lookup = Q(username__iexact=identifier) | Q(email__iexact=identifier)

        user = (
            user_model.objects.filter(lookup)
            .order_by("pk")
            .first()
        )
        if user is None:
            user_model().set_password(password)
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

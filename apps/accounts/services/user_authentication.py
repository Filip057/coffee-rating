"""User authentication service."""

from django.db import transaction
from django.contrib.auth import get_user_model
from django.utils import timezone

from .exceptions import InvalidCredentialsError, InactiveAccountError

User = get_user_model()


@transaction.atomic
def authenticate_user(*, email: str, password: str) -> User:
    """
    Authenticate user with email and password.

    Uses select_for_update() to prevent race conditions when updating last_login.

    Args:
        email: User's email
        password: User's password

    Returns:
        Authenticated User instance

    Raises:
        InvalidCredentialsError: If credentials are invalid
        InactiveAccountError: If account is deactivated
    """
    # Get user with lock to prevent race conditions on last_login
    try:
        user = (
            User.objects
            .select_for_update()
            .get(email=email)
        )
    except User.DoesNotExist:
        raise InvalidCredentialsError("Invalid email or password")

    # Check password
    if not user.check_password(password):
        raise InvalidCredentialsError("Invalid email or password")

    # Check if active
    if not user.is_active:
        raise InactiveAccountError("Account is deactivated")

    # Update last login
    user.last_login = timezone.now()
    user.save(update_fields=['last_login'])

    return user

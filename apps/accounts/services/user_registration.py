"""User registration service."""

from django.db import transaction
from django.contrib.auth import get_user_model
import secrets

from .exceptions import UserRegistrationError

User = get_user_model()


@transaction.atomic
def register_user(
    *,
    email: str,
    password: str,
    display_name: str = ""
) -> User:
    """
    Register a new user with email verification token.

    Args:
        email: User's email address
        password: User's password (will be hashed)
        display_name: Optional display name

    Returns:
        Created User instance

    Raises:
        UserRegistrationError: If registration fails
    """
    try:
        # Create user with hashed password
        user = User.objects.create_user(
            email=email,
            password=password,
            display_name=display_name
        )

        # Generate verification token
        user.verification_token = secrets.token_urlsafe(32)
        user.save(update_fields=['verification_token'])

        # TODO: Send verification email (outside transaction)
        # transaction.on_commit(
        #     lambda: send_verification_email(user)
        # )

        return user

    except Exception as e:
        raise UserRegistrationError(f"Registration failed: {str(e)}")

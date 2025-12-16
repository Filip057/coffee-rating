"""Password reset service."""

from django.db import transaction
from django.contrib.auth import get_user_model
import secrets

from .exceptions import UserNotFoundError, InvalidTokenError

User = get_user_model()


@transaction.atomic
def request_password_reset(*, email: str) -> str:
    """
    Generate password reset token for user.

    Args:
        email: User's email address

    Returns:
        Reset token

    Raises:
        UserNotFoundError: If user does not exist
    """
    try:
        user = (
            User.objects
            .select_for_update()
            .get(email=email, is_active=True)
        )
    except User.DoesNotExist:
        raise UserNotFoundError(f"No active user with email: {email}")

    # Generate reset token
    reset_token = secrets.token_urlsafe(32)
    user.verification_token = reset_token
    user.save(update_fields=['verification_token'])

    # TODO: Send email (outside transaction)
    # transaction.on_commit(
    #     lambda: send_password_reset_email(user, reset_token)
    # )

    return reset_token


@transaction.atomic
def confirm_password_reset(*, token: str, new_password: str) -> User:
    """
    Reset user password with token.

    Args:
        token: Reset token
        new_password: New password

    Returns:
        User instance

    Raises:
        InvalidTokenError: If token is invalid or expired
    """
    try:
        user = (
            User.objects
            .select_for_update()
            .get(verification_token=token, is_active=True)
        )
    except User.DoesNotExist:
        raise InvalidTokenError("Invalid or expired reset token")

    # Set new password and clear token
    user.set_password(new_password)
    user.verification_token = None
    user.save(update_fields=['password', 'verification_token'])

    return user

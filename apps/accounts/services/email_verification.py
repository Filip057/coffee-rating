"""Email verification service."""

from django.db import transaction
from django.contrib.auth import get_user_model
from uuid import UUID

from .exceptions import InvalidTokenError

User = get_user_model()


@transaction.atomic
def verify_user_email(*, user_id: UUID, token: str) -> User:
    """
    Verify user's email with token.

    Args:
        user_id: User's ID
        token: Verification token

    Returns:
        User instance

    Raises:
        InvalidTokenError: If token is invalid
    """
    user = (
        User.objects
        .select_for_update()
        .get(id=user_id)
    )

    if user.verification_token != token:
        raise InvalidTokenError("Invalid verification token")

    # Mark email as verified and clear token
    user.email_verified = True
    user.verification_token = None
    user.save(update_fields=['email_verified', 'verification_token'])

    return user

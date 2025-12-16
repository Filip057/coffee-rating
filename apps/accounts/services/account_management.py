"""Account management service."""

from django.db import transaction
from django.contrib.auth import get_user_model
from uuid import UUID

from .exceptions import PasswordConfirmationError

User = get_user_model()


@transaction.atomic
def delete_user_account(*, user_id: UUID, password: str) -> None:
    """
    GDPR-compliant account deletion (anonymization).

    Args:
        user_id: User's ID
        password: User's password for confirmation

    Raises:
        PasswordConfirmationError: If password is incorrect
    """
    user = (
        User.objects
        .select_for_update()
        .get(id=user_id)
    )

    # Verify password
    if not user.check_password(password):
        raise PasswordConfirmationError("Invalid password")

    # Anonymize user (calls model method)
    user.anonymize()

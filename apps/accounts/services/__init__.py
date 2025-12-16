"""Services for accounts business logic."""

from .exceptions import (
    AccountsServiceError,
    UserRegistrationError,
    InvalidCredentialsError,
    InactiveAccountError,
    InvalidTokenError,
    UserNotFoundError,
    PasswordConfirmationError,
)
from .user_registration import register_user
from .user_authentication import authenticate_user
from .password_reset import request_password_reset, confirm_password_reset
from .email_verification import verify_user_email
from .account_management import delete_user_account

__all__ = [
    # Exceptions
    'AccountsServiceError',
    'UserRegistrationError',
    'InvalidCredentialsError',
    'InactiveAccountError',
    'InvalidTokenError',
    'UserNotFoundError',
    'PasswordConfirmationError',
    # Services
    'register_user',
    'authenticate_user',
    'request_password_reset',
    'confirm_password_reset',
    'verify_user_email',
    'delete_user_account',
]

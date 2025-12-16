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
]

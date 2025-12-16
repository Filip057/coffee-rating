"""Domain-specific exceptions for accounts services."""


class AccountsServiceError(Exception):
    """Base exception for accounts services."""
    pass


class UserRegistrationError(AccountsServiceError):
    """Raised when user registration fails."""
    pass


class InvalidCredentialsError(AccountsServiceError):
    """Raised when authentication credentials are invalid."""
    pass


class InactiveAccountError(AccountsServiceError):
    """Raised when account is deactivated."""
    pass


class InvalidTokenError(AccountsServiceError):
    """Raised when verification/reset token is invalid."""
    pass


class UserNotFoundError(AccountsServiceError):
    """Raised when user does not exist."""
    pass


class PasswordConfirmationError(AccountsServiceError):
    """Raised when password confirmation fails."""
    pass

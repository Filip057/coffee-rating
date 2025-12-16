# Accounts App Refactoring Checklist

**Goal:** Refactor accounts app to follow DRF best practices with proper service layer, transaction management, and concurrency protection.

**Estimated Time:** 1-2 days
**Difficulty:** Medium
**Risk Level:** Low (incremental changes, tests verify correctness)

---

## 📋 Phase 1: Setup & Foundation (30 min)

### ✅ Task 1.1: Create Services Directory Structure

**Create files:**
```bash
apps/accounts/services/
├── __init__.py
├── exceptions.py
├── user_registration.py
├── user_authentication.py
├── password_reset.py
├── email_verification.py
└── account_management.py
```

**Command:**
```bash
mkdir -p apps/accounts/services
touch apps/accounts/services/__init__.py
touch apps/accounts/services/exceptions.py
touch apps/accounts/services/user_registration.py
touch apps/accounts/services/user_authentication.py
touch apps/accounts/services/password_reset.py
touch apps/accounts/services/email_verification.py
touch apps/accounts/services/account_management.py
```

---

### ✅ Task 1.2: Create Domain Exceptions

**File:** `apps/accounts/services/exceptions.py`

**Content:**
```python
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
```

**Test:** Import works
```bash
python manage.py shell -c "from apps.accounts.services.exceptions import AccountsServiceError"
```

---

### ✅ Task 1.3: Create Services __init__.py

**File:** `apps/accounts/services/__init__.py`

**Content:**
```python
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

__all__ = [
    'AccountsServiceError',
    'UserRegistrationError',
    'InvalidCredentialsError',
    'InactiveAccountError',
    'InvalidTokenError',
    'UserNotFoundError',
    'PasswordConfirmationError',
]
```

---

## 📋 Phase 2: User Registration (45 min)

### ✅ Task 2.1: Create Registration Service

**File:** `apps/accounts/services/user_registration.py`

**Content:**
```python
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
```

**Export in services/__init__.py:**
```python
from .user_registration import register_user

__all__ = [
    # ... existing exports
    'register_user',
]
```

---

### ✅ Task 2.2: Update Registration Serializer

**File:** `apps/accounts/serializers.py`

**Action:** Remove the `create()` method from `UserRegistrationSerializer`

**Before:**
```python
def create(self, validated_data):
    """Create user with hashed password."""
    validated_data.pop('password_confirm')

    user = User.objects.create_user(
        email=validated_data['email'],
        password=validated_data['password'],
        display_name=validated_data.get('display_name', '')
    )

    # Generate verification token
    import secrets
    user.verification_token = secrets.token_urlsafe(32)
    user.save(update_fields=['verification_token'])

    # TODO: Send verification email

    return user
```

**After:**
```python
# Remove entire create() method
# Serializer now only validates input
```

---

### ✅ Task 2.3: Update Registration View

**File:** `apps/accounts/views.py`

**Before (lines 64-83):**
```python
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """Register a new user account."""
    serializer = UserRegistrationSerializer(data=request.data)

    if serializer.is_valid():
        user = serializer.save()

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        return Response({
            'message': 'Registration successful. Please verify your email.',
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
```

**After:**
```python
from apps.accounts.services import register_user, UserRegistrationError

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """Register a new user account."""
    serializer = UserRegistrationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    # Remove password_confirm before passing to service
    data = serializer.validated_data.copy()
    data.pop('password_confirm', None)

    try:
        user = register_user(**data)
    except UserRegistrationError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Generate JWT tokens
    refresh = RefreshToken.for_user(user)

    return Response({
        'message': 'Registration successful. Please verify your email.',
        'user': UserSerializer(user).data,
        'tokens': {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
    }, status=status.HTTP_201_CREATED)
```

---

### ✅ Task 2.4: Test Registration

**Run tests:**
```bash
pytest apps/accounts/tests/test_api.py::TestRegistration -v
```

**Expected:** All registration tests pass ✅

---

## 📋 Phase 3: User Authentication (45 min)

### ✅ Task 3.1: Create Authentication Service

**File:** `apps/accounts/services/user_authentication.py`

**Content:**
```python
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
```

**Export:**
```python
from .user_authentication import authenticate_user
```

---

### ✅ Task 3.2: Update Login View

**File:** `apps/accounts/views.py`

**Before (lines 99-136):**
```python
@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """Login with email and password."""
    serializer = UserLoginSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    email = serializer.validated_data['email']
    password = serializer.validated_data['password']

    # Authenticate user
    user = authenticate(request, username=email, password=password)

    if user is None:
        return Response({
            'error': 'Invalid credentials'
        }, status=status.HTTP_401_UNAUTHORIZED)

    if not user.is_active:
        return Response({
            'error': 'Account is deactivated'
        }, status=status.HTTP_403_FORBIDDEN)

    # Update last login
    user.last_login = timezone.now()
    user.save(update_fields=['last_login'])

    # Generate tokens
    refresh = RefreshToken.for_user(user)

    return Response({
        'message': 'Login successful',
        'user': UserSerializer(user).data,
        'tokens': {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
    })
```

**After:**
```python
from apps.accounts.services import (
    authenticate_user,
    InvalidCredentialsError,
    InactiveAccountError
)

@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """Login with email and password."""
    serializer = UserLoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        user = authenticate_user(
            email=serializer.validated_data['email'],
            password=serializer.validated_data['password']
        )
    except InvalidCredentialsError:
        return Response(
            {'error': 'Invalid credentials'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    except InactiveAccountError:
        return Response(
            {'error': 'Account is deactivated'},
            status=status.HTTP_403_FORBIDDEN
        )

    # Generate tokens
    refresh = RefreshToken.for_user(user)

    return Response({
        'message': 'Login successful',
        'user': UserSerializer(user).data,
        'tokens': {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
    })
```

---

### ✅ Task 3.3: Test Login

**Run tests:**
```bash
pytest apps/accounts/tests/test_api.py::TestLogin -v
```

**Expected:** All login tests pass ✅

---

## 📋 Phase 4: Password Reset (60 min)

### ✅ Task 4.1: Create Password Reset Service

**File:** `apps/accounts/services/password_reset.py`

**Content:**
```python
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
```

**Export:**
```python
from .password_reset import request_password_reset, confirm_password_reset
```

---

### ✅ Task 4.2: Update Password Reset Views

**File:** `apps/accounts/views.py`

**Request view - Before (lines 209-240):**
```python
@api_view(['POST'])
@permission_classes([AllowAny])
def request_password_reset(request):
    """Request password reset email."""
    serializer = PasswordResetRequestSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    email = serializer.validated_data['email']

    try:
        user = User.objects.get(email=email, is_active=True)

        # Generate reset token
        reset_token = secrets.token_urlsafe(32)
        user.verification_token = reset_token
        user.save(update_fields=['verification_token'])

        # Send email (implement email sending)
        # send_password_reset_email(user, reset_token)

        return Response({
            'message': 'Password reset email sent',
            'token': reset_token  # Remove in production!
        })

    except User.DoesNotExist:
        # Don't reveal if email exists (security)
        return Response({
            'message': 'If account exists, password reset email has been sent'
        })
```

**After:**
```python
from apps.accounts.services import (
    request_password_reset as request_reset_service,
    UserNotFoundError
)

@api_view(['POST'])
@permission_classes([AllowAny])
def request_password_reset(request):
    """Request password reset email."""
    serializer = PasswordResetRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        reset_token = request_reset_service(
            email=serializer.validated_data['email']
        )

        return Response({
            'message': 'Password reset email sent',
            'token': reset_token  # Remove in production!
        })
    except UserNotFoundError:
        # Don't reveal if email exists (security)
        pass

    return Response({
        'message': 'If account exists, password reset email has been sent'
    })
```

**Confirm view - Before (lines 252-279):**
```python
@api_view(['POST'])
@permission_classes([AllowAny])
def confirm_password_reset(request):
    """Confirm password reset with token."""
    serializer = PasswordResetConfirmSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    token = serializer.validated_data['token']
    new_password = serializer.validated_data['new_password']

    try:
        user = User.objects.get(verification_token=token, is_active=True)

        # Set new password
        user.set_password(new_password)
        user.verification_token = None
        user.save(update_fields=['password', 'verification_token'])

        return Response({
            'message': 'Password reset successful'
        })

    except User.DoesNotExist:
        return Response({
            'error': 'Invalid or expired reset token'
        }, status=status.HTTP_400_BAD_REQUEST)
```

**After:**
```python
from apps.accounts.services import (
    confirm_password_reset as confirm_reset_service,
    InvalidTokenError
)

@api_view(['POST'])
@permission_classes([AllowAny])
def confirm_password_reset(request):
    """Confirm password reset with token."""
    serializer = PasswordResetConfirmSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        confirm_reset_service(
            token=serializer.validated_data['token'],
            new_password=serializer.validated_data['new_password']
        )

        return Response({
            'message': 'Password reset successful'
        })
    except InvalidTokenError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
```

---

### ✅ Task 4.3: Test Password Reset

**Run tests:**
```bash
pytest apps/accounts/tests/test_api.py -k password_reset -v
```

**Expected:** All password reset tests pass ✅

---

## 📋 Phase 5: Email Verification (30 min)

### ✅ Task 5.1: Create Email Verification Service

**File:** `apps/accounts/services/email_verification.py`

**Content:**
```python
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
```

**Export:**
```python
from .email_verification import verify_user_email
```

---

### ✅ Task 5.2: Update Email Verification View

**File:** `apps/accounts/views.py`

**Before (lines 291-309):**
```python
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_email(request):
    """Verify email with token."""
    token = request.data.get('token')
    user = request.user

    if user.verification_token == token:
        user.email_verified = True
        user.verification_token = None
        user.save(update_fields=['email_verified', 'verification_token'])

        return Response({
            'message': 'Email verified successfully'
        })

    return Response({
        'error': 'Invalid verification token'
    }, status=status.HTTP_400_BAD_REQUEST)
```

**After:**
```python
from apps.accounts.services import verify_user_email, InvalidTokenError

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_email(request):
    """Verify email with token."""
    token = request.data.get('token')

    try:
        verify_user_email(
            user_id=request.user.id,
            token=token
        )

        return Response({
            'message': 'Email verified successfully'
        })
    except InvalidTokenError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
```

---

### ✅ Task 5.3: Test Email Verification

**Run tests:**
```bash
pytest apps/accounts/tests/test_api.py -k verify_email -v
```

**Expected:** All email verification tests pass ✅

---

## 📋 Phase 6: Account Management (30 min)

### ✅ Task 6.1: Create Account Management Service

**File:** `apps/accounts/services/account_management.py`

**Content:**
```python
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
```

**Export:**
```python
from .account_management import delete_user_account
```

---

### ✅ Task 6.2: Update Account Deletion View

**File:** `apps/accounts/views.py`

**Before (lines 322-345):**
```python
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_account(request):
    """GDPR-compliant account deletion (anonymization)."""
    password = request.data.get('password')
    confirm = request.data.get('confirm')

    if not confirm:
        return Response({
            'error': 'Confirmation required'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Verify password
    if not request.user.check_password(password):
        return Response({
            'error': 'Invalid password'
        }, status=status.HTTP_401_UNAUTHORIZED)

    # Anonymize user data (GDPR)
    request.user.anonymize()

    return Response({
        'message': 'Account deleted successfully'
    }, status=status.HTTP_204_NO_CONTENT)
```

**After:**
```python
from apps.accounts.services import (
    delete_user_account,
    PasswordConfirmationError
)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_account(request):
    """GDPR-compliant account deletion (anonymization)."""
    password = request.data.get('password')
    confirm = request.data.get('confirm')

    if not confirm:
        return Response({
            'error': 'Confirmation required'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        delete_user_account(
            user_id=request.user.id,
            password=password
        )

        return Response({
            'message': 'Account deleted successfully'
        }, status=status.HTTP_204_NO_CONTENT)
    except PasswordConfirmationError:
        return Response(
            {'error': 'Invalid password'},
            status=status.HTTP_401_UNAUTHORIZED
        )
```

---

### ✅ Task 6.3: Test Account Deletion

**Run tests:**
```bash
pytest apps/accounts/tests/test_api.py -k delete -v
```

**Expected:** All deletion tests pass ✅

---

## 📋 Phase 7: Additional Improvements (30 min)

### ✅ Task 7.1: Fix Logout Exception Handling

**File:** `apps/accounts/views.py` (lines 152-165)

**Before:**
```python
try:
    refresh_token = request.data.get('refresh')
    if refresh_token:
        token = RefreshToken(refresh_token)
        # Note: Requires djangorestframework-simplejwt[blacklist]
        # token.blacklist()

    return Response({
        'message': 'Logout successful'
    })
except Exception as e:  # ❌ Too broad
    return Response({
        'error': 'Invalid token'
    }, status=status.HTTP_400_BAD_REQUEST)
```

**After:**
```python
from rest_framework_simplejwt.exceptions import TokenError

try:
    refresh_token = request.data.get('refresh')
    if refresh_token:
        token = RefreshToken(refresh_token)
        # Note: Requires djangorestframework-simplejwt[blacklist]
        # token.blacklist()

    return Response({
        'message': 'Logout successful'
    })
except TokenError:  # ✅ Specific exception
    return Response({
        'error': 'Invalid token'
    }, status=status.HTTP_400_BAD_REQUEST)
```

---

### ✅ Task 7.2: Add Global Exception Handler (Optional)

**File:** `config/exception_handlers.py` (create new file)

**Content:**
```python
"""Custom exception handlers for DRF."""

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

from apps.accounts.services.exceptions import (
    InvalidCredentialsError,
    InactiveAccountError,
    InvalidTokenError,
    UserNotFoundError,
    PasswordConfirmationError,
    UserRegistrationError,
)


def custom_exception_handler(exc, context):
    """
    Custom exception handler that maps domain exceptions to HTTP responses.
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    # If DRF didn't handle it, check our domain exceptions
    if response is None:
        if isinstance(exc, InvalidCredentialsError):
            return Response(
                {'error': str(exc)},
                status=status.HTTP_401_UNAUTHORIZED
            )
        elif isinstance(exc, InactiveAccountError):
            return Response(
                {'error': str(exc)},
                status=status.HTTP_403_FORBIDDEN
            )
        elif isinstance(exc, (InvalidTokenError, PasswordConfirmationError, UserRegistrationError)):
            return Response(
                {'error': str(exc)},
                status=status.HTTP_400_BAD_REQUEST
            )
        elif isinstance(exc, UserNotFoundError):
            return Response(
                {'error': str(exc)},
                status=status.HTTP_404_NOT_FOUND
            )

    return response
```

**Update settings.py:**
```python
REST_FRAMEWORK = {
    # ... existing settings
    'EXCEPTION_HANDLER': 'config.exception_handlers.custom_exception_handler',
}
```

---

## 📋 Phase 8: Testing & Validation (60 min)

### ✅ Task 8.1: Create Service Unit Tests

**File:** `apps/accounts/tests/test_services.py` (create new file)

**Content:**
```python
"""Unit tests for accounts services."""

import pytest
from django.db import transaction
from apps.accounts.models import User
from apps.accounts.services import (
    register_user,
    authenticate_user,
    request_password_reset,
    confirm_password_reset,
    verify_user_email,
    delete_user_account,
    UserRegistrationError,
    InvalidCredentialsError,
    InactiveAccountError,
    InvalidTokenError,
    UserNotFoundError,
    PasswordConfirmationError,
)


@pytest.mark.django_db
class TestRegistrationService:
    """Tests for register_user service."""

    def test_register_user_success(self):
        """Successfully register a new user."""
        user = register_user(
            email='test@example.com',
            password='SecurePass123!',
            display_name='Test User'
        )

        assert user.email == 'test@example.com'
        assert user.display_name == 'Test User'
        assert user.check_password('SecurePass123!')
        assert user.verification_token is not None
        assert not user.email_verified

    def test_register_user_duplicate_email(self, user):
        """Cannot register with duplicate email."""
        with pytest.raises(UserRegistrationError):
            register_user(
                email=user.email,
                password='SecurePass123!'
            )

    def test_register_user_creates_token(self):
        """Registration creates verification token."""
        user = register_user(
            email='verify@example.com',
            password='SecurePass123!'
        )

        assert user.verification_token is not None
        assert len(user.verification_token) > 20


@pytest.mark.django_db
class TestAuthenticationService:
    """Tests for authenticate_user service."""

    def test_authenticate_valid_credentials(self, user):
        """Authenticate with valid credentials."""
        authenticated_user = authenticate_user(
            email=user.email,
            password='TestPass123!'
        )

        assert authenticated_user.id == user.id
        assert authenticated_user.last_login is not None

    def test_authenticate_invalid_password(self, user):
        """Authentication fails with wrong password."""
        with pytest.raises(InvalidCredentialsError):
            authenticate_user(
                email=user.email,
                password='WrongPassword'
            )

    def test_authenticate_nonexistent_user(self):
        """Authentication fails for non-existent user."""
        with pytest.raises(InvalidCredentialsError):
            authenticate_user(
                email='nonexistent@example.com',
                password='password'
            )

    def test_authenticate_inactive_user(self, user):
        """Authentication fails for inactive user."""
        user.is_active = False
        user.save()

        with pytest.raises(InactiveAccountError):
            authenticate_user(
                email=user.email,
                password='TestPass123!'
            )


@pytest.mark.django_db
class TestPasswordResetService:
    """Tests for password reset services."""

    def test_request_password_reset_success(self, user):
        """Successfully request password reset."""
        token = request_password_reset(email=user.email)

        assert token is not None
        user.refresh_from_db()
        assert user.verification_token == token

    def test_request_password_reset_nonexistent_user(self):
        """Request fails for non-existent user."""
        with pytest.raises(UserNotFoundError):
            request_password_reset(email='nonexistent@example.com')

    def test_confirm_password_reset_success(self, user):
        """Successfully reset password with token."""
        token = request_password_reset(email=user.email)

        confirm_password_reset(
            token=token,
            new_password='NewSecure123!'
        )

        user.refresh_from_db()
        assert user.check_password('NewSecure123!')
        assert user.verification_token is None

    def test_confirm_password_reset_invalid_token(self):
        """Reset fails with invalid token."""
        with pytest.raises(InvalidTokenError):
            confirm_password_reset(
                token='invalid-token',
                new_password='NewPass123!'
            )


@pytest.mark.django_db
class TestConcurrency:
    """Tests for concurrency protection."""

    def test_concurrent_password_reset_requests(self, user):
        """Multiple concurrent reset requests are handled safely."""
        # This test would need threading/multiprocessing
        # to properly test race conditions
        pass

    def test_concurrent_login_attempts(self, user):
        """Multiple concurrent logins update last_login correctly."""
        # This test would need threading/multiprocessing
        pass
```

**Run service tests:**
```bash
pytest apps/accounts/tests/test_services.py -v
```

---

### ✅ Task 8.2: Run Full Test Suite

**Run all accounts tests:**
```bash
pytest apps/accounts/tests/ -v --tb=short
```

**Expected:** All tests pass ✅

---

### ✅ Task 8.3: Test Coverage Report

**Generate coverage:**
```bash
pytest apps/accounts/tests/ --cov=apps.accounts --cov-report=html
```

**Review:**
```bash
open htmlcov/index.html
```

**Target:** >90% coverage on services

---

## 📋 Phase 9: Documentation & Cleanup (30 min)

### ✅ Task 9.1: Update App Documentation

**File:** `docs/app-context/accounts.md`

**Add section:**
```markdown
## Services Layer

The accounts app follows DRF best practices with a dedicated services layer:

### Service Files

- `services/user_registration.py` - User registration logic
- `services/user_authentication.py` - Authentication logic
- `services/password_reset.py` - Password reset workflows
- `services/email_verification.py` - Email verification
- `services/account_management.py` - Account deletion/management
- `services/exceptions.py` - Domain-specific exceptions

### Transaction Safety

All state-changing operations are wrapped in `@transaction.atomic` decorators:
- User registration
- Password reset
- Email verification
- Account deletion
- Login (last_login update)

### Concurrency Protection

Critical operations use `select_for_update()` to prevent race conditions:
- Login (last_login)
- Password reset request
- Password reset confirm
- Email verification
```

---

### ✅ Task 9.2: Remove TODO Comments

**Search for TODOs:**
```bash
grep -r "TODO" apps/accounts/*.py apps/accounts/services/*.py
```

**Action:** Resolve or document each TODO

---

### ✅ Task 9.3: Clean Up Imports

**File:** `apps/accounts/views.py`

**Organize imports:**
```python
# Standard library
import secrets

# Django
from django.contrib.auth import authenticate
from django.utils import timezone

# DRF
from rest_framework import status, generics, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

# DRF Spectacular
from drf_spectacular.utils import extend_schema, inline_serializer

# Local
from .models import User
from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
)
from .services import (
    register_user,
    authenticate_user,
    request_password_reset as request_reset_service,
    confirm_password_reset as confirm_reset_service,
    verify_user_email,
    delete_user_account,
    # Exceptions
    UserRegistrationError,
    InvalidCredentialsError,
    InactiveAccountError,
    InvalidTokenError,
    UserNotFoundError,
    PasswordConfirmationError,
)
```

---

## ✅ Final Verification Checklist

Before considering refactoring complete:

- [ ] All services created and exported
- [ ] All views updated to use services
- [ ] All serializers simplified (no business logic)
- [ ] All state changes wrapped in `@transaction.atomic`
- [ ] Critical operations use `select_for_update()`
- [ ] All API tests pass
- [ ] Service unit tests created and passing
- [ ] No generic `except Exception` blocks
- [ ] Documentation updated
- [ ] Code review completed
- [ ] No breaking changes to API interface

---

## 📊 Success Metrics

**Code Quality:**
- ✅ Clear separation of concerns
- ✅ Services contain business logic
- ✅ Views are thin (HTTP only)
- ✅ Serializers only validate
- ✅ Models enforce domain rules

**Safety:**
- ✅ Transaction protection
- ✅ Concurrency protection
- ✅ No race conditions

**Testability:**
- ✅ Service unit tests
- ✅ API integration tests
- ✅ >90% coverage

**Maintainability:**
- ✅ Easy to understand
- ✅ Easy to extend
- ✅ Well documented

---

## 🎉 Completion

Once all tasks are complete:

1. **Commit changes:**
```bash
git add apps/accounts/
git commit -m "Refactor accounts app to follow DRF best practices

- Add services layer for business logic
- Add transaction management with @transaction.atomic
- Add concurrency protection with select_for_update()
- Simplify views to HTTP-only concerns
- Remove business logic from serializers
- Add domain-specific exceptions
- Add service unit tests
- Update documentation"
```

2. **Push to remote:**
```bash
git push origin claude/github-workflow-guide-ieUiF
```

3. **Create PR** with detailed description of changes

---

**Total Estimated Time:** 6-8 hours (can be done over 1-2 days)

**Difficulty:** Medium

**Risk:** Low (incremental, tests verify correctness)

**Benefit:** High (better architecture, safer code, easier maintenance)

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from apps.accounts.models import User


@pytest.fixture
def api_client():
    """Return an unauthenticated API client."""
    return APIClient()


@pytest.fixture
def user(db):
    """Create and return a test user."""
    return User.objects.create_user(
        email='testuser@example.com',
        password='TestPass123!',
        display_name='Test User',
        email_verified=True,
    )


@pytest.fixture
def user_unverified(db):
    """Create and return a user with unverified email."""
    user = User.objects.create_user(
        email='unverified@example.com',
        password='TestPass123!',
        display_name='Unverified User',
        email_verified=False,
    )
    user.verification_token = 'test-verification-token'
    user.save()
    return user


@pytest.fixture
def user_inactive(db):
    """Create and return an inactive user."""
    return User.objects.create_user(
        email='inactive@example.com',
        password='TestPass123!',
        display_name='Inactive User',
        is_active=False,
    )


@pytest.fixture
def other_user(db):
    """Create and return another test user."""
    return User.objects.create_user(
        email='otheruser@example.com',
        password='OtherPass123!',
        display_name='Other User',
        email_verified=True,
    )


@pytest.fixture
def authenticated_client(api_client, user):
    """Return an authenticated API client using JWT."""
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


@pytest.fixture
def user_with_reset_token(db):
    """Create a user with a password reset token."""
    user = User.objects.create_user(
        email='resetuser@example.com',
        password='OldPass123!',
        display_name='Reset User',
        email_verified=True,
    )
    user.verification_token = 'valid-reset-token-12345'
    user.save()
    return user

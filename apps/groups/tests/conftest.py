import pytest
import secrets
from decimal import Decimal
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from apps.accounts.models import User
from apps.groups.models import Group, GroupMembership, GroupLibraryEntry, GroupRole
from apps.beans.models import CoffeeBean


def generate_invite_code():
    """Generate a random invite code for test fixtures."""
    return secrets.token_urlsafe(12)[:16]


@pytest.fixture
def api_client():
    """Return an unauthenticated API client."""
    return APIClient()


@pytest.fixture
def group_owner(db):
    """Create and return a test user (group owner)."""
    return User.objects.create_user(
        email='owner@example.com',
        password='TestPass123!',
        display_name='Group Owner',
        email_verified=True,
    )


@pytest.fixture
def admin_user(db):
    """Create and return an admin user."""
    return User.objects.create_user(
        email='admin@example.com',
        password='TestPass123!',
        display_name='Group Admin',
        email_verified=True,
    )


@pytest.fixture
def member_user(db):
    """Create and return a member user."""
    return User.objects.create_user(
        email='member@example.com',
        password='TestPass123!',
        display_name='Group Member',
        email_verified=True,
    )


@pytest.fixture
def group_other_user(db):
    """Create and return a user not in any group."""
    return User.objects.create_user(
        email='other@example.com',
        password='TestPass123!',
        display_name='Other User',
        email_verified=True,
    )


@pytest.fixture
def authenticated_client(api_client, group_owner):
    """Return API client authenticated as group owner."""
    refresh = RefreshToken.for_user(group_owner)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


@pytest.fixture
def admin_client(api_client, admin_user):
    """Return API client authenticated as group admin."""
    refresh = RefreshToken.for_user(admin_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


@pytest.fixture
def member_client(api_client, member_user):
    """Return API client authenticated as group member."""
    refresh = RefreshToken.for_user(member_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


@pytest.fixture
def other_client(api_client, group_other_user):
    """Return API client authenticated as non-member user."""
    refresh = RefreshToken.for_user(group_other_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


@pytest.fixture
def group(db, group_owner):
    """Create and return a test group with owner membership."""
    group = Group.objects.create(
        name='Test Coffee Club',
        description='A group for coffee enthusiasts',
        is_private=True,
        owner=group_owner,
        invite_code=generate_invite_code(),
    )
    # Create owner membership
    GroupMembership.objects.create(
        user=group_owner,
        group=group,
        role=GroupRole.OWNER,
    )
    return group


@pytest.fixture
def group_with_members(group, admin_user, member_user):
    """Group with owner, admin, and member."""
    GroupMembership.objects.create(
        user=admin_user,
        group=group,
        role=GroupRole.ADMIN,
    )
    GroupMembership.objects.create(
        user=member_user,
        group=group,
        role=GroupRole.MEMBER,
    )
    return group


@pytest.fixture
def public_group(db, group_owner):
    """Create and return a public group."""
    group = Group.objects.create(
        name='Public Coffee Club',
        description='A public group',
        is_private=False,
        owner=group_owner,
        invite_code=generate_invite_code(),
    )
    GroupMembership.objects.create(
        user=group_owner,
        group=group,
        role=GroupRole.OWNER,
    )
    return group


@pytest.fixture
def group_coffeebean(db, group_owner):
    """Create and return a test coffee bean."""
    return CoffeeBean.objects.create(
        name='Ethiopia Yirgacheffe',
        roastery_name='Test Roastery',
        origin_country='Ethiopia',
        created_by=group_owner,
    )


@pytest.fixture
def group_another_coffeebean(db, group_owner):
    """Create and return another test coffee bean."""
    return CoffeeBean.objects.create(
        name='Brazil Santos',
        roastery_name='Another Roastery',
        origin_country='Brazil',
        created_by=group_owner,
    )


@pytest.fixture
def group_library_entry(db, group, group_coffeebean, group_owner):
    """Create and return a library entry."""
    return GroupLibraryEntry.objects.create(
        group=group,
        coffeebean=group_coffeebean,
        added_by=group_owner,
        notes='Great coffee!',
    )

import pytest
from decimal import Decimal
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from apps.accounts.models import User
from apps.beans.models import CoffeeBean
from apps.groups.models import Group, GroupMembership, GroupRole
from apps.reviews.models import Review, Tag, UserLibraryEntry


@pytest.fixture
def api_client():
    """Return an unauthenticated API client."""
    return APIClient()


@pytest.fixture
def user(db):
    """Create and return a test user."""
    return User.objects.create_user(
        email='reviewer@example.com',
        password='TestPass123!',
        display_name='Coffee Reviewer',
        email_verified=True,
    )


@pytest.fixture
def other_user(db):
    """Create and return another test user."""
    return User.objects.create_user(
        email='other@example.com',
        password='TestPass123!',
        display_name='Other User',
        email_verified=True,
    )


@pytest.fixture
def authenticated_client(api_client, user):
    """Return API client authenticated as user."""
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


@pytest.fixture
def other_client(api_client, other_user):
    """Return API client authenticated as other user."""
    refresh = RefreshToken.for_user(other_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


@pytest.fixture
def coffeebean(db, user):
    """Create and return a test coffee bean."""
    return CoffeeBean.objects.create(
        name='Ethiopia Yirgacheffe',
        roastery_name='Test Roastery',
        origin_country='Ethiopia',
        roast_profile='light',
        created_by=user,
    )


@pytest.fixture
def another_coffeebean(db, user):
    """Create and return another test coffee bean."""
    return CoffeeBean.objects.create(
        name='Brazil Santos',
        roastery_name='Another Roastery',
        origin_country='Brazil',
        roast_profile='dark',
        created_by=user,
    )


@pytest.fixture
def tag_fruity(db):
    """Create a fruity taste tag."""
    return Tag.objects.create(
        name='fruity',
        category='flavor',
    )


@pytest.fixture
def tag_chocolate(db):
    """Create a chocolate taste tag."""
    return Tag.objects.create(
        name='chocolate',
        category='flavor',
    )


@pytest.fixture
def tag_floral(db):
    """Create a floral taste tag."""
    return Tag.objects.create(
        name='floral',
        category='aroma',
    )


@pytest.fixture
def review(db, user, coffeebean, tag_fruity):
    """Create and return a test review."""
    review = Review.objects.create(
        coffeebean=coffeebean,
        author=user,
        rating=4,
        aroma_score=4,
        flavor_score=5,
        notes='Great coffee with fruity notes!',
        brew_method='filter',
        context='personal',
        would_buy_again=True,
    )
    review.taste_tags.add(tag_fruity)
    return review


@pytest.fixture
def other_review(db, other_user, coffeebean):
    """Create a review by another user."""
    return Review.objects.create(
        coffeebean=coffeebean,
        author=other_user,
        rating=3,
        notes='Decent coffee.',
        context='personal',
    )


@pytest.fixture
def group(db, user):
    """Create a test group."""
    group = Group.objects.create(
        name='Coffee Club',
        description='A group for coffee lovers',
        owner=user,
    )
    GroupMembership.objects.create(
        user=user,
        group=group,
        role=GroupRole.OWNER,
    )
    return group


@pytest.fixture
def library_entry(db, user, coffeebean):
    """Create a user library entry."""
    return UserLibraryEntry.objects.create(
        user=user,
        coffeebean=coffeebean,
        added_by='manual',
    )


@pytest.fixture
def archived_library_entry(db, user, another_coffeebean):
    """Create an archived library entry."""
    return UserLibraryEntry.objects.create(
        user=user,
        coffeebean=another_coffeebean,
        added_by='manual',
        is_archived=True,
    )

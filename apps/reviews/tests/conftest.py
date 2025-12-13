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
def review_user(db):
    """Create and return a test user for reviews."""
    return User.objects.create_user(
        email='reviewer@example.com',
        password='TestPass123!',
        display_name='Coffee Reviewer',
        email_verified=True,
    )


@pytest.fixture
def review_other_user(db):
    """Create and return another test user for reviews."""
    return User.objects.create_user(
        email='review_other@example.com',
        password='TestPass123!',
        display_name='Review Other User',
        email_verified=True,
    )


@pytest.fixture
def review_auth_client(api_client, review_user):
    """Return API client authenticated as review user."""
    refresh = RefreshToken.for_user(review_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


@pytest.fixture
def review_other_client(api_client, review_other_user):
    """Return API client authenticated as other user."""
    refresh = RefreshToken.for_user(review_other_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


@pytest.fixture
def review_coffeebean(db, review_user):
    """Create and return a test coffee bean for reviews."""
    return CoffeeBean.objects.create(
        name='Ethiopia Yirgacheffe',
        roastery_name='Test Roastery',
        origin_country='Ethiopia',
        roast_profile='light',
        created_by=review_user,
    )


@pytest.fixture
def review_another_coffeebean(db, review_user):
    """Create and return another test coffee bean for reviews."""
    return CoffeeBean.objects.create(
        name='Brazil Santos',
        roastery_name='Another Roastery',
        origin_country='Brazil',
        roast_profile='dark',
        created_by=review_user,
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
def review(db, review_user, review_coffeebean, tag_fruity):
    """Create and return a test review."""
    review = Review.objects.create(
        coffeebean=review_coffeebean,
        author=review_user,
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
def other_review(db, review_other_user, review_coffeebean):
    """Create a review by another user."""
    return Review.objects.create(
        coffeebean=review_coffeebean,
        author=review_other_user,
        rating=3,
        notes='Decent coffee.',
        context='personal',
    )


@pytest.fixture
def review_group(db, review_user):
    """Create a test group for reviews."""
    group = Group.objects.create(
        name='Review Coffee Club',
        description='A group for coffee lovers',
        owner=review_user,
    )
    GroupMembership.objects.create(
        user=review_user,
        group=group,
        role=GroupRole.OWNER,
    )
    return group


@pytest.fixture
def review_library_entry(db, review_user, review_coffeebean):
    """Create a user library entry for reviews."""
    return UserLibraryEntry.objects.create(
        user=review_user,
        coffeebean=review_coffeebean,
        added_by='manual',
    )


@pytest.fixture
def review_archived_library_entry(db, review_user, review_another_coffeebean):
    """Create an archived library entry for reviews."""
    return UserLibraryEntry.objects.create(
        user=review_user,
        coffeebean=review_another_coffeebean,
        added_by='manual',
        is_archived=True,
    )

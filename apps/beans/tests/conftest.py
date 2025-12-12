import pytest
from decimal import Decimal
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.beans.models import CoffeeBean, CoffeeBeanVariant


@pytest.fixture
def api_client():
    """Return an unauthenticated API client."""
    return APIClient()


@pytest.fixture
def user(db):
    """Create and return a test user."""
    return User.objects.create_user(
        email='testuser@example.com',
        password='testpass123',
        display_name='Test User',
        email_verified=True,
    )


@pytest.fixture
def other_user(db):
    """Create and return another test user."""
    return User.objects.create_user(
        email='otheruser@example.com',
        password='otherpass123',
        display_name='Other User',
        email_verified=True,
    )


@pytest.fixture
def authenticated_client(api_client, user):
    """Return an authenticated API client."""
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def coffeebean(db, user):
    """Create and return a test coffee bean."""
    return CoffeeBean.objects.create(
        name='Ethiopia Yirgacheffe',
        roastery_name='Test Roastery',
        origin_country='Ethiopia',
        region='Yirgacheffe',
        processing='washed',
        roast_profile='light',
        brew_method='filter',
        description='A bright and fruity coffee.',
        tasting_notes='Blueberry, citrus, floral',
        created_by=user,
    )


@pytest.fixture
def coffeebean_dark(db, user):
    """Create and return a dark roast coffee bean."""
    return CoffeeBean.objects.create(
        name='Brazil Santos',
        roastery_name='Dark Roasters',
        origin_country='Brazil',
        region='Santos',
        processing='natural',
        roast_profile='dark',
        brew_method='espresso',
        description='A classic Brazilian coffee.',
        tasting_notes='Chocolate, nuts, caramel',
        created_by=user,
    )


@pytest.fixture
def coffeebean_inactive(db, user):
    """Create and return an inactive coffee bean."""
    return CoffeeBean.objects.create(
        name='Inactive Bean',
        roastery_name='Old Roastery',
        origin_country='Colombia',
        is_active=False,
        created_by=user,
    )


@pytest.fixture
def variant(db, coffeebean):
    """Create and return a test variant."""
    return CoffeeBeanVariant.objects.create(
        coffeebean=coffeebean,
        package_weight_grams=250,
        price_czk=Decimal('299.00'),
        purchase_url='https://example.com/buy',
    )


@pytest.fixture
def variant_large(db, coffeebean):
    """Create and return a larger variant."""
    return CoffeeBeanVariant.objects.create(
        coffeebean=coffeebean,
        package_weight_grams=1000,
        price_czk=Decimal('999.00'),
        purchase_url='https://example.com/buy-large',
    )

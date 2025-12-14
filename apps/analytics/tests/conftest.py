import pytest
from decimal import Decimal
from datetime import date, timedelta
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from apps.accounts.models import User
from apps.beans.models import CoffeeBean
from apps.groups.models import Group, GroupMembership, GroupRole
from apps.purchases.models import PurchaseRecord, PaymentShare, PaymentStatus
from apps.reviews.models import Review, Tag


@pytest.fixture
def api_client():
    """Return an unauthenticated API client."""
    return APIClient()


# =============================================================================
# Users
# =============================================================================

@pytest.fixture
def analytics_user(db):
    """Create the main analytics test user."""
    return User.objects.create_user(
        email='analytics_user@example.com',
        password='TestPass123!',
        display_name='Analytics User',
        email_verified=True,
    )


@pytest.fixture
def analytics_member1(db):
    """Create a group member for analytics tests."""
    return User.objects.create_user(
        email='analytics_member1@example.com',
        password='TestPass123!',
        display_name='Analytics Member 1',
        email_verified=True,
    )


@pytest.fixture
def analytics_member2(db):
    """Create another group member for analytics tests."""
    return User.objects.create_user(
        email='analytics_member2@example.com',
        password='TestPass123!',
        display_name='Analytics Member 2',
        email_verified=True,
    )


@pytest.fixture
def analytics_outsider(db):
    """Create a user not in any group."""
    return User.objects.create_user(
        email='analytics_outsider@example.com',
        password='TestPass123!',
        display_name='Analytics Outsider',
        email_verified=True,
    )


@pytest.fixture
def analytics_user_client(api_client, analytics_user):
    """Return API client authenticated as analytics user."""
    refresh = RefreshToken.for_user(analytics_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


@pytest.fixture
def analytics_member1_client(api_client, analytics_member1):
    """Return API client authenticated as member1."""
    refresh = RefreshToken.for_user(analytics_member1)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


@pytest.fixture
def analytics_outsider_client(api_client, analytics_outsider):
    """Return API client authenticated as outsider."""
    refresh = RefreshToken.for_user(analytics_outsider)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


# =============================================================================
# Groups
# =============================================================================

@pytest.fixture
def analytics_group(db, analytics_user, analytics_member1, analytics_member2):
    """Create a group with 3 members for analytics tests."""
    group = Group.objects.create(
        name='Analytics Test Group',
        description='Group for analytics testing',
        is_private=True,
        owner=analytics_user,
    )
    GroupMembership.objects.create(
        user=analytics_user,
        group=group,
        role=GroupRole.OWNER,
    )
    GroupMembership.objects.create(
        user=analytics_member1,
        group=group,
        role=GroupRole.MEMBER,
    )
    GroupMembership.objects.create(
        user=analytics_member2,
        group=group,
        role=GroupRole.MEMBER,
    )
    return group


# =============================================================================
# Coffee Beans
# =============================================================================

@pytest.fixture
def analytics_bean1(db, analytics_user):
    """Create a coffee bean with high rating."""
    bean = CoffeeBean.objects.create(
        name='Ethiopia Yirgacheffe Premium',
        roastery_name='Top Roasters',
        origin_country='Ethiopia',
        roast_profile='light',
        created_by=analytics_user,
    )
    # Set initial stats (simulating reviews)
    bean.avg_rating = Decimal('4.5')
    bean.review_count = 5
    bean.save()
    return bean


@pytest.fixture
def analytics_bean2(db, analytics_user):
    """Create another coffee bean with moderate rating."""
    bean = CoffeeBean.objects.create(
        name='Colombia Supremo',
        roastery_name='Coffee Masters',
        origin_country='Colombia',
        roast_profile='medium',
        created_by=analytics_user,
    )
    bean.avg_rating = Decimal('4.0')
    bean.review_count = 3
    bean.save()
    return bean


@pytest.fixture
def analytics_bean3(db, analytics_user):
    """Create a third coffee bean with lower rating."""
    bean = CoffeeBean.objects.create(
        name='Brazil Santos',
        roastery_name='Bean World',
        origin_country='Brazil',
        roast_profile='dark',
        created_by=analytics_user,
    )
    bean.avg_rating = Decimal('3.5')
    bean.review_count = 10
    bean.save()
    return bean


@pytest.fixture
def analytics_bean_no_reviews(db, analytics_user):
    """Create a coffee bean with no reviews."""
    return CoffeeBean.objects.create(
        name='New Bean',
        roastery_name='New Roastery',
        origin_country='Kenya',
        roast_profile='light',
        created_by=analytics_user,
    )


# =============================================================================
# Tags
# =============================================================================

@pytest.fixture
def analytics_tag_fruity(db):
    """Create a fruity taste tag."""
    return Tag.objects.create(name='fruity', category='flavor')


@pytest.fixture
def analytics_tag_chocolate(db):
    """Create a chocolate taste tag."""
    return Tag.objects.create(name='chocolate', category='flavor')


@pytest.fixture
def analytics_tag_floral(db):
    """Create a floral taste tag."""
    return Tag.objects.create(name='floral', category='aroma')


# =============================================================================
# Reviews
# =============================================================================

@pytest.fixture
def analytics_bean_extra(db, analytics_user):
    """Create an extra coffee bean for multiple reviews (same origin as bean1)."""
    bean = CoffeeBean.objects.create(
        name='Ethiopia Harrar',
        roastery_name='Highland Roasters',
        origin_country='Ethiopia',  # Same as bean1 for origin preference
        roast_profile='light',
        created_by=analytics_user,
    )
    bean.avg_rating = Decimal('4.2')
    bean.review_count = 2
    bean.save()
    return bean


@pytest.fixture
def analytics_reviews(
    db, analytics_user, analytics_bean1, analytics_bean2, analytics_bean_extra,
    analytics_tag_fruity, analytics_tag_chocolate, analytics_tag_floral
):
    """Create multiple reviews for taste profile analysis."""
    # Review 1: Ethiopia (light roast) - fruity, floral
    review1 = Review.objects.create(
        coffeebean=analytics_bean1,
        author=analytics_user,
        rating=5,
        notes='Amazing fruity and floral notes!',
        brew_method='filter',
        context='personal',
    )
    review1.taste_tags.add(analytics_tag_fruity, analytics_tag_floral)

    # Review 2: Guatemala (light roast) - fruity
    review2 = Review.objects.create(
        coffeebean=analytics_bean_extra,
        author=analytics_user,
        rating=4,
        notes='Great fruity coffee',
        brew_method='espresso',
        context='personal',
    )
    review2.taste_tags.add(analytics_tag_fruity)

    # Review 3: Colombia (medium roast) - chocolate
    review3 = Review.objects.create(
        coffeebean=analytics_bean2,
        author=analytics_user,
        rating=4,
        notes='Nice chocolate undertones',
        brew_method='filter',
        context='personal',
    )
    review3.taste_tags.add(analytics_tag_chocolate)

    return [review1, review2, review3]


# =============================================================================
# Purchases with Payment Shares
# =============================================================================

@pytest.fixture
def analytics_personal_purchase(db, analytics_user, analytics_bean1):
    """Create a personal purchase with paid share."""
    purchase = PurchaseRecord.objects.create(
        coffeebean=analytics_bean1,
        bought_by=analytics_user,
        total_price_czk=Decimal('500.00'),
        currency='CZK',
        package_weight_grams=500,
        date=date.today() - timedelta(days=10),
        purchase_location='Local Coffee Shop',
    )
    # Create paid payment share for user
    PaymentShare.objects.create(
        purchase=purchase,
        user=analytics_user,
        amount_czk=Decimal('500.00'),
        status=PaymentStatus.PAID,
    )
    purchase.total_collected_czk = Decimal('500.00')
    purchase.is_fully_paid = True
    purchase.save()
    return purchase


@pytest.fixture
def analytics_group_purchase(
    db, analytics_group, analytics_user, analytics_member1,
    analytics_member2, analytics_bean2
):
    """Create a group purchase with payment shares for all members."""
    purchase = PurchaseRecord.objects.create(
        group=analytics_group,
        coffeebean=analytics_bean2,
        bought_by=analytics_user,
        total_price_czk=Decimal('900.00'),
        currency='CZK',
        package_weight_grams=1000,
        date=date.today() - timedelta(days=5),
        purchase_location='Specialty Store',
    )
    # Create payment shares (300 CZK each)
    PaymentShare.objects.create(
        purchase=purchase,
        user=analytics_user,
        amount_czk=Decimal('300.00'),
        status=PaymentStatus.PAID,
    )
    PaymentShare.objects.create(
        purchase=purchase,
        user=analytics_member1,
        amount_czk=Decimal('300.00'),
        status=PaymentStatus.PAID,
    )
    PaymentShare.objects.create(
        purchase=purchase,
        user=analytics_member2,
        amount_czk=Decimal('300.00'),
        status=PaymentStatus.PAID,
    )
    purchase.total_collected_czk = Decimal('900.00')
    purchase.is_fully_paid = True
    purchase.save()
    return purchase


@pytest.fixture
def analytics_old_purchase(db, analytics_user, analytics_bean1):
    """Create an older purchase for time series testing."""
    purchase = PurchaseRecord.objects.create(
        coffeebean=analytics_bean1,
        bought_by=analytics_user,
        total_price_czk=Decimal('300.00'),
        currency='CZK',
        package_weight_grams=250,
        date=date.today() - timedelta(days=60),
        purchase_location='Online Store',
    )
    PaymentShare.objects.create(
        purchase=purchase,
        user=analytics_user,
        amount_czk=Decimal('300.00'),
        status=PaymentStatus.PAID,
    )
    purchase.total_collected_czk = Decimal('300.00')
    purchase.is_fully_paid = True
    purchase.save()
    return purchase


@pytest.fixture
def analytics_all_data(
    analytics_user, analytics_member1, analytics_member2, analytics_outsider,
    analytics_group, analytics_bean1, analytics_bean2, analytics_bean3,
    analytics_reviews, analytics_personal_purchase, analytics_group_purchase,
    analytics_old_purchase
):
    """Fixture that ensures all analytics test data is created."""
    return {
        'user': analytics_user,
        'member1': analytics_member1,
        'member2': analytics_member2,
        'outsider': analytics_outsider,
        'group': analytics_group,
        'beans': [analytics_bean1, analytics_bean2, analytics_bean3],
        'reviews': analytics_reviews,
        'personal_purchase': analytics_personal_purchase,
        'group_purchase': analytics_group_purchase,
        'old_purchase': analytics_old_purchase,
    }

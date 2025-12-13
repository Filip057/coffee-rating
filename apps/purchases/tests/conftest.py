import pytest
from decimal import Decimal
from datetime import date
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from apps.accounts.models import User
from apps.beans.models import CoffeeBean, CoffeeBeanVariant
from apps.groups.models import Group, GroupMembership, GroupRole
from apps.purchases.models import PurchaseRecord, PaymentShare, PaymentStatus


@pytest.fixture
def api_client():
    """Return an unauthenticated API client."""
    return APIClient()


@pytest.fixture
def purchase_buyer(db):
    """Create and return a test user who buys coffee."""
    return User.objects.create_user(
        email='buyer@example.com',
        password='TestPass123!',
        display_name='Coffee Buyer',
        email_verified=True,
    )


@pytest.fixture
def purchase_member1(db):
    """Create and return a group member."""
    return User.objects.create_user(
        email='member1@example.com',
        password='TestPass123!',
        display_name='Member One',
        email_verified=True,
    )


@pytest.fixture
def purchase_member2(db):
    """Create and return another group member."""
    return User.objects.create_user(
        email='member2@example.com',
        password='TestPass123!',
        display_name='Member Two',
        email_verified=True,
    )


@pytest.fixture
def purchase_member3(db):
    """Create and return a third group member."""
    return User.objects.create_user(
        email='member3@example.com',
        password='TestPass123!',
        display_name='Member Three',
        email_verified=True,
    )


@pytest.fixture
def purchase_outsider(db):
    """Create and return a user not in any group."""
    return User.objects.create_user(
        email='outsider@example.com',
        password='TestPass123!',
        display_name='Outsider User',
        email_verified=True,
    )


@pytest.fixture
def buyer_client(api_client, purchase_buyer):
    """Return API client authenticated as buyer."""
    refresh = RefreshToken.for_user(purchase_buyer)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


@pytest.fixture
def member1_client(api_client, purchase_member1):
    """Return API client authenticated as member1."""
    refresh = RefreshToken.for_user(purchase_member1)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


@pytest.fixture
def member2_client(api_client, purchase_member2):
    """Return API client authenticated as member2."""
    refresh = RefreshToken.for_user(purchase_member2)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


@pytest.fixture
def outsider_client(api_client, purchase_outsider):
    """Return API client authenticated as outsider."""
    refresh = RefreshToken.for_user(purchase_outsider)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


@pytest.fixture
def purchase_group(db, purchase_buyer, purchase_member1, purchase_member2):
    """Create a group with buyer as owner and two members."""
    group = Group.objects.create(
        name='Coffee Buying Club',
        description='A group for sharing coffee purchases',
        is_private=True,
        owner=purchase_buyer,
    )
    GroupMembership.objects.create(
        user=purchase_buyer,
        group=group,
        role=GroupRole.OWNER,
    )
    GroupMembership.objects.create(
        user=purchase_member1,
        group=group,
        role=GroupRole.MEMBER,
    )
    GroupMembership.objects.create(
        user=purchase_member2,
        group=group,
        role=GroupRole.MEMBER,
    )
    return group


@pytest.fixture
def purchase_coffeebean(db, purchase_buyer):
    """Create a test coffee bean."""
    return CoffeeBean.objects.create(
        name='Ethiopia Sidamo',
        roastery_name='Local Roasters',
        origin_country='Ethiopia',
        roast_profile='light',
        created_by=purchase_buyer,
    )


@pytest.fixture
def purchase_variant(db, purchase_coffeebean):
    """Create a test coffee bean variant."""
    return CoffeeBeanVariant.objects.create(
        coffeebean=purchase_coffeebean,
        weight_grams=250,
        price_czk=Decimal('299.00'),
        is_available=True,
    )


@pytest.fixture
def personal_purchase(db, purchase_buyer, purchase_coffeebean):
    """Create a personal (non-group) purchase."""
    return PurchaseRecord.objects.create(
        coffeebean=purchase_coffeebean,
        bought_by=purchase_buyer,
        total_price_czk=Decimal('299.00'),
        currency='CZK',
        package_weight_grams=250,
        date=date.today(),
        purchase_location='Local Coffee Shop',
        note='Great Ethiopian coffee!',
    )


@pytest.fixture
def group_purchase(db, purchase_group, purchase_buyer, purchase_coffeebean):
    """Create a group purchase without payment shares."""
    return PurchaseRecord.objects.create(
        group=purchase_group,
        coffeebean=purchase_coffeebean,
        bought_by=purchase_buyer,
        total_price_czk=Decimal('450.00'),
        currency='CZK',
        package_weight_grams=500,
        date=date.today(),
        purchase_location='Specialty Coffee Store',
        note='Group buy for the club',
    )


@pytest.fixture
def group_purchase_with_shares(db, group_purchase, purchase_buyer, purchase_member1, purchase_member2):
    """Create a group purchase with payment shares for 3 members."""
    # 450 CZK / 3 = 150 CZK each (even split)
    PaymentShare.objects.create(
        purchase=group_purchase,
        user=purchase_buyer,
        amount_czk=Decimal('150.00'),
        status=PaymentStatus.PAID,  # Buyer already paid
    )
    PaymentShare.objects.create(
        purchase=group_purchase,
        user=purchase_member1,
        amount_czk=Decimal('150.00'),
        status=PaymentStatus.UNPAID,
    )
    PaymentShare.objects.create(
        purchase=group_purchase,
        user=purchase_member2,
        amount_czk=Decimal('150.00'),
        status=PaymentStatus.UNPAID,
    )
    group_purchase.total_collected_czk = Decimal('150.00')
    group_purchase.save()
    return group_purchase


@pytest.fixture
def uneven_group_purchase(db, purchase_group, purchase_buyer, purchase_coffeebean):
    """Create a group purchase with uneven split (100 CZK / 3 = haléř test)."""
    purchase = PurchaseRecord.objects.create(
        group=purchase_group,
        coffeebean=purchase_coffeebean,
        bought_by=purchase_buyer,
        total_price_czk=Decimal('100.00'),
        currency='CZK',
        date=date.today(),
        note='Test uneven split',
    )
    return purchase


@pytest.fixture
def payment_share_unpaid(db, group_purchase, purchase_member1):
    """Create an unpaid payment share."""
    return PaymentShare.objects.create(
        purchase=group_purchase,
        user=purchase_member1,
        amount_czk=Decimal('150.00'),
        status=PaymentStatus.UNPAID,
    )


@pytest.fixture
def payment_share_paid(db, group_purchase, purchase_buyer):
    """Create a paid payment share."""
    return PaymentShare.objects.create(
        purchase=group_purchase,
        user=purchase_buyer,
        amount_czk=Decimal('150.00'),
        status=PaymentStatus.PAID,
    )

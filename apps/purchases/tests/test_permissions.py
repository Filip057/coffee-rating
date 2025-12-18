import pytest
from rest_framework.test import APIRequestFactory
from apps.purchases.permissions import (
    IsGroupMemberForPurchase,
    CanManagePurchase,
    CanMarkPaymentPaid,
    IsGroupMemberForShare,
)
from apps.purchases.models import PaymentShare, PaymentStatus


# =============================================================================
# IsGroupMemberForPurchase Tests
# =============================================================================

@pytest.mark.django_db
class TestIsGroupMemberForPurchase:
    """Tests for IsGroupMemberForPurchase permission class."""

    def test_owner_can_view_personal_purchase(self, purchase_buyer, personal_purchase):
        """Purchase buyer can view their own personal purchase."""
        factory = APIRequestFactory()
        request = factory.get('/')
        request.user = purchase_buyer

        permission = IsGroupMemberForPurchase()
        assert permission.has_object_permission(request, None, personal_purchase) is True

    def test_non_owner_cannot_view_personal_purchase(self, purchase_outsider, personal_purchase):
        """Non-owner cannot view someone else's personal purchase."""
        factory = APIRequestFactory()
        request = factory.get('/')
        request.user = purchase_outsider

        permission = IsGroupMemberForPurchase()
        assert permission.has_object_permission(request, None, personal_purchase) is False

    def test_buyer_can_view_group_purchase(self, purchase_buyer, group_purchase):
        """Buyer (group owner) can view their group purchase."""
        factory = APIRequestFactory()
        request = factory.get('/')
        request.user = purchase_buyer

        permission = IsGroupMemberForPurchase()
        assert permission.has_object_permission(request, None, group_purchase) is True

    def test_group_member_can_view_group_purchase(self, purchase_member1, group_purchase):
        """Group member can view group purchase."""
        factory = APIRequestFactory()
        request = factory.get('/')
        request.user = purchase_member1

        permission = IsGroupMemberForPurchase()
        assert permission.has_object_permission(request, None, group_purchase) is True

    def test_non_member_cannot_view_group_purchase(self, purchase_outsider, group_purchase):
        """Non-member cannot view group purchase."""
        factory = APIRequestFactory()
        request = factory.get('/')
        request.user = purchase_outsider

        permission = IsGroupMemberForPurchase()
        assert permission.has_object_permission(request, None, group_purchase) is False


# =============================================================================
# CanManagePurchase Tests
# =============================================================================

@pytest.mark.django_db
class TestCanManagePurchase:
    """Tests for CanManagePurchase permission class."""

    def test_buyer_can_manage_personal_purchase(self, purchase_buyer, personal_purchase):
        """Buyer can update/delete their own personal purchase."""
        factory = APIRequestFactory()
        request = factory.patch('/')
        request.user = purchase_buyer

        permission = CanManagePurchase()
        assert permission.has_object_permission(request, None, personal_purchase) is True

    def test_non_buyer_cannot_manage_personal_purchase(self, purchase_outsider, personal_purchase):
        """Non-buyer cannot manage someone else's personal purchase."""
        factory = APIRequestFactory()
        request = factory.patch('/')
        request.user = purchase_outsider

        permission = CanManagePurchase()
        assert permission.has_object_permission(request, None, personal_purchase) is False

    def test_buyer_can_manage_group_purchase(self, purchase_buyer, group_purchase):
        """Buyer can manage their group purchase."""
        factory = APIRequestFactory()
        request = factory.patch('/')
        request.user = purchase_buyer

        permission = CanManagePurchase()
        assert permission.has_object_permission(request, None, group_purchase) is True

    def test_group_owner_can_manage_purchase(self, purchase_buyer, group_purchase):
        """Group owner can manage any purchase in their group."""
        factory = APIRequestFactory()
        request = factory.patch('/')
        request.user = purchase_buyer  # Owner of the group

        permission = CanManagePurchase()
        assert permission.has_object_permission(request, None, group_purchase) is True

    def test_group_member_cannot_manage_others_purchase(self, purchase_member1, group_purchase):
        """Regular member cannot manage purchases they didn't create."""
        factory = APIRequestFactory()
        request = factory.patch('/')
        request.user = purchase_member1

        permission = CanManagePurchase()
        assert permission.has_object_permission(request, None, group_purchase) is False


# =============================================================================
# CanMarkPaymentPaid Tests
# =============================================================================

@pytest.mark.django_db
class TestCanMarkPaymentPaid:
    """Tests for CanMarkPaymentPaid permission class."""

    def test_user_can_mark_own_share_paid(self, purchase_member1, group_purchase_with_shares):
        """User can mark their own payment share as paid."""
        share = PaymentShare.objects.get(
            purchase=group_purchase_with_shares,
            user=purchase_member1
        )
        factory = APIRequestFactory()
        request = factory.post('/')
        request.user = purchase_member1

        permission = CanMarkPaymentPaid()
        assert permission.has_object_permission(request, None, share) is True

    def test_buyer_can_mark_any_share_paid(self, purchase_buyer, group_purchase_with_shares, purchase_member1):
        """Purchase buyer can mark any share in their purchase as paid."""
        share = PaymentShare.objects.get(
            purchase=group_purchase_with_shares,
            user=purchase_member1
        )
        factory = APIRequestFactory()
        request = factory.post('/')
        request.user = purchase_buyer

        permission = CanMarkPaymentPaid()
        assert permission.has_object_permission(request, None, share) is True

    def test_group_owner_can_mark_any_share_paid(self, purchase_buyer, group_purchase_with_shares, purchase_member1):
        """Group owner can mark any share in group purchase as paid."""
        share = PaymentShare.objects.get(
            purchase=group_purchase_with_shares,
            user=purchase_member1
        )
        factory = APIRequestFactory()
        request = factory.post('/')
        request.user = purchase_buyer  # Group owner

        permission = CanMarkPaymentPaid()
        assert permission.has_object_permission(request, None, share) is True

    def test_other_member_cannot_mark_share_paid(self, purchase_member2, group_purchase_with_shares, purchase_member1):
        """Other group members cannot mark someone else's share as paid."""
        share = PaymentShare.objects.get(
            purchase=group_purchase_with_shares,
            user=purchase_member1
        )
        factory = APIRequestFactory()
        request = factory.post('/')
        request.user = purchase_member2

        permission = CanMarkPaymentPaid()
        assert permission.has_object_permission(request, None, share) is False

    def test_outsider_cannot_mark_share_paid(self, purchase_outsider, group_purchase_with_shares, purchase_member1):
        """Non-member cannot mark shares in group purchases as paid."""
        share = PaymentShare.objects.get(
            purchase=group_purchase_with_shares,
            user=purchase_member1
        )
        factory = APIRequestFactory()
        request = factory.post('/')
        request.user = purchase_outsider

        permission = CanMarkPaymentPaid()
        assert permission.has_object_permission(request, None, share) is False


# =============================================================================
# IsGroupMemberForShare Tests
# =============================================================================

@pytest.mark.django_db
class TestIsGroupMemberForShare:
    """Tests for IsGroupMemberForShare permission class."""

    def test_share_owner_can_view_own_share(self, purchase_member1, group_purchase_with_shares):
        """User can view their own payment share."""
        share = PaymentShare.objects.get(
            purchase=group_purchase_with_shares,
            user=purchase_member1
        )
        factory = APIRequestFactory()
        request = factory.get('/')
        request.user = purchase_member1

        permission = IsGroupMemberForShare()
        assert permission.has_object_permission(request, None, share) is True

    def test_group_member_can_view_share(self, purchase_member2, group_purchase_with_shares, purchase_member1):
        """Group member can view other members' shares in same group."""
        share = PaymentShare.objects.get(
            purchase=group_purchase_with_shares,
            user=purchase_member1
        )
        factory = APIRequestFactory()
        request = factory.get('/')
        request.user = purchase_member2

        permission = IsGroupMemberForShare()
        assert permission.has_object_permission(request, None, share) is True

    def test_buyer_can_view_all_shares(self, purchase_buyer, group_purchase_with_shares, purchase_member1):
        """Purchase buyer can view all shares in their purchase."""
        share = PaymentShare.objects.get(
            purchase=group_purchase_with_shares,
            user=purchase_member1
        )
        factory = APIRequestFactory()
        request = factory.get('/')
        request.user = purchase_buyer

        permission = IsGroupMemberForShare()
        assert permission.has_object_permission(request, None, share) is True

    def test_outsider_cannot_view_share(self, purchase_outsider, group_purchase_with_shares, purchase_member1):
        """Non-member cannot view shares in group purchases."""
        share = PaymentShare.objects.get(
            purchase=group_purchase_with_shares,
            user=purchase_member1
        )
        factory = APIRequestFactory()
        request = factory.get('/')
        request.user = purchase_outsider

        permission = IsGroupMemberForShare()
        assert permission.has_object_permission(request, None, share) is False

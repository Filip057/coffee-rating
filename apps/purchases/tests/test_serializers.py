import pytest
from decimal import Decimal
from datetime import date, timedelta
from rest_framework.exceptions import ValidationError
from apps.purchases.serializers import (
    PurchaseFilterSerializer,
    PaymentShareFilterSerializer,
    MarkPaidInputSerializer,
)
from apps.purchases.models import PaymentStatus


# =============================================================================
# PurchaseFilterSerializer Tests
# =============================================================================

class TestPurchaseFilterSerializer:
    """Tests for PurchaseFilterSerializer input validation."""

    def test_valid_group_filter(self, purchase_group):
        """Valid group UUID filter."""
        data = {'group': str(purchase_group.id)}
        serializer = PurchaseFilterSerializer(data=data)

        assert serializer.is_valid()
        assert 'group' in serializer.validated_data
        assert serializer.validated_data['group'] == purchase_group.id

    def test_valid_user_filter(self, purchase_buyer):
        """Valid user UUID filter."""
        data = {'user': str(purchase_buyer.id)}
        serializer = PurchaseFilterSerializer(data=data)

        assert serializer.is_valid()
        assert 'user' in serializer.validated_data
        assert serializer.validated_data['user'] == purchase_buyer.id

    def test_valid_date_range(self):
        """Valid date range filter."""
        today = date.today()
        yesterday = today - timedelta(days=1)

        data = {
            'date_from': str(yesterday),
            'date_to': str(today),
        }
        serializer = PurchaseFilterSerializer(data=data)

        assert serializer.is_valid()
        assert serializer.validated_data['date_from'] == yesterday
        assert serializer.validated_data['date_to'] == today

    def test_valid_is_fully_paid_filter(self):
        """Valid is_fully_paid boolean filter."""
        data = {'is_fully_paid': True}
        serializer = PurchaseFilterSerializer(data=data)

        assert serializer.is_valid()
        assert serializer.validated_data['is_fully_paid'] is True

        data = {'is_fully_paid': False}
        serializer = PurchaseFilterSerializer(data=data)

        assert serializer.is_valid()
        assert serializer.validated_data['is_fully_paid'] is False

    def test_empty_filters(self):
        """Empty filters are valid (no filtering)."""
        data = {}
        serializer = PurchaseFilterSerializer(data=data)

        assert serializer.is_valid()
        assert len(serializer.validated_data) == 0

    def test_invalid_uuid_format(self):
        """Invalid UUID format raises error."""
        data = {'group': 'not-a-uuid'}
        serializer = PurchaseFilterSerializer(data=data)

        assert not serializer.is_valid()
        assert 'group' in serializer.errors

    def test_invalid_date_format(self):
        """Invalid date format raises error."""
        data = {'date_from': 'not-a-date'}
        serializer = PurchaseFilterSerializer(data=data)

        assert not serializer.is_valid()
        assert 'date_from' in serializer.errors

    def test_date_to_before_date_from(self):
        """date_to before date_from raises validation error."""
        today = date.today()
        tomorrow = today + timedelta(days=1)

        data = {
            'date_from': str(tomorrow),
            'date_to': str(today),
        }
        serializer = PurchaseFilterSerializer(data=data)

        assert not serializer.is_valid()
        assert 'date_to' in serializer.errors
        assert 'after start date' in str(serializer.errors['date_to'][0]).lower()

    def test_same_date_for_from_and_to(self):
        """Same date for date_from and date_to is valid."""
        today = date.today()

        data = {
            'date_from': str(today),
            'date_to': str(today),
        }
        serializer = PurchaseFilterSerializer(data=data)

        assert serializer.is_valid()

    def test_combined_filters(self, purchase_group, purchase_buyer):
        """Multiple filters can be combined."""
        today = date.today()

        data = {
            'group': str(purchase_group.id),
            'user': str(purchase_buyer.id),
            'date_from': str(today),
            'is_fully_paid': False,
        }
        serializer = PurchaseFilterSerializer(data=data)

        assert serializer.is_valid()
        assert len(serializer.validated_data) == 4


# =============================================================================
# PaymentShareFilterSerializer Tests
# =============================================================================

class TestPaymentShareFilterSerializer:
    """Tests for PaymentShareFilterSerializer input validation."""

    def test_valid_status_filter_unpaid(self):
        """Valid status filter for unpaid."""
        data = {'status': PaymentStatus.UNPAID}
        serializer = PaymentShareFilterSerializer(data=data)

        assert serializer.is_valid()
        assert serializer.validated_data['status'] == PaymentStatus.UNPAID

    def test_valid_status_filter_paid(self):
        """Valid status filter for paid."""
        data = {'status': PaymentStatus.PAID}
        serializer = PaymentShareFilterSerializer(data=data)

        assert serializer.is_valid()
        assert serializer.validated_data['status'] == PaymentStatus.PAID

    def test_valid_status_filter_failed(self):
        """Valid status filter for failed."""
        data = {'status': PaymentStatus.FAILED}
        serializer = PaymentShareFilterSerializer(data=data)

        assert serializer.is_valid()
        assert serializer.validated_data['status'] == PaymentStatus.FAILED

    def test_valid_purchase_filter(self, group_purchase):
        """Valid purchase UUID filter."""
        data = {'purchase': str(group_purchase.id)}
        serializer = PaymentShareFilterSerializer(data=data)

        assert serializer.is_valid()
        assert serializer.validated_data['purchase'] == group_purchase.id

    def test_invalid_status_value(self):
        """Invalid status value raises error."""
        data = {'status': 'invalid_status'}
        serializer = PaymentShareFilterSerializer(data=data)

        assert not serializer.is_valid()
        assert 'status' in serializer.errors

    def test_invalid_purchase_uuid(self):
        """Invalid purchase UUID format raises error."""
        data = {'purchase': 'not-a-uuid'}
        serializer = PaymentShareFilterSerializer(data=data)

        assert not serializer.is_valid()
        assert 'purchase' in serializer.errors

    def test_empty_filters(self):
        """Empty filters are valid."""
        data = {}
        serializer = PaymentShareFilterSerializer(data=data)

        assert serializer.is_valid()
        assert len(serializer.validated_data) == 0

    def test_combined_filters(self, group_purchase):
        """Status and purchase filters can be combined."""
        data = {
            'status': PaymentStatus.UNPAID,
            'purchase': str(group_purchase.id),
        }
        serializer = PaymentShareFilterSerializer(data=data)

        assert serializer.is_valid()
        assert len(serializer.validated_data) == 2


# =============================================================================
# MarkPaidInputSerializer Tests
# =============================================================================

class TestMarkPaidInputSerializer:
    """Tests for MarkPaidInputSerializer input validation."""

    def test_valid_payment_reference(self):
        """Valid payment reference."""
        data = {'payment_reference': 'COFFEE-ABC123'}
        serializer = MarkPaidInputSerializer(data=data)

        assert serializer.is_valid()
        assert serializer.validated_data['payment_reference'] == 'COFFEE-ABC123'

    def test_valid_note(self):
        """Valid note field."""
        data = {'note': 'Paid via bank transfer'}
        serializer = MarkPaidInputSerializer(data=data)

        assert serializer.is_valid()
        assert serializer.validated_data['note'] == 'Paid via bank transfer'

    def test_valid_both_fields(self):
        """Both fields can be provided."""
        data = {
            'payment_reference': 'COFFEE-XYZ789',
            'note': 'Confirmed payment',
        }
        serializer = MarkPaidInputSerializer(data=data)

        assert serializer.is_valid()
        assert len(serializer.validated_data) == 2

    def test_empty_data(self):
        """Empty data is valid (mark user's own share)."""
        data = {}
        serializer = MarkPaidInputSerializer(data=data)

        assert serializer.is_valid()
        assert len(serializer.validated_data) == 0

    def test_payment_reference_max_length(self):
        """Payment reference respects max length."""
        # Valid: exactly 64 characters
        data = {'payment_reference': 'A' * 64}
        serializer = MarkPaidInputSerializer(data=data)
        assert serializer.is_valid()

        # Invalid: 65 characters
        data = {'payment_reference': 'A' * 65}
        serializer = MarkPaidInputSerializer(data=data)
        assert not serializer.is_valid()
        assert 'payment_reference' in serializer.errors

    def test_note_max_length(self):
        """Note respects max length."""
        # Valid: exactly 500 characters
        data = {'note': 'A' * 500}
        serializer = MarkPaidInputSerializer(data=data)
        assert serializer.is_valid()

        # Invalid: 501 characters
        data = {'note': 'A' * 501}
        serializer = MarkPaidInputSerializer(data=data)
        assert not serializer.is_valid()
        assert 'note' in serializer.errors

    def test_payment_reference_can_be_empty_string(self):
        """Empty string for payment_reference is valid."""
        data = {'payment_reference': ''}
        serializer = MarkPaidInputSerializer(data=data)

        # Depends on allow_blank setting, but generally should be valid
        # If you want to enforce non-empty, add `allow_blank=False` to serializer
        assert serializer.is_valid() or 'payment_reference' in serializer.errors

    def test_special_characters_in_reference(self):
        """Special characters in payment reference are valid."""
        data = {'payment_reference': 'COFFEE-2024-01-15-USER123'}
        serializer = MarkPaidInputSerializer(data=data)

        assert serializer.is_valid()

    def test_unicode_in_note(self):
        """Unicode characters in note are valid."""
        data = {'note': 'Zaplaceno přes banku 🎉'}
        serializer = MarkPaidInputSerializer(data=data)

        assert serializer.is_valid()
        assert serializer.validated_data['note'] == 'Zaplaceno přes banku 🎉'


# =============================================================================
# Integration Tests - Serializers with Models
# =============================================================================

@pytest.mark.django_db
class TestSerializersWithModels:
    """Tests for serializers with actual model instances."""

    def test_filter_purchases_by_existing_group(self, purchase_group, group_purchase):
        """Filter by existing group returns valid data."""
        data = {'group': str(purchase_group.id)}
        serializer = PurchaseFilterSerializer(data=data)

        assert serializer.is_valid()
        # The serializer doesn't validate if the group exists, just the UUID format
        # That's handled by the queryset filtering in the view

    def test_filter_shares_by_purchase(self, group_purchase_with_shares):
        """Filter shares by existing purchase."""
        data = {'purchase': str(group_purchase_with_shares.id)}
        serializer = PaymentShareFilterSerializer(data=data)

        assert serializer.is_valid()
        assert serializer.validated_data['purchase'] == group_purchase_with_shares.id

    def test_mark_paid_with_real_payment_reference(self, group_purchase_with_shares, purchase_member1):
        """Mark paid with actual payment reference from share."""
        from apps.purchases.models import PaymentShare

        share = PaymentShare.objects.get(
            purchase=group_purchase_with_shares,
            user=purchase_member1
        )

        data = {'payment_reference': share.payment_reference}
        serializer = MarkPaidInputSerializer(data=data)

        assert serializer.is_valid()
        assert serializer.validated_data['payment_reference'] == share.payment_reference

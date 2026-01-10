from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid


class PaymentStatus(models.TextChoices):
    UNPAID = 'unpaid', 'Unpaid'
    PAID = 'paid', 'Paid'
    FAILED = 'failed', 'Failed'
    REFUNDED = 'refunded', 'Refunded'


# Purchase location choices
PURCHASE_LOCATIONS = [
    ('eshop', 'E-shop'),
    ('cafe', 'Kavarna'),
    ('roastery', 'Prazirna'),
    ('store', 'Prodejna'),
    ('other', 'Jine'),
]


class PurchaseBase(models.Model):
    """Abstract base model for all purchase types."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Coffee bean reference
    coffeebean = models.ForeignKey(
        'beans.CoffeeBean',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_purchases'
    )
    variant = models.ForeignKey(
        'beans.CoffeeBeanVariant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_purchases'
    )

    # Financial details
    total_price_czk = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    currency = models.CharField(max_length=3, default='CZK')

    # Package info
    package_weight_grams = models.PositiveIntegerField(null=True, blank=True)

    # Purchase metadata
    date = models.DateField()
    purchase_location = models.CharField(
        max_length=20,
        choices=PURCHASE_LOCATIONS,
        default='other'
    )
    eshop_url = models.URLField(blank=True)
    note = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class PersonalPurchase(PurchaseBase):
    """Personal coffee purchase - simple tracking for individual user."""

    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='personal_purchases'
    )

    class Meta:
        db_table = 'personal_purchases'
        indexes = [
            models.Index(fields=['user', 'date']),
            models.Index(fields=['date']),
            models.Index(fields=['coffeebean', 'date']),
        ]
        ordering = ['-date', '-created_at']

    def __str__(self):
        bean = self.coffeebean.name if self.coffeebean else "Unknown"
        return f"{self.user.email} - {bean} - {self.total_price_czk} CZK"


class GroupPurchase(PurchaseBase):
    """Group coffee purchase with payment splitting."""

    group = models.ForeignKey(
        'groups.Group',
        on_delete=models.CASCADE,
        related_name='purchases'
    )
    bought_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='group_purchases_bought'
    )

    # Payment tracking
    total_collected_czk = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    is_fully_paid = models.BooleanField(default=False)

    class Meta:
        db_table = 'group_purchases'
        indexes = [
            models.Index(fields=['group', 'date']),
            models.Index(fields=['bought_by', 'date']),
            models.Index(fields=['date']),
            models.Index(fields=['is_fully_paid']),
        ]
        ordering = ['-date', '-created_at']

    def __str__(self):
        bean = self.coffeebean.name if self.coffeebean else "Unknown"
        return f"Group: {self.group.name} - {bean} - {self.total_price_czk} CZK"

    def update_collection_status(self):
        """Recalculate collected amount and check if fully paid."""
        from django.db.models import Sum

        collected = self.payment_shares.filter(
            status=PaymentStatus.PAID
        ).aggregate(total=Sum('amount_czk'))['total'] or Decimal('0.00')

        self.total_collected_czk = collected
        self.is_fully_paid = (collected >= self.total_price_czk)
        self.save(update_fields=['total_collected_czk', 'is_fully_paid', 'updated_at'])

    def get_outstanding_balance(self):
        """Return unpaid amount."""
        return max(Decimal('0.00'), self.total_price_czk - self.total_collected_czk)


class PaymentShare(models.Model):
    """Individual payment share for a group purchase."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    purchase = models.ForeignKey(
        GroupPurchase,
        on_delete=models.CASCADE,
        related_name='payment_shares'
    )
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='payment_shares'
    )
    
    # Amount owed
    amount_czk = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    currency = models.CharField(max_length=3, default='CZK')
    
    # Payment tracking
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.UNPAID
    )
    
    # Unique reference for matching bank payments
    payment_reference = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        editable=False
    )
    
    # QR code for payment (SPD - Czech payment standard)
    qr_url = models.CharField(max_length=500, blank=True)
    qr_image_path = models.CharField(max_length=200, blank=True)
    
    # Payment confirmation
    paid_at = models.DateTimeField(null=True, blank=True)
    paid_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='confirmed_payments'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'payment_shares'
        unique_together = [['purchase', 'user']]
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['purchase', 'status']),
            models.Index(fields=['payment_reference']),
            models.Index(fields=['status', 'created_at']),
        ]
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.user.get_display_name()} owes {self.amount_czk} CZK ({self.status})"
    
    def save(self, *args, **kwargs):
        """Generate payment reference if not set."""
        if not self.payment_reference:
            self.payment_reference = self._generate_payment_reference()
        super().save(*args, **kwargs)
    
    def _generate_payment_reference(self):
        """Generate unique payment reference for bank matching."""
        import secrets
        # Format: COFFEE-<short-uuid>-<4-digit-random>
        short_id = str(self.id)[:8].upper()
        random_suffix = secrets.randbelow(10000)
        return f"COFFEE-{short_id}-{random_suffix:04d}"
    
    def can_be_marked_paid(self):
        """Check if payment share can be marked as paid."""
        return self.status in [PaymentStatus.UNPAID, PaymentStatus.FAILED]

    def mark_paid(self, paid_by_user=None):
        """Mark share as paid with validation."""
        from django.utils import timezone
        from .exceptions import InvalidStateTransitionError

        if not self.can_be_marked_paid():
            raise InvalidStateTransitionError(
                f"Cannot mark share as paid from status {self.status}"
            )

        self.status = PaymentStatus.PAID
        self.paid_at = timezone.now()
        self.paid_by = paid_by_user
        self.save(update_fields=['status', 'paid_at', 'paid_by', 'updated_at'])

        # Update parent purchase collection status
        self.purchase.update_collection_status()
    
    def mark_failed(self):
        """Mark payment as failed."""
        self.status = PaymentStatus.FAILED
        self.save(update_fields=['status', 'updated_at'])


class BankTransaction(models.Model):
    """Imported bank transactions for auto-reconciliation (optional)."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Bank details
    transaction_id = models.CharField(max_length=100, unique=True)
    date = models.DateField()
    amount_czk = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Payment matching
    variable_symbol = models.CharField(max_length=64, blank=True, db_index=True)
    message = models.TextField(blank=True)
    
    # Matching status
    matched_share = models.ForeignKey(
        PaymentShare,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bank_transactions'
    )
    is_matched = models.BooleanField(default=False)
    
    # Import metadata
    imported_at = models.DateTimeField(auto_now_add=True)
    raw_data = models.JSONField(blank=True, null=True)
    
    class Meta:
        db_table = 'bank_transactions'
        indexes = [
            models.Index(fields=['transaction_id']),
            models.Index(fields=['variable_symbol']),
            models.Index(fields=['is_matched', 'date']),
        ]
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.transaction_id} - {self.amount_czk} CZK"
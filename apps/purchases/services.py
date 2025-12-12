from decimal import Decimal, ROUND_DOWN
from django.db import transaction
from .models import PurchaseRecord, PaymentShare, PaymentStatus
from apps.groups.models import Group, GroupMembership


class PurchaseSplitService:
    """Service for creating group purchases with haléř-precise splitting."""
    
    @staticmethod
    def create_group_purchase(
        group_id,
        bought_by_user,
        total_price_czk,
        date,
        coffeebean=None,
        variant=None,
        package_weight_grams=None,
        note='',
        split_members=None  # List of user IDs, or None for all members
    ):
        """
        Create a group purchase and split payment among members.
        
        Uses haléř-precise arithmetic:
        1. Convert total to haléře (total_czk * 100)
        2. Calculate base share per member (floor division)
        3. Distribute remainder (1 haléř each) to first K members
        4. Convert back to CZK (divide by 100)
        
        Args:
            group_id: Group UUID
            bought_by_user: User who made the purchase
            total_price_czk: Total purchase price (Decimal)
            date: Purchase date
            coffeebean: CoffeeBean instance (optional)
            variant: CoffeeBeanVariant instance (optional)
            package_weight_grams: Package weight if custom (optional)
            note: Purchase notes
            split_members: List of user IDs to split among (None = all members)
        
        Returns:
            (PurchaseRecord, list[PaymentShare])
        """
        with transaction.atomic():
            # Validate group
            group = Group.objects.get(id=group_id)
            
            # Get participants
            if split_members:
                # Validate all users are members
                memberships = GroupMembership.objects.filter(
                    group=group,
                    user_id__in=split_members
                ).select_related('user')
            else:
                # All group members
                memberships = GroupMembership.objects.filter(
                    group=group
                ).select_related('user')
            
            participants = [m.user for m in memberships]
            
            if not participants:
                raise ValueError("No participants found for split")
            
            # Create purchase record
            purchase = PurchaseRecord.objects.create(
                group=group,
                bought_by=bought_by_user,
                total_price_czk=total_price_czk,
                date=date,
                coffeebean=coffeebean,
                variant=variant,
                package_weight_grams=package_weight_grams,
                note=note,
                currency='CZK'
            )
            
            # Calculate splits with haléř precision
            shares_data = PurchaseSplitService._calculate_splits(
                total_price_czk,
                participants
            )
            
            # Create payment shares
            payment_shares = []
            for user, amount in shares_data:
                share = PaymentShare.objects.create(
                    purchase=purchase,
                    user=user,
                    amount_czk=amount,
                    currency='CZK',
                    status=PaymentStatus.UNPAID
                )
                payment_shares.append(share)
            
            return purchase, payment_shares
    
    @staticmethod
    def _calculate_splits(total_czk, participants):
        """
        Split amount with haléř precision (no rounding errors).
        
        Algorithm:
        1. Convert to haléře: total_halere = int(total_czk * 100)
        2. Base share: base = total_halere // N
        3. Remainder: remainder = total_halere % N
        4. First 'remainder' participants get (base + 1) haléře
        5. Rest get 'base' haléře
        6. Convert back to CZK: amount_czk = halere / 100
        
        Example:
            100.00 CZK / 3 people
            = 10000 haléře / 3
            = 3333 haléře each + 1 haléř remainder
            = [3334, 3333, 3333] haléře
            = [33.34, 33.33, 33.33] CZK
            Total: 100.00 CZK (exact!)
        
        Returns:
            List of (user, amount_czk) tuples
        """
        if not participants:
            raise ValueError("At least one participant required")
        
        # Convert to haléře (1 CZK = 100 haléř)
        total_halere = int(total_czk * 100)
        num_participants = len(participants)
        
        # Base share and remainder
        base_halere = total_halere // num_participants
        remainder_halere = total_halere % num_participants
        
        # Distribute shares
        shares = []
        for i, user in enumerate(participants):
            # First 'remainder' participants get +1 haléř
            if i < remainder_halere:
                user_halere = base_halere + 1
            else:
                user_halere = base_halere
            
            # Convert back to CZK with exact precision
            amount_czk = Decimal(user_halere) / Decimal(100)
            shares.append((user, amount_czk))
        
        # Verification (safety check)
        total_check = sum(amount for _, amount in shares)
        if total_check != total_czk:
            raise ValueError(
                f"Split calculation error: {total_check} != {total_czk}"
            )
        
        return shares
    
    @staticmethod
    def reconcile_payment(share_id, paid_by_user, method='manual'):
        """
        Mark a payment share as paid.
        
        Args:
            share_id: PaymentShare UUID
            paid_by_user: User confirming payment
            method: 'manual', 'bank_import', 'webhook'
        
        Returns:
            Updated PaymentShare
        """
        with transaction.atomic():
            share = PaymentShare.objects.select_for_update().get(id=share_id)
            
            if share.status == PaymentStatus.PAID:
                raise ValueError("Share already marked as paid")
            
            share.mark_paid(paid_by_user=paid_by_user)
            
            return share
    
    @staticmethod
    def get_purchase_summary(purchase_id):
        """Get detailed summary of purchase and payment status."""
        purchase = PurchaseRecord.objects.prefetch_related(
            'payment_shares__user'
        ).get(id=purchase_id)
        
        shares = purchase.payment_shares.all()
        
        paid_shares = [s for s in shares if s.status == PaymentStatus.PAID]
        unpaid_shares = [s for s in shares if s.status == PaymentStatus.UNPAID]
        
        return {
            'purchase': purchase,
            'total_amount': purchase.total_price_czk,
            'collected_amount': purchase.total_collected_czk,
            'outstanding_amount': purchase.get_outstanding_balance(),
            'is_fully_paid': purchase.is_fully_paid,
            'total_shares': len(shares),
            'paid_count': len(paid_shares),
            'unpaid_count': len(unpaid_shares),
            'paid_shares': paid_shares,
            'unpaid_shares': unpaid_shares,
        }


class SPDPaymentGenerator:
    """
    Generate SPD QR codes for Czech bank payments.
    
    SPD (Short Payment Descriptor) is a Czech standard for payment QR codes.
    Format: SPD*1.0*ACC:<IBAN>*AM:<amount>*CC:CZK*MSG:<message>*X-VS:<variable_symbol>
    """
    
    @staticmethod
    def generate_spd_string(
        iban,
        amount_czk,
        variable_symbol,
        message='',
        recipient_name=''
    ):
        """
        Generate SPD payment string for QR code.
        
        Args:
            iban: Bank account IBAN
            amount_czk: Payment amount
            variable_symbol: Payment reference/VS
            message: Optional payment message
            recipient_name: Payee name
        
        Returns:
            SPD formatted string
        """
        parts = [
            'SPD*1.0',
            f'ACC:{iban}',
            f'AM:{amount_czk:.2f}',
            'CC:CZK',
        ]
        
        if recipient_name:
            parts.append(f'RN:{recipient_name}')
        
        if message:
            # Sanitize message (SPD only allows specific characters)
            clean_msg = ''.join(c for c in message if c.isalnum() or c in ' -.,')
            parts.append(f'MSG:{clean_msg}')
        
        if variable_symbol:
            parts.append(f'X-VS:{variable_symbol}')
        
        return '*'.join(parts)
    
    @staticmethod
    def generate_qr_image(spd_string, output_path=None):
        """
        Generate QR code image from SPD string.
        
        Args:
            spd_string: SPD formatted payment string
            output_path: File path to save image (optional)
        
        Returns:
            QR code image (PIL Image) or path if output_path provided
        """
        import qrcode
        from io import BytesIO
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(spd_string)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        if output_path:
            img.save(output_path)
            return output_path
        
        return img
    
    @staticmethod
    def generate_for_payment_share(share, bank_iban, recipient_name=''):
        """
        Generate QR code for a PaymentShare.
        
        Args:
            share: PaymentShare instance
            bank_iban: Recipient bank IBAN
            recipient_name: Recipient name for display
        
        Returns:
            SPD string and QR image path
        """
        from django.conf import settings
        import os
        
        # Generate SPD string
        spd_string = SPDPaymentGenerator.generate_spd_string(
            iban=bank_iban,
            amount_czk=share.amount_czk,
            variable_symbol=share.payment_reference,
            message=f"Coffee purchase share - {share.purchase.coffeebean.name if share.purchase.coffeebean else 'Coffee'}",
            recipient_name=recipient_name
        )
        
        # Generate QR image
        qr_filename = f"qr_{share.payment_reference}.png"
        qr_path = os.path.join(settings.MEDIA_ROOT, 'qr_codes', qr_filename)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(qr_path), exist_ok=True)
        
        SPDPaymentGenerator.generate_qr_image(spd_string, qr_path)
        
        # Update share with QR info
        share.qr_url = spd_string
        share.qr_image_path = f'qr_codes/{qr_filename}'
        share.save(update_fields=['qr_url', 'qr_image_path'])
        
        return spd_string, qr_path
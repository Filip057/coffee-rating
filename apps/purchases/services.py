"""
Purchase Services Module
=========================

This module provides business logic services for purchase management,
including haléř-precise payment splitting and Czech SPD QR code generation.

Classes:
    PurchaseSplitService: Handles group purchase creation and payment reconciliation.
    SPDPaymentGenerator: Generates Czech SPD format QR codes for bank payments.

Example:
    Creating a group purchase with automatic splitting::

        from apps.purchases.services import PurchaseSplitService
        from decimal import Decimal

        purchase, shares = PurchaseSplitService.create_group_purchase(
            group_id=group.id,
            bought_by_user=current_user,
            total_price_czk=Decimal('900.00'),
            date=date.today(),
            coffeebean=ethiopia_bean,
        )

        # Each member gets a PaymentShare with haléř-precise amount
        for share in shares:
            print(f"{share.user.email}: {share.amount_czk} CZK")
"""

from decimal import Decimal, ROUND_DOWN
from django.db import transaction
from .models import PurchaseRecord, PaymentShare, PaymentStatus
from apps.groups.models import Group, GroupMembership


class PurchaseSplitService:
    """
    Service for creating group purchases with haléř-precise payment splitting.

    This service handles the business logic for group coffee purchases,
    ensuring that payment amounts are split with exact precision (no rounding
    errors) using integer haléř arithmetic.

    The haléř is the smallest Czech currency unit (1 CZK = 100 haléř).
    By converting to haléře, performing integer division, and distributing
    remainders, we guarantee that splits always sum exactly to the total.

    Methods:
        create_group_purchase: Create a purchase and split among members.
        reconcile_payment: Mark a payment share as paid.
        get_purchase_summary: Get detailed payment status for a purchase.

    Example:
        Basic group purchase::

            purchase, shares = PurchaseSplitService.create_group_purchase(
                group_id=group.id,
                bought_by_user=buyer,
                total_price_czk=Decimal('100.00'),
                date=date.today(),
            )
            # With 3 members: shares are 33.34, 33.33, 33.33 CZK

        Purchase with specific members::

            purchase, shares = PurchaseSplitService.create_group_purchase(
                group_id=group.id,
                bought_by_user=buyer,
                total_price_czk=Decimal('500.00'),
                date=date.today(),
                split_members=[user1.id, user2.id],  # Only these 2 users
            )
    """
    
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

        This method creates a PurchaseRecord and automatically generates
        PaymentShare records for each participant with haléř-precise amounts.

        The splitting algorithm ensures no rounding errors:
            1. Convert total to haléře (total_czk * 100)
            2. Calculate base share per member (floor division)
            3. Distribute remainder (1 haléř each) to first K members
            4. Convert back to CZK (divide by 100)

        Args:
            group_id (UUID): The group's unique identifier.
            bought_by_user (User): The user who made the purchase.
            total_price_czk (Decimal): Total purchase price in CZK.
            date (date): The date of purchase.
            coffeebean (CoffeeBean, optional): The purchased coffee bean.
                Defaults to None.
            variant (CoffeeBeanVariant, optional): The specific variant/package.
                Defaults to None.
            package_weight_grams (int, optional): Package weight in grams.
                If not provided, uses variant.package_weight_grams if available.
                Defaults to None.
            note (str, optional): Purchase notes or comments.
                Defaults to empty string.
            split_members (list[UUID], optional): List of user IDs to split among.
                If None, splits among all group members.
                Defaults to None.

        Returns:
            tuple: A tuple containing:
                - PurchaseRecord: The created purchase record.
                - list[PaymentShare]: List of created payment shares.

        Raises:
            Group.DoesNotExist: If the group_id doesn't exist.
            ValueError: If no participants are found for splitting.

        Example:
            Split among all members::

                purchase, shares = PurchaseSplitService.create_group_purchase(
                    group_id=group.id,
                    bought_by_user=request.user,
                    total_price_czk=Decimal('900.00'),
                    date=date.today(),
                    coffeebean=bean,
                    variant=variant,
                )

            Split among specific members::

                purchase, shares = PurchaseSplitService.create_group_purchase(
                    group_id=group.id,
                    bought_by_user=request.user,
                    total_price_czk=Decimal('600.00'),
                    date=date.today(),
                    split_members=[user1.id, user2.id],
                )

        Note:
            This method is wrapped in a database transaction. If any step
            fails, all changes are rolled back.
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

        This is the core algorithm for precise payment splitting. It converts
        the amount to the smallest currency unit (haléře), performs integer
        arithmetic, and distributes any remainder evenly.

        Algorithm:
            1. Convert to haléře: ``total_halere = int(total_czk * 100)``
            2. Base share: ``base = total_halere // N``
            3. Remainder: ``remainder = total_halere % N``
            4. First 'remainder' participants get ``(base + 1)`` haléře
            5. Rest get 'base' haléře
            6. Convert back to CZK: ``amount_czk = halere / 100``

        Args:
            total_czk (Decimal): The total amount to split in CZK.
            participants (list[User]): List of User objects to split among.

        Returns:
            list[tuple]: List of (User, Decimal) tuples where each tuple
            contains a user and their share amount in CZK.

        Raises:
            ValueError: If participants list is empty.
            ValueError: If calculated split doesn't sum to total (safety check).

        Example:
            100.00 CZK split among 3 people::

                >>> splits = PurchaseSplitService._calculate_splits(
                ...     Decimal('100.00'),
                ...     [user1, user2, user3]
                ... )
                >>> for user, amount in splits:
                ...     print(f"{user}: {amount}")
                user1: 33.34
                user2: 33.33
                user3: 33.33
                >>> sum(amount for _, amount in splits)
                Decimal('100.00')  # Exact!

        Note:
            The order of participants matters for remainder distribution.
            The first N participants (where N = remainder) receive 1 extra
            haléř each.
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
        Mark a payment share as paid and update the parent purchase.

        This method handles the reconciliation of a single payment share,
        updating its status to PAID and triggering the parent purchase's
        collection status update.

        Args:
            share_id (UUID): The payment share's unique identifier.
            paid_by_user (User): The user confirming/recording the payment.
                This is typically an admin or the group owner.
            method (str, optional): How the payment was reconciled.
                Options: 'manual', 'bank_import', 'webhook'.
                Defaults to 'manual'.

        Returns:
            PaymentShare: The updated payment share with status=PAID.

        Raises:
            PaymentShare.DoesNotExist: If the share_id doesn't exist.
            ValueError: If the share is already marked as paid.

        Example:
            Manual reconciliation::

                share = PurchaseSplitService.reconcile_payment(
                    share_id=payment_share.id,
                    paid_by_user=admin_user,
                    method='manual',
                )
                print(f"Share {share.id} marked as paid at {share.paid_at}")

        Note:
            This method uses SELECT FOR UPDATE to prevent race conditions
            when multiple reconciliation attempts happen simultaneously.
            It's wrapped in a database transaction.
        """
        with transaction.atomic():
            share = PaymentShare.objects.select_for_update().get(id=share_id)
            
            if share.status == PaymentStatus.PAID:
                raise ValueError("Share already marked as paid")
            
            share.mark_paid(paid_by_user=paid_by_user)
            
            return share
    
    @staticmethod
    def get_purchase_summary(purchase_id):
        """
        Get a detailed summary of a purchase and its payment status.

        This method provides a comprehensive overview of a purchase including
        the amounts collected, outstanding balance, and lists of paid/unpaid
        payment shares.

        Args:
            purchase_id (UUID): The purchase record's unique identifier.

        Returns:
            dict: A dictionary containing:
                - purchase (PurchaseRecord): The purchase object.
                - total_amount (Decimal): Total purchase price in CZK.
                - collected_amount (Decimal): Sum of paid shares in CZK.
                - outstanding_amount (Decimal): Remaining amount to collect.
                - is_fully_paid (bool): Whether all shares are paid.
                - total_shares (int): Total number of payment shares.
                - paid_count (int): Number of paid shares.
                - unpaid_count (int): Number of unpaid shares.
                - paid_shares (list[PaymentShare]): List of paid shares.
                - unpaid_shares (list[PaymentShare]): List of unpaid shares.

        Raises:
            PurchaseRecord.DoesNotExist: If the purchase_id doesn't exist.

        Example:
            Getting purchase status::

                summary = PurchaseSplitService.get_purchase_summary(purchase.id)
                print(f"Collected: {summary['collected_amount']} / {summary['total_amount']}")
                print(f"Outstanding: {summary['outstanding_amount']}")
                print(f"Paid: {summary['paid_count']}/{summary['total_shares']}")
        """
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

    SPD (Short Payment Descriptor) is a Czech standard for encoding payment
    information into QR codes. When scanned by a Czech banking app, the QR
    code pre-fills all payment details.

    Format::

        SPD*1.0*ACC:<IBAN>*AM:<amount>*CC:CZK*MSG:<message>*X-VS:<variable_symbol>

    Fields:
        - SPD*1.0: Version identifier
        - ACC: Bank account in IBAN format
        - AM: Amount (decimal)
        - CC: Currency code (CZK)
        - RN: Recipient name (optional)
        - MSG: Message/note (optional)
        - X-VS: Variable symbol for payment matching (optional)

    Methods:
        generate_spd_string: Create an SPD format string.
        generate_qr_image: Generate a QR code image from SPD string.
        generate_for_payment_share: Full generation for a PaymentShare.

    Example:
        Basic QR code generation::

            spd = SPDPaymentGenerator.generate_spd_string(
                iban='CZ6508000000192000145399',
                amount_czk=Decimal('300.00'),
                variable_symbol='COFFEE-ABC123-4567',
                message='Coffee purchase',
                recipient_name='Coffee Group',
            )
            # spd = "SPD*1.0*ACC:CZ6508000000192000145399*AM:300.00*CC:CZK*..."

            image = SPDPaymentGenerator.generate_qr_image(spd, 'qr_payment.png')

    Note:
        Requires the ``qrcode`` library with PIL support.
        Install with: ``pip install qrcode[pil]``

    See Also:
        https://qr-platba.cz/pro-vyvojare/specifikace-formatu/
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
        Generate an SPD format payment string for QR code encoding.

        This method creates a properly formatted SPD string that can be
        encoded into a QR code for Czech banking apps.

        Args:
            iban (str): Bank account IBAN (e.g., 'CZ6508000000192000145399').
            amount_czk (Decimal | float): Payment amount in CZK.
            variable_symbol (str): Payment reference/variable symbol for
                matching the payment to the correct record.
            message (str, optional): Payment message or note.
                Will be sanitized to remove special characters.
                Defaults to empty string.
            recipient_name (str, optional): Payee/recipient name for display.
                Defaults to empty string.

        Returns:
            str: SPD formatted string ready for QR code generation.

        Example:
            Generate SPD string::

                spd = SPDPaymentGenerator.generate_spd_string(
                    iban='CZ6508000000192000145399',
                    amount_czk=Decimal('299.00'),
                    variable_symbol='COFFEE-ABC12345-6789',
                    message='Ethiopia Yirgacheffe purchase',
                    recipient_name='Coffee Club',
                )
                # Result: "SPD*1.0*ACC:CZ6508000000192000145399*AM:299.00*CC:CZK*RN:Coffee Club*MSG:Ethiopia Yirgacheffe purchase*X-VS:COFFEE-ABC12345-6789"

        Note:
            The message is sanitized to only include alphanumeric characters,
            spaces, and basic punctuation (- . ,). This is required by the
            SPD specification.
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
        Generate a QR code image from an SPD payment string.

        This method creates a QR code image that can be scanned by Czech
        banking apps to pre-fill payment information.

        Args:
            spd_string (str): SPD formatted payment string as generated
                by generate_spd_string().
            output_path (str, optional): File path to save the QR code image.
                If provided, saves as PNG and returns the path.
                If None, returns the PIL Image object.
                Defaults to None.

        Returns:
            PIL.Image.Image | str: The QR code as a PIL Image object,
            or the output file path if output_path was provided.

        Raises:
            ImportError: If the qrcode library is not installed.

        Example:
            Generate and save QR code::

                spd = SPDPaymentGenerator.generate_spd_string(...)
                path = SPDPaymentGenerator.generate_qr_image(spd, 'payment_qr.png')
                print(f"QR code saved to {path}")

            Generate in-memory::

                spd = SPDPaymentGenerator.generate_spd_string(...)
                image = SPDPaymentGenerator.generate_qr_image(spd)
                # Use image directly (e.g., send in HTTP response)

        Note:
            The QR code uses error correction level M (15% recovery),
            which provides good balance between size and reliability.
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
        Generate a complete QR code for a PaymentShare and update the share.

        This is a convenience method that generates the SPD string, creates
        the QR code image, saves it to the media directory, and updates the
        PaymentShare record with the QR information.

        Args:
            share (PaymentShare): The payment share to generate QR for.
            bank_iban (str): Recipient bank account IBAN.
            recipient_name (str, optional): Recipient name for display
                in banking apps. Defaults to empty string.

        Returns:
            tuple: A tuple containing:
                - str: The SPD formatted payment string.
                - str: Path to the saved QR code image.

        Side Effects:
            - Creates QR code image file in MEDIA_ROOT/qr_codes/
            - Updates share.qr_url with the SPD string
            - Updates share.qr_image_path with the relative file path

        Example:
            Generate QR code for a share::

                spd_string, qr_path = SPDPaymentGenerator.generate_for_payment_share(
                    share=payment_share,
                    bank_iban='CZ6508000000192000145399',
                    recipient_name='Coffee Group',
                )
                print(f"QR saved to: {qr_path}")
                print(f"SPD string: {spd_string}")

                # The share is now updated:
                print(share.qr_url)  # SPD string
                print(share.qr_image_path)  # 'qr_codes/qr_COFFEE-XXX.png'

        Note:
            The QR code filename is based on the payment_reference field,
            ensuring unique filenames for each share. The media directory
            is created if it doesn't exist.
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
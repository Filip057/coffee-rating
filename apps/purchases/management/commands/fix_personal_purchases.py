"""
Management command to fix old personal purchases payment status.

This is a one-time fix for personal purchases created before the backend
fix that automatically marks personal purchases as paid.

Usage:
    python manage.py fix_personal_purchases
"""

from django.core.management.base import BaseCommand
from django.db import models
from apps.purchases.models import PurchaseRecord


class Command(BaseCommand):
    help = 'Mark all personal purchases as paid (one-time data fix)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        # Find all personal purchases (no group) that are not marked as paid
        personal_purchases = PurchaseRecord.objects.filter(
            group__isnull=True,  # Personal purchases have no group
            is_fully_paid=False  # Not yet marked as paid
        )

        count = personal_purchases.count()

        if count == 0:
            self.stdout.write(
                self.style.SUCCESS('No personal purchases need fixing. All good!')
            )
            return

        self.stdout.write(f'\nFound {count} personal purchase(s) to fix:\n')

        for purchase in personal_purchases:
            bean_name = purchase.coffeebean.name if purchase.coffeebean else 'Unknown'
            buyer = purchase.bought_by.email if purchase.bought_by else 'Unknown'
            self.stdout.write(
                f'  - {bean_name} | {purchase.total_price_czk} CZK | Bought by: {buyer} | Date: {purchase.date}'
            )

        if dry_run:
            self.stdout.write(
                self.style.WARNING('\n--dry-run mode: No changes made.')
            )
            return

        # Update all personal purchases to mark as paid
        updated = personal_purchases.update(
            is_fully_paid=True,
            total_collected_czk=models.F('total_price_czk')  # Set collected = total
        )

        self.stdout.write(
            self.style.SUCCESS(f'\n✓ Successfully fixed {updated} personal purchase(s)!')
        )
        self.stdout.write('All personal purchases are now marked as paid.')

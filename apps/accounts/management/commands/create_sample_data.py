"""
Management command to create sample data for testing the API.

Usage:
    python manage.py create_sample_data

This creates:
- 4 users (admin, alice, bob, charlie)
- 2 groups (Coffee Lovers, Office Coffee Club)
- 10 coffee beans with variants
- Tags for taste profiles
- Reviews
- Purchases with payment shares
- Library entries
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal
from datetime import date, timedelta
import random

from apps.accounts.models import User
from apps.beans.models import CoffeeBean, CoffeeBeanVariant
from apps.groups.models import Group, GroupMembership, GroupRole, GroupLibraryEntry
from apps.reviews.models import Review, Tag, UserLibraryEntry
from apps.purchases.models import PurchaseRecord, PaymentShare, PaymentStatus


class Command(BaseCommand):
    help = 'Create sample data for testing the API'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before creating new sample data',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing data...')
            self.clear_data()

        self.stdout.write('Creating sample data...')

        # Create users
        users = self.create_users()

        # Create tags
        tags = self.create_tags()

        # Create coffee beans
        beans = self.create_beans(users['admin'])

        # Create groups
        groups = self.create_groups(users)

        # Create reviews
        self.create_reviews(users, beans, tags)

        # Create purchases
        self.create_purchases(users, beans, groups)

        # Create library entries
        self.create_library_entries(users, beans, groups)

        self.stdout.write(self.style.SUCCESS('Sample data created successfully!'))
        self.stdout.write('')
        self.stdout.write('Test accounts:')
        self.stdout.write('  admin@example.com / admin123 (superuser)')
        self.stdout.write('  alice@example.com / password123')
        self.stdout.write('  bob@example.com / password123')
        self.stdout.write('  charlie@example.com / password123')

    def clear_data(self):
        """Clear all data from the database."""
        PaymentShare.objects.all().delete()
        PurchaseRecord.objects.all().delete()
        Review.objects.all().delete()
        UserLibraryEntry.objects.all().delete()
        GroupLibraryEntry.objects.all().delete()
        GroupMembership.objects.all().delete()
        Group.objects.all().delete()
        CoffeeBeanVariant.objects.all().delete()
        CoffeeBean.objects.all().delete()
        Tag.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()
        User.objects.filter(email='admin@example.com').delete()

    def create_users(self):
        """Create test users."""
        self.stdout.write('  Creating users...')

        # Admin user
        admin, _ = User.objects.get_or_create(
            email='admin@example.com',
            defaults={
                'display_name': 'Admin User',
                'is_staff': True,
                'is_superuser': True,
                'email_verified': True,
            }
        )
        admin.set_password('admin123')
        admin.save()

        # Regular users
        alice, _ = User.objects.get_or_create(
            email='alice@example.com',
            defaults={
                'display_name': 'Alice Coffee',
                'email_verified': True,
            }
        )
        alice.set_password('password123')
        alice.save()

        bob, _ = User.objects.get_or_create(
            email='bob@example.com',
            defaults={
                'display_name': 'Bob Barista',
                'email_verified': True,
            }
        )
        bob.set_password('password123')
        bob.save()

        charlie, _ = User.objects.get_or_create(
            email='charlie@example.com',
            defaults={
                'display_name': 'Charlie Caffeine',
                'email_verified': True,
            }
        )
        charlie.set_password('password123')
        charlie.save()

        return {
            'admin': admin,
            'alice': alice,
            'bob': bob,
            'charlie': charlie,
        }

    def create_tags(self):
        """Create taste tags."""
        self.stdout.write('  Creating tags...')

        tag_data = [
            ('fruity', 'flavor'),
            ('chocolate', 'flavor'),
            ('nutty', 'flavor'),
            ('caramel', 'flavor'),
            ('berry', 'flavor'),
            ('citrus', 'flavor'),
            ('floral', 'aroma'),
            ('earthy', 'aroma'),
            ('spicy', 'aroma'),
            ('sweet', 'aroma'),
            ('bright', 'acidity'),
            ('balanced', 'acidity'),
            ('low-acid', 'acidity'),
            ('full-body', 'body'),
            ('medium-body', 'body'),
            ('light-body', 'body'),
            ('smooth', 'mouthfeel'),
            ('creamy', 'mouthfeel'),
        ]

        tags = {}
        for name, category in tag_data:
            tag, _ = Tag.objects.get_or_create(
                name=name,
                defaults={'category': category}
            )
            tags[name] = tag

        return tags

    def create_beans(self, created_by):
        """Create coffee beans with variants."""
        self.stdout.write('  Creating coffee beans...')

        beans_data = [
            {
                'name': 'Yirgacheffe Natural',
                'roastery_name': 'Doubleshot',
                'origin_country': 'Ethiopia',
                'region': 'Yirgacheffe',
                'roast_profile': 'light',
                'processing': 'natural',
                'tasting_notes': 'Blueberry, jasmine, wine',
                'variants': [
                    {'package_weight_grams': 250, 'price_czk': Decimal('320')},
                    {'package_weight_grams': 1000, 'price_czk': Decimal('1100')},
                ]
            },
            {
                'name': 'Geisha Washed',
                'roastery_name': 'Doubleshot',
                'origin_country': 'Panama',
                'region': 'Boquete',
                'roast_profile': 'light',
                'processing': 'washed',
                'tasting_notes': 'Floral, bergamot, peach',
                'variants': [
                    {'package_weight_grams': 100, 'price_czk': Decimal('450')},
                    {'package_weight_grams': 250, 'price_czk': Decimal('950')},
                ]
            },
            {
                'name': 'Supremo',
                'roastery_name': 'La Boheme',
                'origin_country': 'Colombia',
                'region': 'Huila',
                'roast_profile': 'medium',
                'processing': 'washed',
                'tasting_notes': 'Caramel, apple, chocolate',
                'variants': [
                    {'package_weight_grams': 250, 'price_czk': Decimal('280')},
                    {'package_weight_grams': 500, 'price_czk': Decimal('520')},
                ]
            },
            {
                'name': 'Santos Natural',
                'roastery_name': 'Káva z Afriky',
                'origin_country': 'Brazil',
                'region': 'Cerrado',
                'roast_profile': 'medium',
                'processing': 'natural',
                'tasting_notes': 'Nuts, chocolate, low acidity',
                'variants': [
                    {'package_weight_grams': 250, 'price_czk': Decimal('220')},
                    {'package_weight_grams': 1000, 'price_czk': Decimal('750')},
                ]
            },
            {
                'name': 'AA Nyeri',
                'roastery_name': 'Coffee Source',
                'origin_country': 'Kenya',
                'region': 'Nyeri',
                'roast_profile': 'light',
                'processing': 'washed',
                'tasting_notes': 'Blackcurrant, tomato, bright',
                'variants': [
                    {'package_weight_grams': 250, 'price_czk': Decimal('380')},
                ]
            },
            {
                'name': 'Decaf Swiss Water',
                'roastery_name': 'Nordbeans',
                'origin_country': 'Colombia',
                'region': 'Various',
                'roast_profile': 'medium',
                'processing': 'washed',
                'tasting_notes': 'Chocolate, caramel, smooth',
                'variants': [
                    {'package_weight_grams': 250, 'price_czk': Decimal('290')},
                ]
            },
            {
                'name': 'Espresso Blend',
                'roastery_name': 'Nordbeans',
                'origin_country': 'Blend',
                'roast_profile': 'dark',
                'processing': 'other',
                'tasting_notes': 'Dark chocolate, caramel, full body',
                'variants': [
                    {'package_weight_grams': 250, 'price_czk': Decimal('250')},
                    {'package_weight_grams': 1000, 'price_czk': Decimal('850')},
                ]
            },
            {
                'name': 'Antigua',
                'roastery_name': 'Father Coffee',
                'origin_country': 'Guatemala',
                'region': 'Antigua',
                'roast_profile': 'medium',
                'processing': 'washed',
                'tasting_notes': 'Chocolate, spice, balanced',
                'variants': [
                    {'package_weight_grams': 250, 'price_czk': Decimal('310')},
                ]
            },
            {
                'name': 'Sidamo Washed',
                'roastery_name': 'Candycane',
                'origin_country': 'Ethiopia',
                'region': 'Sidamo',
                'roast_profile': 'light',
                'processing': 'washed',
                'tasting_notes': 'Citrus, tea-like, floral',
                'variants': [
                    {'package_weight_grams': 200, 'price_czk': Decimal('270')},
                    {'package_weight_grams': 500, 'price_czk': Decimal('580')},
                ]
            },
            {
                'name': 'Sumatra Mandheling',
                'roastery_name': 'Doubleshot',
                'origin_country': 'Indonesia',
                'region': 'Sumatra',
                'roast_profile': 'dark',
                'processing': 'other',
                'tasting_notes': 'Earthy, herbal, full body',
                'variants': [
                    {'package_weight_grams': 250, 'price_czk': Decimal('340')},
                ]
            },
        ]

        beans = []
        for data in beans_data:
            variants_data = data.pop('variants')

            bean, _ = CoffeeBean.objects.get_or_create(
                name=data['name'],
                roastery_name=data['roastery_name'],
                defaults={
                    **data,
                    'created_by': created_by,
                }
            )

            # Create variants
            for variant_data in variants_data:
                CoffeeBeanVariant.objects.get_or_create(
                    coffeebean=bean,
                    package_weight_grams=variant_data['package_weight_grams'],
                    defaults={'price_czk': variant_data['price_czk']}
                )

            beans.append(bean)

        return beans

    def create_groups(self, users):
        """Create groups with members."""
        self.stdout.write('  Creating groups...')

        # Coffee Lovers group (alice as owner)
        coffee_lovers, created = Group.objects.get_or_create(
            name='Coffee Lovers',
            defaults={
                'description': 'A group for coffee enthusiasts sharing their favorite beans',
                'owner': users['alice'],
                'is_private': False,
            }
        )

        if created:
            GroupMembership.objects.create(
                user=users['alice'],
                group=coffee_lovers,
                role=GroupRole.OWNER
            )
            GroupMembership.objects.create(
                user=users['bob'],
                group=coffee_lovers,
                role=GroupRole.ADMIN
            )
            GroupMembership.objects.create(
                user=users['charlie'],
                group=coffee_lovers,
                role=GroupRole.MEMBER
            )

        # Office Coffee Club (bob as owner)
        office_club, created = Group.objects.get_or_create(
            name='Office Coffee Club',
            defaults={
                'description': 'Weekly coffee purchases for the office',
                'owner': users['bob'],
                'is_private': True,
            }
        )

        if created:
            GroupMembership.objects.create(
                user=users['bob'],
                group=office_club,
                role=GroupRole.OWNER
            )
            GroupMembership.objects.create(
                user=users['alice'],
                group=office_club,
                role=GroupRole.MEMBER
            )

        return {
            'coffee_lovers': coffee_lovers,
            'office_club': office_club,
        }

    def create_reviews(self, users, beans, tags):
        """Create reviews for beans."""
        self.stdout.write('  Creating reviews...')

        review_data = [
            # Alice's reviews
            {
                'user': users['alice'],
                'bean': beans[0],  # Yirgacheffe
                'rating': 5,
                'notes': 'Amazing fruity notes, exactly what I was looking for!',
                'brew_method': 'filter',
                'tags': ['fruity', 'floral', 'bright'],
            },
            {
                'user': users['alice'],
                'bean': beans[2],  # Colombia Supremo
                'rating': 4,
                'notes': 'Great daily drinker, smooth and balanced.',
                'brew_method': 'espresso',
                'tags': ['chocolate', 'caramel', 'balanced'],
            },
            {
                'user': users['alice'],
                'bean': beans[4],  # Kenya AA
                'rating': 5,
                'notes': 'Incredible complexity! The blackcurrant is so pronounced.',
                'brew_method': 'aeropress',
                'tags': ['fruity', 'bright', 'berry'],
            },
            # Bob's reviews
            {
                'user': users['bob'],
                'bean': beans[0],  # Yirgacheffe
                'rating': 4,
                'notes': 'Nice fruity coffee, but a bit too light for my espresso.',
                'brew_method': 'espresso',
                'tags': ['fruity', 'light-body'],
            },
            {
                'user': users['bob'],
                'bean': beans[6],  # Espresso Blend
                'rating': 5,
                'notes': 'Perfect for espresso! Rich crema and chocolate notes.',
                'brew_method': 'espresso',
                'tags': ['chocolate', 'full-body', 'creamy'],
            },
            {
                'user': users['bob'],
                'bean': beans[3],  # Brazil Santos
                'rating': 4,
                'notes': 'Good value, nutty and smooth. Great for milk drinks.',
                'brew_method': 'espresso',
                'tags': ['nutty', 'smooth', 'low-acid'],
            },
            # Charlie's reviews
            {
                'user': users['charlie'],
                'bean': beans[1],  # Geisha
                'rating': 5,
                'notes': 'Worth every crown! Most elegant coffee I have had.',
                'brew_method': 'filter',
                'tags': ['floral', 'fruity', 'sweet'],
            },
            {
                'user': users['charlie'],
                'bean': beans[8],  # Sidamo
                'rating': 4,
                'notes': 'Lovely tea-like quality. Perfect afternoon coffee.',
                'brew_method': 'filter',
                'tags': ['floral', 'citrus', 'light-body'],
            },
        ]

        for data in review_data:
            review, created = Review.objects.get_or_create(
                author=data['user'],
                coffeebean=data['bean'],
                defaults={
                    'rating': data['rating'],
                    'notes': data['notes'],
                    'brew_method': data['brew_method'],
                    'context': 'personal',
                }
            )

            if created:
                for tag_name in data['tags']:
                    if tag_name in tags:
                        review.taste_tags.add(tags[tag_name])

                # Update bean's aggregate rating
                data['bean'].update_aggregate_rating()

    def create_purchases(self, users, beans, groups):
        """Create purchase records with payment shares."""
        self.stdout.write('  Creating purchases...')

        today = date.today()

        # Personal purchase - Alice
        bean = beans[0]  # Yirgacheffe
        variant = bean.variants.first()
        purchase1, created = PurchaseRecord.objects.get_or_create(
            coffeebean=bean,
            bought_by=users['alice'],
            date=today - timedelta(days=5),
            defaults={
                'variant': variant,
                'total_price_czk': variant.price_czk if variant else Decimal('320'),
                'package_weight_grams': variant.package_weight_grams if variant else 250,
                'purchase_location': 'Doubleshot Prague',
            }
        )
        if created:
            share = PaymentShare.objects.create(
                purchase=purchase1,
                user=users['alice'],
                amount_czk=purchase1.total_price_czk,
                status=PaymentStatus.PAID,
            )
            purchase1.is_fully_paid = True
            purchase1.total_collected_czk = purchase1.total_price_czk
            purchase1.save()

        # Group purchase - Coffee Lovers
        bean = beans[2]  # Colombia
        variant = bean.variants.filter(package_weight_grams=500).first()
        purchase2, created = PurchaseRecord.objects.get_or_create(
            coffeebean=bean,
            group=groups['coffee_lovers'],
            bought_by=users['alice'],
            date=today - timedelta(days=3),
            defaults={
                'variant': variant,
                'total_price_czk': Decimal('520'),
                'package_weight_grams': 500,
                'purchase_location': 'Online - La Boheme',
                'note': 'Shared purchase for the group tasting',
            }
        )
        if created:
            # Split among 3 members (520 / 3 = 173.33...)
            PaymentShare.objects.create(
                purchase=purchase2,
                user=users['alice'],
                amount_czk=Decimal('174'),  # Buyer gets extra haléř
                status=PaymentStatus.PAID,
            )
            PaymentShare.objects.create(
                purchase=purchase2,
                user=users['bob'],
                amount_czk=Decimal('173'),
                status=PaymentStatus.PAID,
            )
            PaymentShare.objects.create(
                purchase=purchase2,
                user=users['charlie'],
                amount_czk=Decimal('173'),
                status=PaymentStatus.UNPAID,  # Charlie hasn't paid yet
            )
            purchase2.total_collected_czk = Decimal('347')
            purchase2.save()

        # Group purchase - Office Club (outstanding)
        bean = beans[6]  # Espresso Blend
        variant = bean.variants.filter(package_weight_grams=1000).first()
        purchase3, created = PurchaseRecord.objects.get_or_create(
            coffeebean=bean,
            group=groups['office_club'],
            bought_by=users['bob'],
            date=today - timedelta(days=1),
            defaults={
                'variant': variant,
                'total_price_czk': Decimal('850'),
                'package_weight_grams': 1000,
                'purchase_location': 'Nordbeans.cz',
                'note': 'Office coffee for next week',
            }
        )
        if created:
            # Split between 2 members
            PaymentShare.objects.create(
                purchase=purchase3,
                user=users['bob'],
                amount_czk=Decimal('425'),
                status=PaymentStatus.PAID,
            )
            PaymentShare.objects.create(
                purchase=purchase3,
                user=users['alice'],
                amount_czk=Decimal('425'),
                status=PaymentStatus.UNPAID,
            )
            purchase3.total_collected_czk = Decimal('425')
            purchase3.save()

    def create_library_entries(self, users, beans, groups):
        """Create user and group library entries."""
        self.stdout.write('  Creating library entries...')

        # User libraries (some automatically created by reviews, add more)
        for user in [users['alice'], users['bob'], users['charlie']]:
            for bean in random.sample(beans, min(5, len(beans))):
                UserLibraryEntry.ensure_entry(
                    user=user,
                    coffeebean=bean,
                    added_by='manual'
                )

        # Group libraries
        for group in groups.values():
            group_beans = random.sample(beans, min(4, len(beans)))
            for bean in group_beans:
                GroupLibraryEntry.objects.get_or_create(
                    group=group,
                    coffeebean=bean,
                    defaults={
                        'added_by': group.owner,
                        'notes': f'Added by {group.owner.get_display_name()}',
                    }
                )

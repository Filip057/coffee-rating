# Generated manually for purchases app refactor

import uuid
from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('beans', '0002_mergehistory'),
        ('groups', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PersonalPurchase',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('total_price_czk', models.DecimalField(decimal_places=2, max_digits=10, validators=[MinValueValidator(Decimal('0.01'))])),
                ('currency', models.CharField(default='CZK', max_length=3)),
                ('package_weight_grams', models.PositiveIntegerField(blank=True, null=True)),
                ('date', models.DateField()),
                ('purchase_location', models.CharField(choices=[('eshop', 'E-shop'), ('cafe', 'Kavarna'), ('roastery', 'Prazirna'), ('store', 'Prodejna'), ('other', 'Jine')], default='other', max_length=20)),
                ('eshop_url', models.URLField(blank=True)),
                ('note', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('coffeebean', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='personalpurchase_purchases', to='beans.coffeebean')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='personal_purchases', to=settings.AUTH_USER_MODEL)),
                ('variant', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='personalpurchase_purchases', to='beans.coffeebeanvariant')),
            ],
            options={
                'db_table': 'personal_purchases',
                'ordering': ['-date', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='GroupPurchase',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('total_price_czk', models.DecimalField(decimal_places=2, max_digits=10, validators=[MinValueValidator(Decimal('0.01'))])),
                ('currency', models.CharField(default='CZK', max_length=3)),
                ('package_weight_grams', models.PositiveIntegerField(blank=True, null=True)),
                ('date', models.DateField()),
                ('purchase_location', models.CharField(choices=[('eshop', 'E-shop'), ('cafe', 'Kavarna'), ('roastery', 'Prazirna'), ('store', 'Prodejna'), ('other', 'Jine')], default='other', max_length=20)),
                ('eshop_url', models.URLField(blank=True)),
                ('note', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('total_collected_czk', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=10)),
                ('is_fully_paid', models.BooleanField(default=False)),
                ('bought_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='group_purchases_bought', to=settings.AUTH_USER_MODEL)),
                ('coffeebean', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='grouppurchase_purchases', to='beans.coffeebean')),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='purchases', to='groups.group')),
                ('variant', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='grouppurchase_purchases', to='beans.coffeebeanvariant')),
            ],
            options={
                'db_table': 'group_purchases',
                'ordering': ['-date', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='PaymentShare',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('amount_czk', models.DecimalField(decimal_places=2, max_digits=10, validators=[MinValueValidator(Decimal('0.01'))])),
                ('currency', models.CharField(default='CZK', max_length=3)),
                ('status', models.CharField(choices=[('unpaid', 'Unpaid'), ('paid', 'Paid'), ('failed', 'Failed'), ('refunded', 'Refunded')], default='unpaid', max_length=20)),
                ('payment_reference', models.CharField(db_index=True, editable=False, max_length=64, unique=True)),
                ('qr_url', models.CharField(blank=True, max_length=500)),
                ('qr_image_path', models.CharField(blank=True, max_length=200)),
                ('paid_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('paid_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='confirmed_payments', to=settings.AUTH_USER_MODEL)),
                ('purchase', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payment_shares', to='purchases.grouppurchase')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payment_shares', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'payment_shares',
                'ordering': ['created_at'],
            },
        ),
        migrations.CreateModel(
            name='BankTransaction',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('transaction_id', models.CharField(max_length=100, unique=True)),
                ('date', models.DateField()),
                ('amount_czk', models.DecimalField(decimal_places=2, max_digits=10)),
                ('variable_symbol', models.CharField(blank=True, db_index=True, max_length=64)),
                ('message', models.TextField(blank=True)),
                ('is_matched', models.BooleanField(default=False)),
                ('imported_at', models.DateTimeField(auto_now_add=True)),
                ('raw_data', models.JSONField(blank=True, null=True)),
                ('matched_share', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='bank_transactions', to='purchases.paymentshare')),
            ],
            options={
                'db_table': 'bank_transactions',
                'ordering': ['-date'],
            },
        ),
        # Create indexes for PersonalPurchase
        migrations.AddIndex(
            model_name='personalpurchase',
            index=models.Index(fields=['user', 'date'], name='personal_pu_user_id_f8c64b_idx'),
        ),
        migrations.AddIndex(
            model_name='personalpurchase',
            index=models.Index(fields=['date'], name='personal_pu_date_5a2e91_idx'),
        ),
        migrations.AddIndex(
            model_name='personalpurchase',
            index=models.Index(fields=['coffeebean', 'date'], name='personal_pu_coffeeb_2f4d43_idx'),
        ),
        # Create indexes for GroupPurchase
        migrations.AddIndex(
            model_name='grouppurchase',
            index=models.Index(fields=['group', 'date'], name='group_purch_group_i_b4f5e1_idx'),
        ),
        migrations.AddIndex(
            model_name='grouppurchase',
            index=models.Index(fields=['bought_by', 'date'], name='group_purch_bought__a8d2c3_idx'),
        ),
        migrations.AddIndex(
            model_name='grouppurchase',
            index=models.Index(fields=['date'], name='group_purch_date_7b9e41_idx'),
        ),
        migrations.AddIndex(
            model_name='grouppurchase',
            index=models.Index(fields=['is_fully_paid'], name='group_purch_is_full_5c6a92_idx'),
        ),
        # Create indexes for PaymentShare
        migrations.AddIndex(
            model_name='paymentshare',
            index=models.Index(fields=['user', 'status'], name='payment_sha_user_id_d3e8f7_idx'),
        ),
        migrations.AddIndex(
            model_name='paymentshare',
            index=models.Index(fields=['purchase', 'status'], name='payment_sha_purchas_6c4a93_idx'),
        ),
        migrations.AddIndex(
            model_name='paymentshare',
            index=models.Index(fields=['payment_reference'], name='payment_sha_payment_1e5b42_idx'),
        ),
        migrations.AddIndex(
            model_name='paymentshare',
            index=models.Index(fields=['status', 'created_at'], name='payment_sha_status_7f9c21_idx'),
        ),
        # Create unique constraint for PaymentShare
        migrations.AlterUniqueTogether(
            name='paymentshare',
            unique_together={('purchase', 'user')},
        ),
        # Create indexes for BankTransaction
        migrations.AddIndex(
            model_name='banktransaction',
            index=models.Index(fields=['transaction_id'], name='bank_transa_transac_8d4e62_idx'),
        ),
        migrations.AddIndex(
            model_name='banktransaction',
            index=models.Index(fields=['variable_symbol'], name='bank_transa_variabl_3f7a91_idx'),
        ),
        migrations.AddIndex(
            model_name='banktransaction',
            index=models.Index(fields=['is_matched', 'date'], name='bank_transa_is_matc_5c2b84_idx'),
        ),
    ]

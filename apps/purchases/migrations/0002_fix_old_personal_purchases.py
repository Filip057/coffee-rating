# Generated manually to fix old personal purchases
from django.db import migrations, models


def fix_personal_purchases(apps, schema_editor):
    """Mark all personal purchases as paid."""
    PurchaseRecord = apps.get_model('purchases', 'PurchaseRecord')

    # Find personal purchases that aren't marked as paid
    personal_purchases = PurchaseRecord.objects.filter(
        group__isnull=True,
        is_fully_paid=False
    )

    # Update them to be marked as paid
    count = personal_purchases.update(
        is_fully_paid=True,
        total_collected_czk=models.F('total_price_czk')
    )

    if count > 0:
        print(f"Fixed {count} personal purchase(s)")


def reverse_fix(apps, schema_editor):
    """Reverse the fix (for rollback)."""
    # We don't reverse this - it's a data fix
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('purchases', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(fix_personal_purchases, reverse_fix),
    ]

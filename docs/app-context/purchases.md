# Purchases App - Application Context

> **Last Updated:** 2025-12-14
> **Owner:** Filip Prudek
> **Status:** Development

---

## Purpose & Responsibility

Manages coffee purchase tracking for individuals and groups with haléř-precise payment splitting, payment share tracking, and SPD QR code generation for Czech bank payments.

**Core Responsibility:**
- Personal and group purchase recording
- Automatic payment splitting with haléř precision
- Payment share tracking (unpaid/paid/failed)
- Payment reference generation for bank matching
- SPD QR code generation for Czech banking
- Purchase reconciliation tracking

**NOT Responsible For:**
- Coffee bean catalog (that's `beans` app)
- Group membership (that's `groups` app)
- User library (that's `reviews` app - but purchases can trigger library entries)
- User authentication (that's `accounts` app)

---

## Models

### **PurchaseRecord**

**Purpose:** Records a coffee purchase (personal or group) with financial details.

**Fields:**
| Field | Type | Purpose | Business Rule |
|-------|------|---------|---------------|
| `id` | UUIDField (PK) | Unique identifier | Auto-generated |
| `group` | FK(Group) | Group context | Null for personal purchases |
| `coffeebean` | FK(CoffeeBean) | What was purchased | Optional, SET_NULL |
| `variant` | FK(CoffeeBeanVariant) | Specific variant | Optional, SET_NULL |
| `bought_by` | FK(User) | Who made purchase | Required, CASCADE |
| `total_price_czk` | Decimal(10,2) | Total cost | Required, min 0.01 |
| `currency` | CharField(3) | Currency code | Default: CZK |
| `package_weight_grams` | PositiveInt | Package weight | Optional |
| `date` | DateField | Purchase date | Required |
| `purchase_location` | CharField(200) | Where bought | Optional |
| `note` | TextField | Purchase notes | Optional |
| `total_collected_czk` | Decimal(10,2) | Sum of paid shares | Default: 0.00 |
| `is_fully_paid` | BooleanField | All shares paid | Default: False |
| `created_at` | DateTimeField | Creation timestamp | Auto-set |
| `updated_at` | DateTimeField | Last update | Auto-set |

**Relationships:**
- **Belongs To:** Group (optional, for group purchases)
- **Belongs To:** CoffeeBean (optional)
- **Belongs To:** CoffeeBeanVariant (optional)
- **Belongs To:** User (via `bought_by`)
- **Has Many:** PaymentShare (via `payment_shares`)

**Key Methods:**
```python
def update_collection_status(self):
    """Recalculate collected amount from paid shares."""
    collected = self.payment_shares.filter(
        status=PaymentStatus.PAID
    ).aggregate(total=Sum('amount_czk'))['total'] or Decimal('0.00')

    self.total_collected_czk = collected
    self.is_fully_paid = (collected >= self.total_price_czk)
    self.save(update_fields=['total_collected_czk', 'is_fully_paid', 'updated_at'])

def get_outstanding_balance(self):
    """Return unpaid amount."""
    return max(Decimal('0.00'), self.total_price_czk - self.total_collected_czk)
```

**Business Rules:**
1. **Group Purchase:** If group is set, payment shares are auto-created
2. **Personal Purchase:** No payment shares created (buyer pays themselves)
3. **Reconciliation:** `is_fully_paid` auto-updated when shares are marked paid
4. **Soft Reference:** coffeebean/variant use SET_NULL to preserve history

**Indexes:**
- `(group, date)` - For group purchase history
- `(bought_by, date)` - For user purchase history
- `(coffeebean, date)` - For bean purchase history
- `date` - For chronological listing
- `is_fully_paid` - For outstanding purchase filtering

---

### **PaymentShare**

**Purpose:** Individual payment owed by a user for a group purchase.

**Fields:**
| Field | Type | Purpose | Business Rule |
|-------|------|---------|---------------|
| `id` | UUIDField (PK) | Unique identifier | Auto-generated |
| `purchase` | FK(PurchaseRecord) | Parent purchase | Required, CASCADE |
| `user` | FK(User) | Who owes | Required, CASCADE |
| `amount_czk` | Decimal(10,2) | Amount owed | Required, min 0.01 |
| `currency` | CharField(3) | Currency code | Default: CZK |
| `status` | CharField(20) | Payment status | Default: unpaid |
| `payment_reference` | CharField(64) | Bank reference | Auto-generated, unique |
| `qr_url` | CharField(500) | SPD string | Optional |
| `qr_image_path` | CharField(200) | QR image path | Optional |
| `paid_at` | DateTimeField | Payment timestamp | Null until paid |
| `paid_by` | FK(User) | Who confirmed | Null until paid |
| `created_at` | DateTimeField | Creation timestamp | Auto-set |
| `updated_at` | DateTimeField | Last update | Auto-set |

**Enum Choices:**
```python
class PaymentStatus(models.TextChoices):
    UNPAID = 'unpaid', 'Unpaid'
    PAID = 'paid', 'Paid'
    FAILED = 'failed', 'Failed'
    REFUNDED = 'refunded', 'Refunded'
```

**Key Methods:**
```python
def save(self, *args, **kwargs):
    """Generate payment reference if not set."""
    if not self.payment_reference:
        self.payment_reference = self._generate_payment_reference()
    super().save(*args, **kwargs)

def _generate_payment_reference(self):
    """Generate unique reference: COFFEE-<uuid8>-<4digits>"""
    short_id = str(self.id)[:8].upper()
    random_suffix = secrets.randbelow(10000)
    return f"COFFEE-{short_id}-{random_suffix:04d}"

def mark_paid(self, paid_by_user=None):
    """Mark share as paid and update parent purchase."""
    self.status = PaymentStatus.PAID
    self.paid_at = timezone.now()
    self.paid_by = paid_by_user
    self.save(update_fields=['status', 'paid_at', 'paid_by', 'updated_at'])
    self.purchase.update_collection_status()
```

**Business Rules:**
1. **Unique Constraint:** `(purchase, user)` - one share per user per purchase
2. **Auto Reference:** `payment_reference` generated on first save
3. **Cascading Update:** `mark_paid()` triggers parent `update_collection_status()`

**Indexes:**
- `(user, status)` - For user's outstanding payments
- `(purchase, status)` - For purchase reconciliation
- `payment_reference` - For bank matching
- `(status, created_at)` - For outstanding payments timeline

---

### **BankTransaction**

**Purpose:** Imported bank transactions for auto-reconciliation (optional feature).

**Fields:**
| Field | Type | Purpose | Business Rule |
|-------|------|---------|---------------|
| `id` | UUIDField (PK) | Unique identifier | Auto-generated |
| `transaction_id` | CharField(100) | Bank's transaction ID | Unique |
| `date` | DateField | Transaction date | Required |
| `amount_czk` | Decimal(10,2) | Transaction amount | Required |
| `variable_symbol` | CharField(64) | Payment reference | Indexed |
| `message` | TextField | Transaction message | Optional |
| `matched_share` | FK(PaymentShare) | Matched payment | Optional |
| `is_matched` | BooleanField | Match status | Default: False |
| `imported_at` | DateTimeField | Import timestamp | Auto-set |
| `raw_data` | JSONField | Original bank data | Optional |

**Business Rules:**
1. **Unique Transaction:** `transaction_id` ensures no duplicate imports
2. **Auto-Matching:** Match `variable_symbol` to `payment_reference`

---

## API Endpoints

### Purchase CRUD

| Method | Endpoint | Purpose | Auth | Permissions |
|--------|----------|---------|------|-------------|
| GET | `/api/purchases/` | List purchases | Required | IsAuthenticated |
| POST | `/api/purchases/` | Create purchase | Required | IsAuthenticated |
| GET | `/api/purchases/{id}/` | Get purchase details | Required | IsAuthenticated |
| PUT | `/api/purchases/{id}/` | Full update | Required | IsAuthenticated |
| PATCH | `/api/purchases/{id}/` | Partial update | Required | IsAuthenticated |
| DELETE | `/api/purchases/{id}/` | Delete purchase | Required | IsAuthenticated |
| GET | `/api/purchases/{id}/summary/` | Get payment summary | Required | IsAuthenticated |
| GET | `/api/purchases/{id}/shares/` | Get all shares | Required | IsAuthenticated |
| POST | `/api/purchases/{id}/mark_paid/` | Mark share paid | Required | IsAuthenticated |

**Query Parameters for List:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `group` | UUID | Filter by group |
| `user` | UUID | Filter by user (buyer or share holder) |
| `date_from` | date | Start date (YYYY-MM-DD) |
| `date_to` | date | End date (YYYY-MM-DD) |
| `is_fully_paid` | bool | Filter by payment status |

### Payment Shares

| Method | Endpoint | Purpose | Auth | Permissions |
|--------|----------|---------|------|-------------|
| GET | `/api/purchases/shares/` | List user's shares | Required | IsAuthenticated |
| GET | `/api/purchases/shares/{id}/` | Get share details | Required | IsAuthenticated |
| GET | `/api/purchases/shares/{id}/qr_code/` | Get QR code info | Required | IsAuthenticated |
| GET | `/api/purchases/my_outstanding/` | User's unpaid shares | Required | IsAuthenticated |

---

## Business Logic & Workflows

### **Workflow 1: Personal Purchase**

**Trigger:** POST to `/api/purchases/` without `group`

**Steps:**
1. Validate required fields (total_price_czk, date)
2. Set `bought_by` to current user
3. Create PurchaseRecord
4. No payment shares created (buyer pays themselves)

**Result:** Single purchase record, no reconciliation needed

### **Workflow 2: Group Purchase with Split**

**Trigger:** POST to `/api/purchases/` with `group`

**Steps:**
1. Validate user is member of group
2. Validate required fields
3. **Transaction Start**
4. Get split participants (all members or specified `split_members`)
5. Calculate haléř-precise splits using `PurchaseSplitService._calculate_splits()`
6. Create PurchaseRecord
7. Create PaymentShare for each participant
8. Generate payment references
9. **Transaction Commit**
10. Optionally generate SPD QR codes

**Code:**
```python
@transaction.atomic
def perform_create(self, serializer):
    split_members = serializer.validated_data.pop('split_members', None)
    group = serializer.validated_data.get('group')

    if group:
        purchase, shares = PurchaseSplitService.create_group_purchase(
            group_id=group.id,
            bought_by_user=self.request.user,
            total_price_czk=serializer.validated_data['total_price_czk'],
            date=serializer.validated_data['date'],
            coffeebean=serializer.validated_data.get('coffeebean'),
            split_members=split_members
        )

        # Generate QR codes if bank IBAN configured
        if settings.PAYMENT_QR_BANK_IBAN:
            for share in shares:
                SPDPaymentGenerator.generate_for_payment_share(share, bank_iban, recipient_name)
```

### **Workflow 3: Haléř-Precise Payment Split**

**Algorithm:**
```
1. Convert to haléře: total_halere = int(total_czk * 100)
2. Base share: base = total_halere // N
3. Remainder: remainder = total_halere % N
4. First 'remainder' participants get (base + 1) haléře
5. Rest get 'base' haléře
6. Convert back to CZK: amount_czk = halere / 100
```

**Example:**
```
100.00 CZK / 3 people
= 10000 haléře / 3
= 3333 haléře each + 1 haléř remainder
= [3334, 3333, 3333] haléře
= [33.34, 33.33, 33.33] CZK
Total: 100.00 CZK (exact!)
```

**Code:**
```python
@staticmethod
def _calculate_splits(total_czk, participants):
    total_halere = int(total_czk * 100)
    num_participants = len(participants)

    base_halere = total_halere // num_participants
    remainder_halere = total_halere % num_participants

    shares = []
    for i, user in enumerate(participants):
        if i < remainder_halere:
            user_halere = base_halere + 1
        else:
            user_halere = base_halere

        amount_czk = Decimal(user_halere) / Decimal(100)
        shares.append((user, amount_czk))

    return shares
```

### **Workflow 4: Payment Reconciliation**

**Trigger:** POST to `/api/purchases/{id}/mark_paid/`

**Steps:**
1. Find share by `payment_reference` or user's own share
2. Verify share is not already paid
3. **Transaction Start**
4. Lock share for update (`select_for_update`)
5. Call `share.mark_paid(paid_by_user)`
6. Updates parent purchase's `total_collected_czk` and `is_fully_paid`
7. **Transaction Commit**

---

## Services

### **PurchaseSplitService**

Core business logic for purchase splitting and reconciliation.

| Method | Purpose |
|--------|---------|
| `create_group_purchase()` | Create purchase with payment shares |
| `_calculate_splits()` | Haléř-precise amount distribution |
| `reconcile_payment()` | Mark share as paid with locking |
| `get_purchase_summary()` | Get detailed payment status |

### **SPDPaymentGenerator**

Czech SPD (Short Payment Descriptor) QR code generation.

| Method | Purpose |
|--------|---------|
| `generate_spd_string()` | Create SPD format string |
| `generate_qr_image()` | Generate QR code PNG |
| `generate_for_payment_share()` | Full generation for a share |

**SPD Format:**
```
SPD*1.0*ACC:<IBAN>*AM:<amount>*CC:CZK*MSG:<message>*X-VS:<variable_symbol>
```

---

## Permissions & Security

**Permission Classes:**
- `IsAuthenticated` - All purchase operations require login

**Access Rules:**
| Action | Who Can Do It |
|--------|---------------|
| List purchases | User involved (buyer or share holder) |
| Create purchase | Any authenticated user |
| View purchase | User involved or group member |
| Update purchase | Buyer only |
| Delete purchase | Buyer only |
| Mark share paid | Any authenticated user (for reconciliation) |
| View shares | User involved or group member |

**Security Considerations:**
- Payment references are cryptographically random
- QuerySet filtered to only show relevant purchases
- Bank IBAN stored in settings, not in code

---

## Testing Strategy

**What to Test:**
1. Purchase CRUD operations
2. Haléř-precise splitting (multiple edge cases)
3. Payment share creation
4. Reconciliation workflow
5. Group membership validation
6. QR code generation

**Test Coverage:** 80+ test cases in `apps/purchases/tests/test_api.py`

**Critical Test Cases:**
```python
def test_uneven_split_three_ways(self):
    """100 CZK split 3 ways = 33.34 + 33.33 + 33.33"""
    splits = PurchaseSplitService._calculate_splits(
        Decimal('100.00'),
        ['user1', 'user2', 'user3']
    )

    amounts = [amount for _, amount in splits]
    assert sum(amounts) == Decimal('100.00')
    assert Decimal('33.34') in amounts
    assert amounts.count(Decimal('33.33')) == 2

def test_mark_paid_updates_collected_amount(self, member1_client, group_purchase_with_shares):
    """Marking paid updates the purchase's collected amount."""
    share = PaymentShare.objects.get(purchase=..., user=...)
    old_collected = purchase.total_collected_czk

    response = member1_client.post(url, {'payment_reference': share.payment_reference})

    purchase.refresh_from_db()
    assert purchase.total_collected_czk > old_collected
```

---

## Dependencies & Relationships

**This App Uses:**
- `accounts.User` - For buyer and share holder references
- `beans.CoffeeBean` / `CoffeeBeanVariant` - For purchase item reference
- `groups.Group` / `GroupMembership` - For group purchases and member lists
- `qrcode` library - For QR code generation

**Used By:**
- `analytics` - Spending and consumption statistics
- `reviews` - Purchases can trigger library entry creation (future)

**External Services:**
- None directly (QR codes are generated locally)

**Configuration:**
```python
# settings.py
PAYMENT_QR_BANK_IBAN = 'CZ1234567890...'  # Optional
PAYMENT_RECIPIENT_NAME = 'Coffee Group'  # Optional
```

---

## Common Patterns

**Pattern 1: Haléř-Precise Calculation**
```python
# Convert to smallest unit, calculate, convert back
total_halere = int(total_czk * 100)
base_halere = total_halere // num_participants
remainder_halere = total_halere % num_participants
# First 'remainder' users get +1 haléř
```

**When to Use:** Any monetary split to avoid rounding errors

**Pattern 2: Atomic Purchase Creation**
```python
with transaction.atomic():
    purchase = PurchaseRecord.objects.create(...)
    for user, amount in shares_data:
        PaymentShare.objects.create(
            purchase=purchase,
            user=user,
            amount_czk=amount,
        )
```

**When to Use:** Creating purchase with shares

**Pattern 3: Cascading Status Update**
```python
def mark_paid(self, paid_by_user=None):
    self.status = PaymentStatus.PAID
    self.save(...)
    self.purchase.update_collection_status()  # Cascade!
```

**When to Use:** Any status change that affects parent

---

## Gotchas & Known Issues

**Issue 1: QR Code Generation Requires qrcode Library**
- **Symptom:** ImportError on purchase creation
- **Cause:** Optional dependency not installed
- **Workaround:** Install `qrcode[pil]` or skip QR generation
- **Status:** Optional feature

**Issue 2: Bank IBAN in Settings**
- **Symptom:** QR codes not generated
- **Cause:** PAYMENT_QR_BANK_IBAN not configured
- **Workaround:** Configure in settings.py
- **Status:** By design

**Issue 3: No Automatic Bank Import**
- **Symptom:** BankTransaction model exists but unused
- **Cause:** Bank API integration not implemented
- **Workaround:** Manual mark_paid
- **Status:** TODO - Future feature

---

## Future Enhancements

**Planned:**
- [ ] Bank API integration for auto-reconciliation
- [ ] Email notifications for payment reminders
- [ ] Export purchase history to CSV
- [ ] Multi-currency support

**Ideas:**
- [ ] Recurring purchases (subscriptions)
- [ ] Receipt photo attachments
- [ ] Price comparison across purchases
- [ ] Budget tracking

**Won't Do (and Why):**
- Full accounting system - Out of scope, use external tools
- Credit card processing - Use external payment providers

---

## Related Documentation

- [API Reference](../API.md#purchases-endpoints)
- [Database Schema](../DATABASE.md)
- Other App Contexts: [accounts](./accounts.md), [beans](./beans.md), [groups](./groups.md)

---

## Notes for Developers

> **Why Haléř Precision?**
> Standard floating-point math loses precision: `100.00 / 3 = 33.333...`. By converting to smallest currency unit (haléře), using integer arithmetic, and distributing remainder, we ensure splits always sum exactly to the total.

> **Why Payment References?**
> Bank transfers use "variable symbol" for matching payments. Our auto-generated references (COFFEE-XXXX-YYYY) can be entered in bank transfer to enable future auto-reconciliation.

> **Why SET_NULL for coffeebean/variant?**
> Purchases should persist even if the coffee bean is soft-deleted. Historical data is valuable for analytics and user history.

---

## AI Assistant Context

**When modifying this app, ALWAYS remember:**

1. **NEVER use floating-point for monetary calculations**
   - Always use Decimal or integer haléře
   - Test that splits sum exactly to total

2. **ALWAYS use transaction.atomic for purchase creation**
   - Purchase and shares must be created together
   - Partial state is unacceptable

3. **ALWAYS call update_collection_status after marking paid**
   - Parent purchase tracks total collected
   - is_fully_paid flag must be accurate

4. **NEVER allow duplicate shares per user per purchase**
   - Enforce via unique_together constraint
   - Handle gracefully in code

5. **ALWAYS validate group membership for group purchases**
   - Check in serializer before creation
   - Non-members cannot create purchases in a group

**Typical Prompts:**

```
"Add multi-currency support"
-> Consider:
1. Add currency field to PurchaseRecord (already exists)
2. Add exchange rate tracking
3. Convert to base currency for splitting
4. Store original currency in shares
5. Update QR generation for currency

"Implement bank API auto-reconciliation"
-> Steps:
1. Add bank API credentials to settings
2. Create import management command
3. Match variable_symbol to payment_reference
4. Call reconcile_payment for matches
5. Handle partial matches and errors

"Add payment reminder emails"
-> Check:
1. Add Celery for async tasks
2. Create email templates
3. Track last reminder sent
4. Configurable reminder intervals
```

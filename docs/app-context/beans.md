# Beans App - Application Context

> **Last Updated:** 2025-12-14
> **Owner:** Filip Prudek
> **Status:** Development

---

## Purpose & Responsibility

Manages the coffee bean catalog including products, variants (package sizes), and pricing. Serves as the central product reference for reviews, purchases, and libraries.

**Core Responsibility:**
- Coffee bean product management (CRUD)
- Package variants with pricing (weight/price combinations)
- Aggregate rating calculation from reviews
- Search and filtering functionality
- Normalization for duplicate prevention

**NOT Responsible For:**
- User reviews (that's `reviews` app)
- Purchase tracking (that's `purchases` app)
- Group libraries (that's `groups` app)
- User personal libraries (that's `reviews` app)

---

## Models

### **CoffeeBean**

**Purpose:** Canonical coffee product representing a specific bean from a roastery.

**Fields:**
| Field | Type | Purpose | Business Rule |
|-------|------|---------|---------------|
| `id` | UUIDField (PK) | Unique identifier | Auto-generated |
| `name` | CharField(200) | Coffee name | Required, indexed |
| `roastery_name` | CharField(200) | Roaster/brand | Required, indexed |
| `name_normalized` | CharField(200) | Lowercase normalized | Auto-generated on save |
| `roastery_normalized` | CharField(200) | Lowercase normalized | Auto-generated on save |
| `origin_country` | CharField(100) | Country of origin | Optional |
| `region` | CharField(200) | Specific region | Optional |
| `processing` | CharField(50) | Processing method | Default: washed |
| `roast_profile` | CharField(50) | Roast level | Default: medium |
| `roast_date` | DateField | Date of roasting | Optional |
| `brew_method` | CharField(50) | Recommended brew | Default: filter |
| `description` | TextField | Detailed description | Optional |
| `tasting_notes` | CharField(500) | Flavor descriptors | Optional |
| `avg_rating` | Decimal(3,2) | Calculated average | Auto-updated from reviews |
| `review_count` | PositiveInt | Number of reviews | Auto-updated |
| `is_active` | BooleanField | Soft delete flag | Default: True |
| `created_by` | FK(User) | Creator reference | SET_NULL on delete |
| `created_at` | DateTimeField | Creation timestamp | Auto-set |
| `updated_at` | DateTimeField | Last update | Auto-set |

**Enum Choices:**
```python
class ProcessingMethod(models.TextChoices):
    WASHED = 'washed', 'Washed'
    NATURAL = 'natural', 'Natural/Dry'
    HONEY = 'honey', 'Honey'
    ANAEROBIC = 'anaerobic', 'Anaerobic'
    OTHER = 'other', 'Other'

class RoastProfile(models.TextChoices):
    LIGHT = 'light', 'Light'
    MEDIUM_LIGHT = 'medium_light', 'Medium-Light'
    MEDIUM = 'medium', 'Medium'
    MEDIUM_DARK = 'medium_dark', 'Medium-Dark'
    DARK = 'dark', 'Dark'

class BrewMethod(models.TextChoices):
    ESPRESSO = 'espresso', 'Espresso'
    FILTER = 'filter', 'Filter/Pour Over'
    FRENCH_PRESS = 'french_press', 'French Press'
    AEROPRESS = 'aeropress', 'AeroPress'
    MOKA = 'moka', 'Moka Pot'
    COLD_BREW = 'cold_brew', 'Cold Brew'
    AUTOMAT = 'automat', 'Automat'
    OTHER = 'other', 'Other'
```

**Relationships:**
- **Has Many:** CoffeeBeanVariant (via `variants`)
- **Has Many:** Review (via `reviews`)
- **Has Many:** UserLibraryEntry (via `library_entries`)
- **Has Many:** GroupLibraryEntry (via `group_library_entries`)
- **Has Many:** Purchase (via `purchases`)
- **Belongs To:** User (via `created_by`)

**Key Methods:**
```python
def save(self, *args, **kwargs):
    """Auto-generates normalized fields on save."""
    self.name_normalized = self._normalize_string(self.name)
    self.roastery_normalized = self._normalize_string(self.roastery_name)
    super().save(*args, **kwargs)

@staticmethod
def _normalize_string(text):
    """Lowercase, trim whitespace, remove special chars."""
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\s-]', '', text)
    return text

def update_aggregate_rating(self):
    """Recalculates avg_rating and review_count from all reviews.
    Called via transaction.on_commit() after review create/update/delete.
    """
    aggregates = self.reviews.aggregate(avg=Avg('rating'), count=Count('id'))
    self.avg_rating = aggregates['avg'] or Decimal('0.00')
    self.review_count = aggregates['count']
    self.save(update_fields=['avg_rating', 'review_count', 'updated_at'])
```

**Business Rules:**
1. **Unique Constraint:** `(name_normalized, roastery_normalized)` must be unique
2. **Soft Delete:** Sets `is_active=False` instead of hard delete
3. **Auto-Normalization:** Normalized fields computed on every save
4. **Aggregate Auto-Update:** `avg_rating` and `review_count` updated by reviews app

**Indexes:**
- `name` (for search)
- `roastery_name` (for filtering)
- `(name_normalized, roastery_normalized)` composite (for uniqueness)
- `avg_rating` (for sorting by rating)
- `created_at` (for sorting by date)

---

### **CoffeeBeanVariant**

**Purpose:** Package size and pricing for a coffee bean.

**Fields:**
| Field | Type | Purpose | Business Rule |
|-------|------|---------|---------------|
| `id` | UUIDField (PK) | Unique identifier | Auto-generated |
| `coffeebean` | FK(CoffeeBean) | Parent product | Required, CASCADE delete |
| `package_weight_grams` | PositiveInt | Package size in grams | Required, min 1 |
| `price_czk` | Decimal(10,2) | Price in CZK | Required, min 0.01 |
| `price_per_gram` | Decimal(10,4) | Calculated price/gram | Auto-calculated on save |
| `purchase_url` | URLField(500) | Link to buy | Optional |
| `is_active` | BooleanField | Soft delete flag | Default: True |
| `created_at` | DateTimeField | Creation timestamp | Auto-set |
| `updated_at` | DateTimeField | Last update | Auto-set |

**Relationships:**
- **Belongs To:** CoffeeBean (via `coffeebean`)
- **Has Many:** Purchase (via purchase's variant reference)

**Key Methods:**
```python
def save(self, *args, **kwargs):
    """Auto-calculates price_per_gram on save."""
    if self.price_czk and self.package_weight_grams:
        self.price_per_gram = self.price_czk / Decimal(self.package_weight_grams)
    super().save(*args, **kwargs)
```

**Business Rules:**
1. **Unique Constraint:** `(coffeebean, package_weight_grams)` must be unique
2. **Auto-Calculation:** `price_per_gram` computed on save
3. **Soft Delete:** Sets `is_active=False` instead of hard delete

**Indexes:**
- `(coffeebean, is_active)` (for active variants of a bean)
- `price_per_gram` (for value comparison sorting)

---

## API Endpoints

### CoffeeBean Endpoints

| Method | Endpoint | Purpose | Auth | Permissions |
|--------|----------|---------|------|-------------|
| GET | `/api/beans/` | List beans (paginated, filtered) | Optional | IsAuthenticatedOrReadOnly |
| POST | `/api/beans/` | Create bean | Required | IsAuthenticated |
| GET | `/api/beans/{id}/` | Get bean details + variants | Optional | IsAuthenticatedOrReadOnly |
| PUT | `/api/beans/{id}/` | Full update | Required | IsAuthenticated |
| PATCH | `/api/beans/{id}/` | Partial update | Required | IsAuthenticated |
| DELETE | `/api/beans/{id}/` | Soft delete (is_active=False) | Required | IsAuthenticated |
| GET | `/api/beans/roasteries/` | List all roastery names | Optional | IsAuthenticatedOrReadOnly |
| GET | `/api/beans/origins/` | List all origin countries | Optional | IsAuthenticatedOrReadOnly |

**Query Parameters for List:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `search` | string | Search in name, roastery, origin, description, tasting_notes |
| `roastery` | string | Filter by roastery name (icontains) |
| `origin` | string | Filter by origin country (icontains) |
| `roast_profile` | string | Filter by exact roast profile |
| `processing` | string | Filter by exact processing method |
| `min_rating` | decimal | Filter by minimum avg_rating |
| `page` | int | Page number (default: 1) |
| `page_size` | int | Items per page (default: 20, max: 100) |

### CoffeeBeanVariant Endpoints

| Method | Endpoint | Purpose | Auth | Permissions |
|--------|----------|---------|------|-------------|
| GET | `/api/beans/variants/` | List variants | Optional | IsAuthenticatedOrReadOnly |
| POST | `/api/beans/variants/` | Create variant | Required | IsAuthenticated |
| GET | `/api/beans/variants/{id}/` | Get variant details | Optional | IsAuthenticatedOrReadOnly |
| PATCH | `/api/beans/variants/{id}/` | Update variant | Required | IsAuthenticated |
| DELETE | `/api/beans/variants/{id}/` | Soft delete | Required | IsAuthenticated |

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `coffeebean` | UUID | Filter variants by parent bean ID |

---

## Business Logic & Workflows

### **Workflow 1: Bean Creation**

**Trigger:** POST to `/api/beans/`

**Steps:**
1. Validate required fields (name, roastery_name)
2. Auto-generate normalized fields
3. Check unique constraint `(name_normalized, roastery_normalized)`
4. Set `created_by` to current user
5. Save with default values for optional fields
6. Return created bean

**Code:**
```python
def perform_create(self, serializer):
    serializer.save(created_by=self.request.user)
```

**Edge Cases:**
- Duplicate bean: Returns 400 due to unique constraint violation
- Missing roastery_name: Returns 400 validation error
- Unauthenticated: Returns 401/403

### **Workflow 2: Aggregate Rating Update**

**Trigger:** Called by reviews app after review create/update/delete

**Steps:**
1. Aggregate all reviews for the bean
2. Calculate average rating
3. Count total reviews
4. Update `avg_rating` and `review_count`
5. Update `updated_at` timestamp

**Code:**
```python
def update_aggregate_rating(self):
    from django.db.models import Avg, Count
    aggregates = self.reviews.aggregate(avg=Avg('rating'), count=Count('id'))
    self.avg_rating = aggregates['avg'] or Decimal('0.00')
    self.review_count = aggregates['count']
    self.save(update_fields=['avg_rating', 'review_count', 'updated_at'])
```

**Important:** Called via `transaction.on_commit()` to ensure review is committed first.

### **Workflow 3: Soft Delete**

**Trigger:** DELETE request to bean or variant

**Steps:**
1. Find the object
2. Set `is_active = False`
3. Save only the `is_active` field
4. Return 204 No Content

**Code:**
```python
def perform_destroy(self, instance):
    instance.is_active = False
    instance.save(update_fields=['is_active'])
```

**Why Soft Delete:** Preserves historical data for reviews, purchases, and analytics.

---

## Permissions & Security

**Permission Classes:**
- `IsAuthenticatedOrReadOnly` - Anyone can view, only authenticated can modify

**Access Rules:**
| Action | Who Can Do It |
|--------|---------------|
| List/View | Everyone (public) |
| Create | Authenticated users |
| Update | Authenticated users |
| Delete | Authenticated users |

**Security Considerations:**
- No ownership restriction: Any authenticated user can edit any bean
- Soft delete prevents data loss
- Normalized fields prevent case-sensitive duplicates
- Query parameters are sanitized via Django ORM

**Future Consideration:** Add owner-only edit permission or admin approval for edits.

---

## Testing Strategy

**What to Test:**
1. CRUD operations for beans and variants
2. Search and filter functionality
3. Soft delete behavior
4. Normalization and unique constraint
5. Aggregate rating updates (integration with reviews)
6. Pagination

**Test Coverage:** 30+ test cases in `apps/beans/tests/test_api.py`

**Critical Test Cases:**
```python
def test_delete_bean_soft_deletes(self, authenticated_client, coffeebean):
    """Delete performs soft delete (sets is_active=False)."""
    url = reverse('beans:coffeebean-detail', args=[coffeebean.id])
    response = authenticated_client.delete(url)

    assert response.status_code == 204
    coffeebean.refresh_from_db()
    assert coffeebean.is_active is False
    assert CoffeeBean.objects.filter(id=coffeebean.id).exists()

def test_create_variant_calculates_price_per_gram(self, authenticated_client, coffeebean):
    """Price per gram is calculated automatically."""
    data = {
        'coffeebean': str(coffeebean.id),
        'package_weight_grams': 250,
        'price_czk': '250.00',
    }
    response = authenticated_client.post(url, data)

    assert Decimal(response.data['price_per_gram']) == Decimal('1.0000')
```

**Edge Cases to Test:**
- Search across multiple fields
- Empty origin_country excluded from origins list
- Inactive beans excluded from list and detail
- Variant filtering by coffeebean ID
- Pagination with 25+ beans

---

## Dependencies & Relationships

**This App Uses:**
- `accounts.User` - For `created_by` reference

**Used By:**
- `reviews` - Review references CoffeeBean, calls `update_aggregate_rating()`
- `purchases` - Purchase references CoffeeBean and CoffeeBeanVariant
- `groups` - GroupLibraryEntry references CoffeeBean
- `analytics` - Consumption and statistics calculations

**External Services:**
- None

---

## Common Patterns

**Pattern 1: Soft Delete QuerySet**
```python
# Always filter for active beans in queryset
queryset = CoffeeBean.objects.filter(is_active=True)

# Soft delete in perform_destroy
def perform_destroy(self, instance):
    instance.is_active = False
    instance.save(update_fields=['is_active'])
```

**When to Use:** All list/retrieve operations, delete operations

**Pattern 2: Auto-Calculated Fields**
```python
def save(self, *args, **kwargs):
    # Calculate derived values before saving
    self.price_per_gram = self.price_czk / Decimal(self.package_weight_grams)
    super().save(*args, **kwargs)
```

**When to Use:** Fields that depend on other field values

**Pattern 3: String Normalization for Uniqueness**
```python
@staticmethod
def _normalize_string(text):
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\s-]', '', text)
    return text
```

**When to Use:** Preventing case-sensitive or whitespace-variant duplicates

---

## Gotchas & Known Issues

**Issue 1: No Owner Restriction on Edits**
- **Symptom:** Any authenticated user can edit any bean
- **Cause:** `IsAuthenticatedOrReadOnly` doesn't check ownership
- **Workaround:** Acceptable for collaborative catalog
- **Status:** By design for MVP, consider for future

**Issue 2: Aggregate Rating Consistency**
- **Symptom:** `avg_rating` could be stale if `update_aggregate_rating()` fails
- **Cause:** Depends on reviews app calling update correctly
- **Workaround:** Use `transaction.on_commit()` in reviews app
- **Status:** Working as expected

**Issue 3: N+1 Queries on List**
- **Problem:** Loading variants for each bean
- **Solution:** Use `prefetch_related('variants')` in queryset
- **Status:** Already implemented in ViewSet

---

## Future Enhancements

**Planned:**
- [ ] Image upload for coffee beans
- [ ] Barcode/QR scanning for quick lookup
- [ ] Roastery as separate model with details

**Ideas:**
- [ ] Bean comparison feature
- [ ] Price history tracking
- [ ] Availability notifications

**Won't Do (and Why):**
- Complex inventory tracking - Out of scope for rating app
- E-commerce functionality - Use `purchase_url` for external links

---

## Related Documentation

- [API Reference](../API.md#beans-endpoints)
- [Database Schema](../DATABASE.md)
- Other App Contexts: [accounts](./accounts.md), [reviews](./reviews.md), [purchases](./purchases.md)

---

## Notes for Developers

> **Why Normalized Fields?**
> Prevents duplicates like "Ethiopia Yirgacheffe" and "ethiopia yirgacheffe" from being created as separate beans. The unique constraint on normalized fields catches these.

> **Why Soft Delete?**
> Coffee beans are referenced by reviews, purchases, and library entries. Hard delete would cascade and lose historical data. Soft delete preserves data integrity.

> **Why CZK Currency?**
> Initial market is Czech Republic. Currency field could be added later for internationalization.

---

## AI Assistant Context

**When modifying this app, ALWAYS remember:**

1. **NEVER hard delete beans or variants**
   - Always use soft delete (`is_active=False`)
   - Beans are referenced by reviews, purchases, libraries

2. **ALWAYS filter by `is_active=True` in querysets**
   - Base queryset should exclude inactive items
   - Prevents showing deleted beans to users

3. **ALWAYS use `prefetch_related('variants')` for bean lists**
   - Prevents N+1 queries
   - Already configured in ViewSet queryset

4. **NEVER modify `avg_rating` or `review_count` directly**
   - These are auto-calculated by `update_aggregate_rating()`
   - Only the reviews app should trigger updates

**Typical Prompts:**

```
"Add an image field to CoffeeBean"
-> Remember: Use ImageField, add MEDIA_ROOT config, update serializer,
   consider thumbnail generation

"Add owner-only edit permission"
-> Check: Create IsOwnerOrReadOnly permission class,
   handle created_by in get_permissions()

"Fix duplicate beans appearing"
-> Look for: Check normalized fields are being set,
   verify unique_together constraint exists
```

# Accounts App - Application Context

> **Last Updated:** 2025-12-14
> **Owner:** Filip Prudek
> **Status:** Development

---

## Purpose & Responsibility

Manages user authentication, profiles, and account lifecycle. Provides email-based authentication using JWT tokens with GDPR-compliant account management.

**Core Responsibility:**
- User authentication (registration, login, logout)
- User profile management
- Email verification system
- Password reset flow
- GDPR-compliant account deletion (anonymization)

**NOT Responsible For:**
- Group membership management (that's `groups` app)
- Review authorship tracking (that's `reviews` app)
- Purchase participant tracking (that's `purchases` app)

---

## Models

### **User**

**Purpose:** Custom user model with email-based authentication and UUID primary key.

**Fields:**
| Field | Type | Purpose | Business Rule |
|-------|------|---------|---------------|
| `id` | UUIDField (PK) | Unique identifier | Auto-generated, not editable |
| `email` | EmailField(255) | Login identifier | Unique, indexed |
| `display_name` | CharField(100) | Public display name | Optional, blank allowed |
| `email_verified` | BooleanField | Email verified status | Default: False |
| `verification_token` | CharField(64) | Email/reset token | Nullable, cleared after use |
| `is_active` | BooleanField | Account active status | Default: True |
| `is_staff` | BooleanField | Admin access | Default: False |
| `created_at` | DateTimeField | Account creation time | Auto-set on create |
| `last_login` | DateTimeField | Last login timestamp | Updated on each login |
| `gdpr_deleted_at` | DateTimeField | GDPR deletion time | Null until anonymized |
| `preferences` | JSONField | User preferences | Default: empty dict |

**Relationships:**
- **Has Many:** Review (via `author`)
- **Has Many:** GroupMembership (via `user`)
- **Has Many:** Purchase (via `purchaser`)
- **Has Many:** PaymentShare (via `user`)
- **Has Many:** UserLibraryEntry (via `user`)
- **Owns:** Group (via `owner`)

**Key Methods:**
```python
def get_display_name(self):
    """Return display name or email prefix if not set."""
    return self.display_name or self.email.split('@')[0]

def anonymize(self):
    """GDPR-compliant anonymization.
    - Sets email to 'deleted_{uuid}@anonymized.local'
    - Sets display_name to 'Deleted User'
    - Deactivates account
    - Clears password and preferences
    - Records deletion timestamp
    """
```

**Business Rules:**
1. **Email as Username:** Uses email field for authentication (USERNAME_FIELD = 'email')
2. **Password Hashing:** Passwords stored via Django's `set_password()` (never plain text)
3. **Soft Delete:** Account deletion uses `anonymize()` instead of hard delete
4. **Verification Token:** Shared for email verification and password reset (single use)

**Indexes:**
- `email` (for login lookups)
- `created_at` (for sorting by registration date)

---

## API Endpoints

| Method | Endpoint | Purpose | Auth | Permissions |
|--------|----------|---------|------|-------------|
| POST | `/api/auth/register/` | Create new account | None | AllowAny |
| POST | `/api/auth/login/` | Authenticate user | None | AllowAny |
| POST | `/api/auth/logout/` | Logout user | Required | IsAuthenticated |
| GET | `/api/auth/user/` | Get current user profile | Required | IsAuthenticated |
| PATCH | `/api/auth/user/update/` | Update profile | Required | IsAuthenticated |
| DELETE | `/api/auth/user/delete/` | Delete account (GDPR) | Required | IsAuthenticated |
| GET | `/api/auth/users/{id}/` | Get user by ID | Required | IsAuthenticated |
| POST | `/api/auth/verify-email/` | Verify email address | Required | IsAuthenticated |
| POST | `/api/auth/password-reset/` | Request password reset | None | AllowAny |
| POST | `/api/auth/password-reset/confirm/` | Confirm password reset | None | AllowAny |

**Response Format:**

Authentication endpoints return:
```json
{
  "message": "Login successful",
  "user": { "id": "uuid", "email": "...", "display_name": "..." },
  "tokens": { "access": "jwt_token", "refresh": "jwt_token" }
}
```

---

## Business Logic & Workflows

### **Workflow 1: User Registration**

**Trigger:** POST to `/api/auth/register/`

**Steps:**
1. Validate email format and uniqueness
2. Validate password strength (Django validators)
3. Validate password confirmation matches
4. Create user with hashed password
5. Generate verification token
6. Return JWT tokens immediately

**Code:**
```python
def create(self, validated_data):
    validated_data.pop('password_confirm')
    user = User.objects.create_user(
        email=validated_data['email'],
        password=validated_data['password'],
        display_name=validated_data.get('display_name', '')
    )
    user.verification_token = secrets.token_urlsafe(32)
    user.save(update_fields=['verification_token'])
    return user
```

**Edge Cases:**
- Duplicate email: Returns 400 with validation error
- Weak password: Returns 400 with Django password validation errors
- Missing password_confirm: Returns 400

### **Workflow 2: Login**

**Trigger:** POST to `/api/auth/login/`

**Steps:**
1. Validate email/password presence
2. Authenticate against database
3. Check if account is active
4. Update `last_login` timestamp
5. Generate and return JWT tokens

**Edge Cases:**
- Invalid credentials: Returns 401 (doesn't reveal which field is wrong)
- Inactive account: Returns 403

### **Workflow 3: GDPR Account Deletion**

**Trigger:** DELETE to `/api/auth/user/delete/`

**Steps:**
1. Verify current password
2. Require explicit confirmation (`confirm: true`)
3. Call `user.anonymize()`
4. Return 204 No Content

**Anonymization:**
```python
def anonymize(self):
    self.email = f"deleted_{self.id}@anonymized.local"
    self.display_name = "Deleted User"
    self.is_active = False
    self.gdpr_deleted_at = timezone.now()
    self.set_unusable_password()
    self.preferences = {}
    self.save()
```

**Data Preserved:**
- User ID (for foreign key integrity)
- Reviews, purchases, group memberships (attributed to "Deleted User")

---

## Permissions & Security

**Permission Classes:**
- `AllowAny` - Public endpoints (register, login, password reset)
- `IsAuthenticated` - Protected endpoints (profile, logout, delete)

**Access Rules:**
| Action | Who Can Do It |
|--------|---------------|
| Register | Anyone |
| Login | Anyone |
| View own profile | Authenticated user |
| Update own profile | Authenticated user |
| Delete own account | Authenticated user (with password confirmation) |
| View other user | Authenticated user |

**Security Considerations:**
- Password reset doesn't reveal if email exists (enumeration protection)
- Account deletion requires current password + explicit confirmation
- Email field is read-only (cannot be changed via profile update)
- JWT tokens have configurable expiration (see settings)
- Verification tokens are cleared after successful use

---

## Testing Strategy

**What to Test:**
1. Registration flow (success, validation errors)
2. Login flow (success, wrong password, inactive user)
3. Profile operations (get, update, read-only fields)
4. Account deletion (password verification, anonymization)
5. Password reset (token generation, confirmation)
6. Email verification flow

**Test Coverage:** 38 test cases in `apps/accounts/tests/test_api.py`

**Critical Test Cases:**
```python
def test_delete_account_success(self, authenticated_client, user):
    """Verify GDPR anonymization works correctly."""
    response = authenticated_client.delete(url, {
        'password': 'TestPass123!',
        'confirm': True,
    })
    assert response.status_code == 204
    user.refresh_from_db()
    assert user.is_active is False
    assert 'anonymized' in user.email
    assert user.gdpr_deleted_at is not None

def test_password_reset_nonexistent_email(self, api_client):
    """Ensure email enumeration is prevented."""
    response = api_client.post(url, {'email': 'nonexistent@example.com'})
    assert response.status_code == 200  # Always success
```

---

## Dependencies & Relationships

**This App Uses:**
- `django.contrib.auth` - BaseUserManager, PermissionsMixin
- `rest_framework_simplejwt` - JWT token generation
- `django.contrib.auth.password_validation` - Password strength validation

**Used By:**
- `reviews` - `Review.author` references User
- `groups` - `Group.owner`, `GroupMembership.user` reference User
- `purchases` - `Purchase.purchaser`, `PaymentShare.user` reference User
- `analytics` - Consumption tracking per user

**External Services:**
- Email service (TODO: not yet implemented for verification/reset emails)

---

## Common Patterns

**Pattern 1: Token-based Verification**
```python
# Generate token
user.verification_token = secrets.token_urlsafe(32)
user.save(update_fields=['verification_token'])

# Verify and clear token
if user.verification_token == provided_token:
    user.email_verified = True
    user.verification_token = None  # Clear after use
    user.save()
```

**When to Use:** Email verification, password reset

**Pattern 2: Read-Only Serializer Fields**
```python
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        read_only_fields = ['id', 'email', 'email_verified', 'created_at', 'last_login']
```

**When to Use:** When certain fields should never be modified by the client

---

## Gotchas & Known Issues

**Issue 1: Token Exposed in Development**
- **Symptom:** Password reset token returned in response
- **Cause:** Convenience for development without email service
- **Workaround:** Remove `'token': reset_token` line before production
- **Status:** TODO

**Issue 2: Token Blacklist Not Enabled**
- **Symptom:** Logout doesn't actually invalidate tokens
- **Cause:** JWT blacklist requires additional setup
- **Workaround:** Token expiration provides eventual invalidation
- **Status:** TODO - Enable `rest_framework_simplejwt.token_blacklist`

**Issue 3: Email Sending Not Implemented**
- **Symptom:** No actual emails sent for verification/reset
- **Cause:** Email service not configured
- **Workaround:** Use tokens from response (dev only)
- **Status:** TODO - Implement email sending

---

## Future Enhancements

**Planned:**
- [ ] Implement email sending for verification and password reset
- [ ] Enable JWT token blacklist for proper logout
- [ ] Add social authentication (OAuth2)
- [ ] Add two-factor authentication (2FA)

**Ideas:**
- [ ] Account recovery with backup codes
- [ ] Login history tracking
- [ ] Session management (list active sessions)

**Won't Do (and Why):**
- Username field - Email is simpler and more universal
- Multiple emails per user - Adds complexity without clear benefit

---

## Related Documentation

- [API Reference](../API.md#auth-endpoints)
- [Database Schema](../DATABASE.md)
- Other App Contexts: [reviews](./reviews.md), [groups](./groups.md), [purchases](./purchases.md)

---

## Notes for Developers

> **Why Email-Based Auth?**
> Email is universal and eliminates username availability issues. Users already know their email, reducing forgotten credential scenarios.

> **Why GDPR Anonymization vs Hard Delete?**
> Hard deleting users would cascade delete reviews, purchases, and break group memberships. Anonymization preserves data integrity while removing personal information.

> **JWT vs Session Auth:**
> JWT enables stateless API authentication, better for mobile apps and scalability. Session auth is also enabled for Django admin compatibility.

---

## AI Assistant Context

**When modifying this app, ALWAYS remember:**

1. **NEVER expose sensitive data in responses**
   - Password hashes should never be serialized
   - Verification tokens should only be exposed in development

2. **ALWAYS hash passwords using set_password()**
   - Never store plain text passwords
   - Use `User.objects.create_user()` which handles hashing

3. **ALWAYS clear verification tokens after use**
   - Single-use tokens prevent replay attacks
   - Set to `None` after successful verification/reset

4. **NEVER reveal email existence on password reset**
   - Return success message regardless of email existing
   - Prevents user enumeration attacks

**Typical Prompts:**

```
"Add a field to track last password change"
-> Remember: Add to model, add migration, exclude from serializer output

"Implement email sending for verification"
-> Check: Create async task, use SMTP settings from config, handle failures gracefully

"Add OAuth/social login"
-> Consider: Use django-allauth or social-auth-app-django,
   handle account linking with existing emails
```

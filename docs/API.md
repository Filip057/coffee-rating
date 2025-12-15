# Coffee Rating API Documentation

> **Version:** 0.5.0
> **Base URL:** `http://localhost:8000/api/`
> **Last Updated:** 2025-12-14

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Error Handling](#error-handling)
4. [Pagination](#pagination)
5. [Filtering & Search](#filtering--search)
6. [Endpoints](#endpoints)
   - [Auth](#auth-endpoints)
   - [Beans](#beans-endpoints)
   - [Reviews](#reviews-endpoints)
   - [Groups](#groups-endpoints)
   - [Purchases](#purchases-endpoints)
   - [Analytics](#analytics-endpoints)

---

## Overview

The Coffee Rating API provides endpoints for tracking coffee bean purchases, reviews, and group consumption. It uses REST conventions with JSON request/response bodies.

**Interactive Documentation:**
- Swagger UI: `http://localhost:8000/api/docs/`
- OpenAPI Schema: `http://localhost:8000/api/schema/`

---

## Authentication

The API uses JWT (JSON Web Tokens) for authentication.

### Getting Tokens

**Login:**
```http
POST /api/auth/login/
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "yourpassword"
}
```

**Response:**
```json
{
  "message": "Login successful",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "display_name": "John"
  },
  "tokens": {
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
  }
}
```

### Using Tokens

Include the access token in the `Authorization` header:

```http
GET /api/beans/
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

### Refreshing Tokens

```http
POST /api/auth/token/refresh/
Content-Type: application/json

{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Response:**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### Token Lifetimes

| Token Type | Lifetime |
|------------|----------|
| Access | 60 minutes |
| Refresh | 7 days |

---

## Error Handling

### HTTP Status Codes

| Code | Meaning | When Used |
|------|---------|-----------|
| 200 | OK | Successful GET, PUT, PATCH |
| 201 | Created | Successful POST (resource created) |
| 204 | No Content | Successful DELETE |
| 400 | Bad Request | Validation error, invalid data |
| 401 | Unauthorized | Missing or invalid token |
| 403 | Forbidden | Valid token but insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 500 | Server Error | Unexpected server error |

### Error Response Format

```json
{
  "error": "Description of what went wrong"
}
```

**Validation Errors (400):**
```json
{
  "email": ["This field is required."],
  "password": ["Password must be at least 8 characters."]
}
```

**Authentication Error (401):**
```json
{
  "detail": "Authentication credentials were not provided."
}
```

**Permission Error (403):**
```json
{
  "detail": "You do not have permission to perform this action."
}
```

---

## Pagination

List endpoints return paginated results:

```json
{
  "count": 150,
  "next": "http://localhost:8000/api/beans/?page=2",
  "previous": null,
  "results": [...]
}
```

### Query Parameters

| Parameter | Default | Max | Description |
|-----------|---------|-----|-------------|
| `page` | 1 | - | Page number |
| `page_size` | 20 | 100 | Items per page |

**Example:**
```http
GET /api/beans/?page=2&page_size=50
```

---

## Filtering & Search

### Common Filter Patterns

**Exact match:**
```http
GET /api/beans/?roast_profile=light
```

**Contains (case-insensitive):**
```http
GET /api/beans/?roastery=doubleshot
```

**Date range:**
```http
GET /api/purchases/?date_from=2025-01-01&date_to=2025-12-31
```

**Boolean:**
```http
GET /api/purchases/?is_fully_paid=true
```

**Search (multiple fields):**
```http
GET /api/beans/?search=ethiopia
```

---

## Endpoints

---

## Auth Endpoints

### Register

Create a new user account.

```http
POST /api/auth/register/
```

**Request:**
```json
{
  "email": "newuser@example.com",
  "password": "SecurePass123!",
  "password_confirm": "SecurePass123!",
  "display_name": "John Doe"
}
```

**Response (201):**
```json
{
  "message": "Registration successful",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "newuser@example.com",
    "display_name": "John Doe"
  },
  "tokens": {
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
  }
}
```

**Errors:**
- `400` - Email already exists, password too weak, passwords don't match

---

### Login

Authenticate and get JWT tokens.

```http
POST /api/auth/login/
```

**Request:**
```json
{
  "email": "user@example.com",
  "password": "yourpassword"
}
```

**Response (200):**
```json
{
  "message": "Login successful",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "display_name": "John"
  },
  "tokens": {
    "access": "eyJ...",
    "refresh": "eyJ..."
  }
}
```

**Errors:**
- `401` - Invalid credentials

---

### Logout

Logout current user.

```http
POST /api/auth/logout/
Authorization: Bearer {token}
```

**Request:**
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Response (200):**
```json
{
  "message": "Logout successful"
}
```

---

### Get Current User

Get authenticated user's profile.

```http
GET /api/auth/user/
Authorization: Bearer {token}
```

**Response (200):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "display_name": "John",
  "email_verified": true,
  "created_at": "2025-01-15T10:30:00Z",
  "last_login": "2025-12-14T08:00:00Z"
}
```

---

### Update Profile

Update current user's profile.

```http
PATCH /api/auth/user/update/
Authorization: Bearer {token}
```

**Request:**
```json
{
  "display_name": "Johnny"
}
```

**Response (200):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "display_name": "Johnny",
  "email_verified": true
}
```

**Note:** Email cannot be changed via this endpoint.

---

### Delete Account (GDPR)

Anonymize and deactivate account.

```http
DELETE /api/auth/user/delete/
Authorization: Bearer {token}
```

**Request:**
```json
{
  "password": "yourpassword",
  "confirm": true
}
```

**Response (204):** No content

**Note:** This anonymizes your data instead of hard deleting. Reviews and purchases are preserved but attributed to "Deleted User".

---

### Request Password Reset

Request a password reset token.

```http
POST /api/auth/password-reset/
```

**Request:**
```json
{
  "email": "user@example.com"
}
```

**Response (200):**
```json
{
  "message": "If this email exists, a reset link has been sent."
}
```

**Note:** Returns success even for non-existent emails (security measure).

---

### Confirm Password Reset

Reset password using token.

```http
POST /api/auth/password-reset/confirm/
```

**Request:**
```json
{
  "token": "abc123...",
  "password": "NewSecurePass123!",
  "password_confirm": "NewSecurePass123!"
}
```

**Response (200):**
```json
{
  "message": "Password reset successful"
}
```

---

## Beans Endpoints

### List Beans

Get paginated list of coffee beans.

```http
GET /api/beans/
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `search` | string | Search in name, roastery, origin, description, tasting_notes |
| `roastery` | string | Filter by roastery name (contains) |
| `origin` | string | Filter by origin country (contains) |
| `roast_profile` | string | Exact match: light, medium_light, medium, medium_dark, dark |
| `processing` | string | Exact match: washed, natural, honey, anaerobic, other |
| `min_rating` | decimal | Minimum average rating |

**Response (200):**
```json
{
  "count": 42,
  "next": "http://localhost:8000/api/beans/?page=2",
  "previous": null,
  "results": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Ethiopia Yirgacheffe",
      "roastery_name": "Doubleshot",
      "origin_country": "Ethiopia",
      "region": "Yirgacheffe",
      "processing": "washed",
      "roast_profile": "light",
      "avg_rating": "4.50",
      "review_count": 12,
      "is_active": true
    }
  ]
}
```

---

### Create Bean

Create a new coffee bean.

```http
POST /api/beans/
Authorization: Bearer {token}
```

**Request:**
```json
{
  "name": "Ethiopia Yirgacheffe",
  "roastery_name": "Doubleshot",
  "origin_country": "Ethiopia",
  "region": "Yirgacheffe",
  "processing": "washed",
  "roast_profile": "light",
  "brew_method": "filter",
  "description": "Bright and fruity with floral notes",
  "tasting_notes": "Blueberry, jasmine, bergamot"
}
```

**Response (201):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Ethiopia Yirgacheffe",
  "roastery_name": "Doubleshot",
  "name_normalized": "ethiopia yirgacheffe",
  "roastery_normalized": "doubleshot",
  "origin_country": "Ethiopia",
  "region": "Yirgacheffe",
  "processing": "washed",
  "roast_profile": "light",
  "brew_method": "filter",
  "description": "Bright and fruity with floral notes",
  "tasting_notes": "Blueberry, jasmine, bergamot",
  "avg_rating": "0.00",
  "review_count": 0,
  "is_active": true,
  "created_by": "550e8400-e29b-41d4-a716-446655440001",
  "created_at": "2025-12-14T10:00:00Z",
  "variants": []
}
```

**Errors:**
- `400` - Bean with same name/roastery already exists

---

### Get Bean Details

Get a single bean with its variants.

```http
GET /api/beans/{id}/
```

**Response (200):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Ethiopia Yirgacheffe",
  "roastery_name": "Doubleshot",
  "origin_country": "Ethiopia",
  "region": "Yirgacheffe",
  "processing": "washed",
  "roast_profile": "light",
  "brew_method": "filter",
  "description": "Bright and fruity with floral notes",
  "tasting_notes": "Blueberry, jasmine, bergamot",
  "avg_rating": "4.50",
  "review_count": 12,
  "is_active": true,
  "variants": [
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "package_weight_grams": 250,
      "price_czk": "299.00",
      "price_per_gram": "1.1960",
      "purchase_url": "https://doubleshot.cz/product/123",
      "is_active": true
    },
    {
      "id": "660e8400-e29b-41d4-a716-446655440002",
      "package_weight_grams": 1000,
      "price_czk": "999.00",
      "price_per_gram": "0.9990",
      "purchase_url": null,
      "is_active": true
    }
  ]
}
```

---

### Update Bean

Update a coffee bean.

```http
PATCH /api/beans/{id}/
Authorization: Bearer {token}
```

**Request:**
```json
{
  "description": "Updated description",
  "tasting_notes": "Updated notes"
}
```

**Response (200):** Updated bean object

---

### Delete Bean

Soft delete a bean (sets is_active=false).

```http
DELETE /api/beans/{id}/
Authorization: Bearer {token}
```

**Response (204):** No content

---

### List Roasteries

Get all unique roastery names.

```http
GET /api/beans/roasteries/
```

**Response (200):**
```json
[
  "Doubleshot",
  "La Boheme",
  "Nordbeans",
  "Father's Coffee"
]
```

---

### List Origins

Get all unique origin countries.

```http
GET /api/beans/origins/
```

**Response (200):**
```json
[
  "Ethiopia",
  "Colombia",
  "Kenya",
  "Brazil"
]
```

---

### Variants

#### List Variants

```http
GET /api/beans/variants/?coffeebean={bean_id}
```

#### Create Variant

```http
POST /api/beans/variants/
Authorization: Bearer {token}
```

**Request:**
```json
{
  "coffeebean": "550e8400-e29b-41d4-a716-446655440000",
  "package_weight_grams": 250,
  "price_czk": "299.00",
  "purchase_url": "https://shop.com/product"
}
```

**Response (201):**
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "coffeebean": "550e8400-e29b-41d4-a716-446655440000",
  "package_weight_grams": 250,
  "price_czk": "299.00",
  "price_per_gram": "1.1960",
  "purchase_url": "https://shop.com/product",
  "is_active": true
}
```

**Note:** `price_per_gram` is automatically calculated.

---

## Reviews Endpoints

### List Reviews

Get paginated list of reviews.

```http
GET /api/reviews/
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `coffeebean` | UUID | Filter by bean |
| `author` | UUID | Filter by author |
| `group` | UUID | Filter by group |
| `rating` | int | Exact rating (1-5) |
| `min_rating` | int | Minimum rating |
| `context` | string | personal, group, public |
| `search` | string | Search in notes, bean name, roastery |
| `tag` | UUID | Filter by taste tag |

**Response (200):**
```json
{
  "count": 25,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "770e8400-e29b-41d4-a716-446655440000",
      "coffeebean": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "Ethiopia Yirgacheffe",
        "roastery_name": "Doubleshot"
      },
      "author": {
        "id": "880e8400-e29b-41d4-a716-446655440000",
        "email": "user@example.com",
        "display_name": "John"
      },
      "rating": 5,
      "aroma_score": 5,
      "flavor_score": 4,
      "acidity_score": 4,
      "body_score": 3,
      "aftertaste_score": 5,
      "notes": "Amazing fruity notes, very clean cup",
      "brew_method": "filter",
      "taste_tags": [
        {"id": "990e8400...", "name": "fruity"},
        {"id": "990e8401...", "name": "floral"}
      ],
      "context": "personal",
      "would_buy_again": true,
      "created_at": "2025-12-14T10:00:00Z"
    }
  ]
}
```

---

### Create Review

Create a review for a coffee bean.

```http
POST /api/reviews/
Authorization: Bearer {token}
```

**Request:**
```json
{
  "coffeebean": "550e8400-e29b-41d4-a716-446655440000",
  "rating": 5,
  "aroma_score": 5,
  "flavor_score": 4,
  "acidity_score": 4,
  "body_score": 3,
  "aftertaste_score": 5,
  "notes": "Amazing fruity notes, very clean cup",
  "brew_method": "filter",
  "taste_tags": ["990e8400...", "990e8401..."],
  "context": "personal",
  "would_buy_again": true
}
```

**Response (201):** Created review object

**Side Effects:**
- Automatically adds bean to user's library
- Updates bean's `avg_rating` and `review_count`

**Errors:**
- `400` - Already reviewed this bean (one review per user per bean)

---

### Get My Reviews

Get current user's reviews.

```http
GET /api/reviews/my_reviews/
Authorization: Bearer {token}
```

---

### Get Bean Review Summary

Get review statistics for a bean.

```http
GET /api/reviews/bean/{bean_id}/summary/
```

**Response (200):**
```json
{
  "bean_id": "550e8400-e29b-41d4-a716-446655440000",
  "review_count": 12,
  "avg_rating": 4.5,
  "rating_distribution": {
    "5": 6,
    "4": 4,
    "3": 2,
    "2": 0,
    "1": 0
  },
  "avg_scores": {
    "aroma": 4.2,
    "flavor": 4.5,
    "acidity": 4.0,
    "body": 3.8,
    "aftertaste": 4.3
  },
  "common_tags": [
    {"tag": "fruity", "count": 8},
    {"tag": "floral", "count": 5}
  ]
}
```

---

### User Library

#### Get My Library

```http
GET /api/reviews/library/
Authorization: Bearer {token}
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `archived` | bool | Include archived entries (default: false) |
| `search` | string | Search in bean name or roastery |

**Response (200):**
```json
[
  {
    "id": "aa0e8400-e29b-41d4-a716-446655440000",
    "coffeebean": {
      "id": "550e8400...",
      "name": "Ethiopia Yirgacheffe",
      "roastery_name": "Doubleshot"
    },
    "added_by": "review",
    "added_at": "2025-12-14T10:00:00Z",
    "own_price_czk": null,
    "is_archived": false
  }
]
```

#### Add to Library

```http
POST /api/reviews/library/add/
Authorization: Bearer {token}
```

**Request:**
```json
{
  "coffeebean_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

#### Archive Library Entry

```http
PATCH /api/reviews/library/{id}/archive/
Authorization: Bearer {token}
```

**Request:**
```json
{
  "is_archived": true
}
```

---

### Tags

#### List Tags

```http
GET /api/reviews/tags/
```

**Response (200):**
```json
[
  {"id": "990e8400...", "name": "fruity", "category": "flavor"},
  {"id": "990e8401...", "name": "chocolate", "category": "flavor"},
  {"id": "990e8402...", "name": "nutty", "category": "flavor"}
]
```

#### Create Tag

```http
POST /api/reviews/tags/create/
Authorization: Bearer {token}
```

**Request:**
```json
{
  "name": "tropical",
  "category": "flavor"
}
```

---

## Groups Endpoints

### List My Groups

Get groups where user is a member.

```http
GET /api/groups/
Authorization: Bearer {token}
```

**Response (200):**
```json
{
  "count": 2,
  "results": [
    {
      "id": "bb0e8400-e29b-41d4-a716-446655440000",
      "name": "Coffee Lovers",
      "description": "A group for coffee enthusiasts",
      "is_private": true,
      "member_count": 5,
      "owner": {
        "id": "880e8400...",
        "display_name": "John"
      },
      "created_at": "2025-01-01T10:00:00Z"
    }
  ]
}
```

---

### Create Group

```http
POST /api/groups/
Authorization: Bearer {token}
```

**Request:**
```json
{
  "name": "Office Coffee Club",
  "description": "Coffee tracking for our office",
  "is_private": true
}
```

**Response (201):**
```json
{
  "id": "bb0e8400-e29b-41d4-a716-446655440000",
  "name": "Office Coffee Club",
  "description": "Coffee tracking for our office",
  "is_private": true,
  "invite_code": "abc123xyz789",
  "owner": {...},
  "created_at": "2025-12-14T10:00:00Z"
}
```

**Note:** Creator automatically becomes owner and first member.

---

### Get Group Details

```http
GET /api/groups/{id}/
Authorization: Bearer {token}
```

**Response (200):** Full group object with invite_code (members only)

---

### Join Group

Join a group using invite code.

```http
POST /api/groups/{id}/join/
Authorization: Bearer {token}
```

**Request:**
```json
{
  "invite_code": "abc123xyz789"
}
```

**Response (201):**
```json
{
  "id": "cc0e8400...",
  "user": {...},
  "group": "bb0e8400...",
  "role": "member",
  "joined_at": "2025-12-14T10:00:00Z"
}
```

**Errors:**
- `400` - Invalid invite code
- `400` - Already a member

---

### Leave Group

```http
POST /api/groups/{id}/leave/
Authorization: Bearer {token}
```

**Response (204):** No content

**Errors:**
- `400` - Owner cannot leave (must transfer ownership or delete group)

---

### Get Members

```http
GET /api/groups/{id}/members/
Authorization: Bearer {token}
```

**Response (200):**
```json
[
  {
    "id": "cc0e8400...",
    "user": {
      "id": "880e8400...",
      "email": "owner@example.com",
      "display_name": "John"
    },
    "role": "owner",
    "joined_at": "2025-01-01T10:00:00Z"
  },
  {
    "id": "cc0e8401...",
    "user": {...},
    "role": "admin",
    "joined_at": "2025-02-15T10:00:00Z"
  },
  {
    "id": "cc0e8402...",
    "user": {...},
    "role": "member",
    "joined_at": "2025-03-20T10:00:00Z"
  }
]
```

---

### Update Member Role

Change a member's role (admin only).

```http
POST /api/groups/{id}/update_member_role/
Authorization: Bearer {token}
```

**Request:**
```json
{
  "user_id": "880e8400-e29b-41d4-a716-446655440001",
  "role": "admin"
}
```

**Allowed roles:** `admin`, `member`

**Errors:**
- `400` - Cannot change owner's role
- `403` - Only admins can change roles

---

### Remove Member

```http
DELETE /api/groups/{id}/remove_member/
Authorization: Bearer {token}
```

**Request:**
```json
{
  "user_id": "880e8400-e29b-41d4-a716-446655440001"
}
```

**Errors:**
- `400` - Cannot remove owner

---

### Regenerate Invite Code

```http
POST /api/groups/{id}/regenerate_invite/
Authorization: Bearer {token}
```

**Response (200):**
```json
{
  "invite_code": "newcode123xyz",
  "message": "Invite code regenerated successfully"
}
```

---

### Group Library

#### Get Group Library

```http
GET /api/groups/{id}/library/
Authorization: Bearer {token}
```

#### Add to Group Library

```http
POST /api/groups/{id}/add_to_library/
Authorization: Bearer {token}
```

**Request:**
```json
{
  "coffeebean_id": "550e8400-e29b-41d4-a716-446655440000",
  "notes": "Great for the office espresso machine"
}
```

---

## Purchases Endpoints

### List Purchases

Get purchases where user is buyer or has a payment share.

```http
GET /api/purchases/
Authorization: Bearer {token}
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `group` | UUID | Filter by group |
| `user` | UUID | Filter by user |
| `date_from` | date | Start date (YYYY-MM-DD) |
| `date_to` | date | End date (YYYY-MM-DD) |
| `is_fully_paid` | bool | Filter by payment status |

**Response (200):**
```json
{
  "count": 10,
  "results": [
    {
      "id": "dd0e8400-e29b-41d4-a716-446655440000",
      "group": "bb0e8400...",
      "coffeebean_name": "Doubleshot - Ethiopia Yirgacheffe",
      "bought_by": {
        "id": "880e8400...",
        "display_name": "John"
      },
      "total_price_czk": "900.00",
      "date": "2025-12-10",
      "is_fully_paid": false,
      "created_at": "2025-12-10T14:00:00Z"
    }
  ]
}
```

---

### Create Purchase

Create a purchase (personal or group).

```http
POST /api/purchases/
Authorization: Bearer {token}
```

**Personal Purchase:**
```json
{
  "coffeebean": "550e8400-e29b-41d4-a716-446655440000",
  "variant": "660e8400-e29b-41d4-a716-446655440001",
  "total_price_czk": "299.00",
  "package_weight_grams": 250,
  "date": "2025-12-14",
  "purchase_location": "Doubleshot Shop",
  "note": "Great deal!"
}
```

**Group Purchase (splits among all members):**
```json
{
  "group": "bb0e8400-e29b-41d4-a716-446655440000",
  "coffeebean": "550e8400-e29b-41d4-a716-446655440000",
  "total_price_czk": "900.00",
  "package_weight_grams": 1000,
  "date": "2025-12-14"
}
```

**Group Purchase (split among specific members):**
```json
{
  "group": "bb0e8400-e29b-41d4-a716-446655440000",
  "coffeebean": "550e8400-e29b-41d4-a716-446655440000",
  "total_price_czk": "600.00",
  "date": "2025-12-14",
  "split_members": [
    "880e8400-e29b-41d4-a716-446655440000",
    "880e8400-e29b-41d4-a716-446655440001"
  ]
}
```

**Response (201):**
```json
{
  "id": "dd0e8400-e29b-41d4-a716-446655440000",
  "group": "bb0e8400...",
  "coffeebean": {...},
  "variant": {...},
  "bought_by": {...},
  "total_price_czk": "900.00",
  "package_weight_grams": 1000,
  "date": "2025-12-14",
  "total_collected_czk": "0.00",
  "is_fully_paid": false,
  "payment_shares": [
    {
      "id": "ee0e8400...",
      "user": {...},
      "amount_czk": "300.00",
      "status": "unpaid",
      "payment_reference": "COFFEE-DD0E8400-1234"
    },
    ...
  ]
}
```

**Note:** Payment amounts are split with haléř precision (100.00 CZK / 3 = 33.34 + 33.33 + 33.33).

---

### Get Purchase Summary

Get detailed payment status for a purchase.

```http
GET /api/purchases/{id}/summary/
Authorization: Bearer {token}
```

**Response (200):**
```json
{
  "purchase": {...},
  "total_amount": "900.00",
  "collected_amount": "300.00",
  "outstanding_amount": "600.00",
  "is_fully_paid": false,
  "total_shares": 3,
  "paid_count": 1,
  "unpaid_count": 2,
  "paid_shares": [...],
  "unpaid_shares": [...]
}
```

---

### Get Payment Shares

```http
GET /api/purchases/{id}/shares/
Authorization: Bearer {token}
```

---

### Mark Share as Paid

```http
POST /api/purchases/{id}/mark_paid/
Authorization: Bearer {token}
```

**By payment reference:**
```json
{
  "payment_reference": "COFFEE-DD0E8400-1234"
}
```

**Own share (no reference needed):**
```json
{}
```

**Response (200):**
```json
{
  "id": "ee0e8400...",
  "user": {...},
  "amount_czk": "300.00",
  "status": "paid",
  "paid_at": "2025-12-14T15:00:00Z",
  "paid_by": {...}
}
```

---

### My Outstanding Payments

Get all unpaid shares for current user.

```http
GET /api/purchases/my_outstanding/
Authorization: Bearer {token}
```

**Response (200):**
```json
{
  "total_outstanding": "450.00",
  "count": 3,
  "shares": [
    {
      "id": "ee0e8400...",
      "purchase": "dd0e8400...",
      "amount_czk": "150.00",
      "status": "unpaid",
      "payment_reference": "COFFEE-DD0E8400-1234"
    }
  ]
}
```

---

### Payment Share QR Code

Get QR code for payment (Czech SPD format).

```http
GET /api/purchases/shares/{id}/qr_code/
Authorization: Bearer {token}
```

**Response (200):**
```json
{
  "qr_url": "SPD*1.0*ACC:CZ1234567890*AM:300.00*CC:CZK*MSG:Coffee purchase*X-VS:COFFEE-DD0E8400-1234",
  "qr_image_path": "/media/qr_codes/qr_COFFEE-DD0E8400-1234.png",
  "payment_reference": "COFFEE-DD0E8400-1234",
  "amount_czk": "300.00"
}
```

---

## Analytics Endpoints

### User Consumption

Get user's coffee consumption statistics.

```http
GET /api/analytics/user/consumption/
Authorization: Bearer {token}
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `period` | string | Month (YYYY-MM) |
| `start_date` | date | Start date (YYYY-MM-DD) |
| `end_date` | date | End date (YYYY-MM-DD) |

**Response (200):**
```json
{
  "total_kg": 2.5,
  "total_spent_czk": 2450.00,
  "purchases_count": 8,
  "avg_price_per_kg": 980.00,
  "period_start": "2025-01-01",
  "period_end": "2025-12-31"
}
```

**Specific user:**
```http
GET /api/analytics/user/{user_id}/consumption/
```

---

### Group Consumption

Get group's consumption with member breakdown.

```http
GET /api/analytics/group/{group_id}/consumption/
Authorization: Bearer {token}
```

**Response (200):**
```json
{
  "total_kg": 5.0,
  "total_spent_czk": 4500.00,
  "purchases_count": 12,
  "member_breakdown": [
    {
      "user": {
        "id": "880e8400...",
        "email": "john@example.com",
        "display_name": "John"
      },
      "total_kg": 1.8,
      "total_spent_czk": 1620.00,
      "share_percentage": 36.0
    },
    ...
  ]
}
```

---

### Top Beans

Get top-ranked coffee beans (public endpoint).

```http
GET /api/analytics/beans/top/
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `metric` | string | rating | rating, kg, money, reviews |
| `period` | int | 30 | Number of days to consider |
| `limit` | int | 10 | Number of results |

**Response (200):**
```json
{
  "metric": "rating",
  "period_days": 30,
  "results": [
    {
      "id": "550e8400...",
      "name": "Ethiopia Yirgacheffe",
      "roastery_name": "Doubleshot",
      "score": 4.8,
      "metric": "Average Rating",
      "review_count": 15,
      "avg_rating": 4.8
    }
  ]
}
```

---

### Consumption Timeseries

Get consumption over time for charts.

```http
GET /api/analytics/timeseries/
Authorization: Bearer {token}
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `user_id` | UUID | User ID (defaults to current) |
| `group_id` | UUID | Group ID (for group data) |
| `granularity` | string | day, week, month (default: month) |

**Response (200):**
```json
{
  "granularity": "month",
  "data": [
    {
      "period": "2025-01",
      "kg": 0.75,
      "czk": 750.00,
      "purchases_count": 3
    },
    {
      "period": "2025-02",
      "kg": 1.0,
      "czk": 900.00,
      "purchases_count": 4
    }
  ]
}
```

---

### Taste Profile

Get user's taste preferences from reviews.

```http
GET /api/analytics/user/taste-profile/
Authorization: Bearer {token}
```

**Response (200):**
```json
{
  "review_count": 15,
  "avg_rating": 4.2,
  "favorite_tags": [
    {"tag": "fruity", "count": 8},
    {"tag": "chocolate", "count": 5},
    {"tag": "floral", "count": 4}
  ],
  "preferred_roast": "light",
  "preferred_origin": "Ethiopia"
}
```

---

### Dashboard

Get dashboard summary for current user.

```http
GET /api/analytics/dashboard/
Authorization: Bearer {token}
```

**Response (200):**
```json
{
  "consumption": {
    "total_kg": 0.5,
    "total_spent_czk": 500.00,
    "purchases_count": 2,
    "avg_price_per_kg": 1000.00
  },
  "taste_profile": {
    "review_count": 5,
    "avg_rating": 4.2,
    "favorite_tags": [...],
    "preferred_roast": "light",
    "preferred_origin": "Ethiopia"
  },
  "top_beans": [
    {
      "id": "550e8400...",
      "name": "Ethiopia Yirgacheffe",
      "roastery_name": "Doubleshot",
      "avg_rating": 4.8,
      "review_count": 15
    }
  ]
}
```

---

## Appendix

### Processing Methods

| Value | Display |
|-------|---------|
| `washed` | Washed |
| `natural` | Natural/Dry |
| `honey` | Honey |
| `anaerobic` | Anaerobic |
| `other` | Other |

### Roast Profiles

| Value | Display |
|-------|---------|
| `light` | Light |
| `medium_light` | Medium-Light |
| `medium` | Medium |
| `medium_dark` | Medium-Dark |
| `dark` | Dark |

### Brew Methods

| Value | Display |
|-------|---------|
| `espresso` | Espresso |
| `filter` | Filter/Pour Over |
| `french_press` | French Press |
| `aeropress` | AeroPress |
| `moka` | Moka Pot |
| `cold_brew` | Cold Brew |
| `automat` | Automat |
| `other` | Other |

### Group Roles

| Role | Permissions |
|------|-------------|
| `owner` | All permissions, cannot be removed |
| `admin` | Manage members, regenerate invite, update group |
| `member` | View group, add to library, create purchases |

### Payment Statuses

| Status | Description |
|--------|-------------|
| `unpaid` | Payment pending |
| `paid` | Payment confirmed |
| `failed` | Payment failed |
| `refunded` | Payment refunded |

---

## Test Accounts

For development/testing:

| Email | Password | Notes |
|-------|----------|-------|
| admin@example.com | admin123 | Superuser |
| alice@example.com | password123 | Regular user |
| bob@example.com | password123 | Regular user |
| charlie@example.com | password123 | Regular user |

Create test data: `python manage.py create_sample_data --clear`

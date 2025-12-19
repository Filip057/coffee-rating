# ☕ Coffee Rating API

A comprehensive Django REST API for coffee enthusiasts to track, rate, and share their coffee experiences. Built for individuals and teams to manage coffee purchases, reviews, and consumption analytics.

**Version:** 1.0.0
**Status:** Development

---

## 🎯 Overview

Coffee Rating is a full-featured coffee tracking platform that enables users to:
- Catalog and discover coffee beans from various roasteries
- Write detailed reviews with taste profiles
- Track personal and group coffee purchases with precise payment splitting
- Analyze consumption patterns and spending
- Collaborate with teams through shared group libraries

---

## ✨ Key Features

### 🫘 Coffee Bean Catalog
- Comprehensive bean database with roastery, origin, processing method, and roast profiles
- Multiple package variants with pricing and weight tracking
- Aggregate ratings calculated from user reviews
- Advanced search and filtering capabilities
- Duplicate prevention through normalized fields

**Documentation:** [docs/app-context/beans.md](docs/app-context/beans.md)

### ⭐ Reviews & Ratings
- 1-5 star rating system with detailed scoring (aroma, flavor, acidity, body, aftertaste)
- Personal, group, and public review contexts
- Taste tag system for flavor profiling
- Personal coffee library management
- Automatic library entry creation on first review
- One review per user per bean policy

**Documentation:** [docs/app-context/reviews.md](docs/app-context/reviews.md)

### 💰 Purchase Tracking & Payment Splitting
- Personal and group purchase recording
- Haléř-precise payment splitting (Czech currency precision)
- Payment share tracking with multiple statuses (unpaid/paid/failed/refunded)
- Automatic payment reference generation for bank reconciliation
- SPD QR code generation for Czech banking system
- Purchase reconciliation tracking

**Documentation:** [docs/app-context/purchases.md](docs/app-context/purchases.md)

### 👥 Groups & Collaboration
- Team/group creation with invite code system
- Role-based access control (Owner, Admin, Member)
- Shared coffee library for groups
- Member management (invite, promote, remove)
- Private/public group visibility settings

**Documentation:** [docs/app-context/groups.md](docs/app-context/groups.md)

### 📊 Analytics & Insights
- User consumption statistics (kg, spending, purchase count)
- Group consumption with member breakdown
- Top beans rankings by rating, purchases, spending
- Consumption timeseries for charts
- User taste profile analysis from reviews
- Dashboard summary aggregation

**Documentation:** [docs/app-context/analytics.md](docs/app-context/analytics.md)

### 🔐 User Accounts & Authentication
- Email-based authentication with JWT tokens
- User profile management
- Email verification system
- Password reset flow
- GDPR-compliant account deletion (anonymization)
- Secure token management (60-minute access, 7-day refresh)

**Documentation:** [docs/app-context/accounts.md](docs/app-context/accounts.md)

---

## 🛠 Tech Stack

### Backend
- **Django 4.2.9** - Web framework
- **Django REST Framework 3.14.0** - REST API toolkit
- **Simple JWT 5.3.1** - JWT authentication

### Database & Caching
- **MySQL** - Primary database (via mysqlclient 2.2.1)
- **Redis 5.0.1** - Caching layer
- **django-redis 5.4.0** - Django cache backend

### Task Queue
- **Celery 5.3.6** - Async task processing

### Additional Libraries
- **drf-spectacular 0.27.0** - OpenAPI schema generation
- **qrcode 7.4.2** - Payment QR code generation
- **Pillow 10.2.0** - Image processing
- **django-cors-headers 4.3.1** - CORS handling
- **fuzzywuzzy 0.18.0** - Fuzzy string matching

### Testing
- **pytest 7.4.4** - Testing framework
- **pytest-django 4.7.0** - Django pytest integration
- **factory-boy 3.3.0** - Test fixtures

---

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- MySQL database
- Redis server (optional, for caching)

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd coffee-rating
```

2. **Create virtual environment**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**
Create a `.env` file with:
```env
SECRET_KEY=your-secret-key
DEBUG=True
DATABASE_NAME=coffee_rating
DATABASE_USER=your-db-user
DATABASE_PASSWORD=your-db-password
DATABASE_HOST=localhost
DATABASE_PORT=3306
```

5. **Run migrations**
```bash
python manage.py migrate
```

6. **Create test data (optional)**
```bash
python manage.py create_sample_data --clear
```

7. **Run development server**
```bash
python manage.py runserver
```

The API will be available at `http://localhost:8000/api/`

---

## 📚 API Documentation

### Interactive Documentation
- **Swagger UI:** http://localhost:8000/api/docs/
- **OpenAPI Schema:** http://localhost:8000/api/schema/

### Full API Reference
See [docs/API.md](docs/API.md) for complete endpoint documentation including:
- Authentication & authorization
- Request/response formats
- Query parameters & filtering
- Error handling
- Pagination
- All available endpoints

### Test Accounts
For development/testing (after running `create_sample_data`):

| Email | Password | Role |
|-------|----------|------|
| admin@example.com | admin123 | Superuser |
| alice@example.com | password123 | Regular user |
| bob@example.com | password123 | Regular user |
| charlie@example.com | password123 | Regular user |

---

## 📁 Project Structure

```
coffee-rating/
├── apps/
│   ├── accounts/          # User authentication & profiles
│   ├── analytics/         # Statistics & insights
│   ├── beans/            # Coffee bean catalog
│   ├── groups/           # Team collaboration
│   ├── purchases/        # Purchase tracking & splitting
│   └── reviews/          # Reviews & personal library
├── config/               # Django settings
├── docs/
│   ├── API.md           # Complete API documentation
│   └── app-context/     # App-specific documentation
│       ├── accounts.md
│       ├── analytics.md
│       ├── beans.md
│       ├── groups.md
│       ├── purchases.md
│       └── reviews.md
├── manage.py
├── requirements.txt
└── README.md
```

---

## 🧪 Testing

### Run Tests
```bash
# Run all tests
pytest

# Run tests for specific app
pytest apps/beans/tests/

# Run with coverage
pytest --cov=apps --cov-report=html
```

### Test Coverage
- **Beans App:** 30+ test cases
- **Reviews App:** 50+ test cases
- **Purchases App:** 80+ test cases
- **Groups App:** 40+ test cases
- **Analytics App:** 70+ test cases
- **Accounts App:** 38+ test cases

---

## 🔑 Key Design Decisions

### Haléř-Precise Payment Splitting
Purchases use integer haléř (1/100 CZK) arithmetic to ensure split amounts always sum exactly to the total, preventing rounding errors in group payments.

### Soft Delete for Beans
Coffee beans use soft delete (`is_active=False`) to preserve historical data for reviews, purchases, and analytics.

### GDPR-Compliant Account Deletion
Account deletion anonymizes user data instead of hard deleting, preserving data integrity while removing personal information.

### One Review Per Bean
Users can only create one review per bean but can update it anytime, maintaining rating integrity and encouraging thoughtful reviews.

### Aggregate Rating Auto-Update
Bean ratings are automatically recalculated using `transaction.on_commit()` after review changes to ensure consistency.

---

## 🌍 Currency & Localization

**Current Support:** Czech Crown (CZK)
**Region:** Czech Republic

The application is designed with internationalization in mind but currently focuses on the Czech market with:
- CZK currency for all financial transactions
- SPD QR code format for Czech banking
- Haléř (1/100 CZK) precision for payment splitting

---

## 📄 License

[Add your license information here]

---

## 🤝 Contributing

[Add contribution guidelines here]

---

## 📞 Contact

**Owner:** Filip Prudek
**Last Updated:** 2025-12-14

---

## 🔗 Related Documentation

- [API Documentation](docs/API.md) - Complete API reference
- [Accounts App](docs/app-context/accounts.md) - User authentication
- [Analytics App](docs/app-context/analytics.md) - Statistics & insights
- [Beans App](docs/app-context/beans.md) - Coffee catalog
- [Groups App](docs/app-context/groups.md) - Team collaboration
- [Purchases App](docs/app-context/purchases.md) - Purchase tracking
- [Reviews App](docs/app-context/reviews.md) - Reviews & library

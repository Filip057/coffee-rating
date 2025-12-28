# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Coffee Rating is a Django REST API for tracking coffee purchases, reviews, and group consumption. Built with Django 4.2, Django REST Framework, and MySQL.

## Common Commands

```bash
# Run development server
python manage.py runserver

# Run all tests
pytest

# Run tests for specific app
pytest apps/beans/tests/
pytest apps/reviews/tests/

# Run single test file or function
pytest apps/beans/tests/test_views.py
pytest apps/beans/tests/test_views.py::test_function_name

# Run migrations
python manage.py migrate

# Create sample data for development
python manage.py create_sample_data --clear

# Generate OpenAPI schema
python manage.py spectacular --file schema.yaml
```

## Architecture

The project follows a layered architecture with strict separation of concerns:

```
Views (HTTP layer) → Services (business logic) → Models (domain) → Database
```

### App Structure

Each app in `apps/` follows this pattern:
- `views.py` - Thin HTTP handlers, delegate to services
- `services/` - Business logic as pure functions with `@transaction.atomic`
- `models.py` - Domain entities with state validation methods
- `serializers.py` - Input validation and output formatting only
- `urls.py` - Route definitions
- `tests/` - Test directory with `conftest.py` for fixtures

### Django Apps

- **accounts** - User authentication (JWT), profiles, email verification
- **beans** - Coffee bean catalog with variants, deduplication, soft delete
- **reviews** - Ratings (1-5 stars), taste profiles, one review per user per bean
- **groups** - Team collaboration, role-based access (Owner/Admin/Member), invite codes
- **purchases** - Purchase tracking, haléř-precise payment splitting, SPD QR codes
- **analytics** - Consumption statistics, dashboards, timeseries data

### Key Patterns

- **Services**: Located in `app/services/` directory. Use pure functions, accept explicit arguments (never request objects), wrap in `transaction.atomic`, raise domain exceptions
- **Soft Delete**: Beans use `is_active=False` instead of hard delete
- **Payment Precision**: All money uses integer haléř (1/100 CZK) to prevent rounding errors
- **Aggregate Ratings**: Auto-recalculated via `transaction.on_commit()` after review changes

## Testing

- Uses pytest with `--reuse-db` and `--nomigrations` for speed
- Tests use SQLite instead of MySQL (configured in settings.py)
- Factory Boy for test fixtures
- Each app has its own `tests/conftest.py` with shared fixtures

## API Endpoints

Base URL: `/api/`

- `/api/auth/` - Authentication (login, register, token refresh)
- `/api/beans/` - Coffee bean CRUD
- `/api/reviews/` - Review management
- `/api/groups/` - Group collaboration
- `/api/purchases/` - Purchase tracking
- `/api/analytics/` - Statistics and insights
- `/api/docs/` - Swagger UI documentation
- `/api/schema/` - OpenAPI schema

## Frontend

Simple HTML/JS frontend in `frontend/` directory. Served as static files via Django.

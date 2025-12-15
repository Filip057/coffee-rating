# Django App Context Documentation Structure

## **📁 Recommended File Structure**

```
coffee-rating/
├── docs/
│   ├── app-context/                    # ← New folder for app contexts
│   │   ├── README.md                   # Index of all apps
│   │   ├── accounts.md                 # Users & Auth
│   │   ├── beans.md                    # Coffee Beans
│   │   ├── reviews.md                  # Reviews & Library
│   │   ├── groups.md                   # Teams/Groups
│   │   ├── purchases.md                # Purchases & Splits
│   │   ├── analytics.md                # Analytics & Stats
│   │   └── relationships.md            # How apps interact
│   │
│   ├── API.md                          # API reference
│   ├── WORKFLOWS.md                    # User workflows
│   └── DEVELOPMENT.md                  # Dev guide
│
├── apps/
│   ├── accounts/
│   │   ├── CONTEXT.md                  # ← Quick reference in app
│   │   ├── models.py
│   │   ├── views.py
│   │   └── ...
│   ├── beans/
│   │   ├── CONTEXT.md
│   │   └── ...
│
└── README.md
```
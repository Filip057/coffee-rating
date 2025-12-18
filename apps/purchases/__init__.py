"""
Purchases App - Coffee Purchase Management

This app manages coffee purchase records, payment splitting for group purchases,
and payment tracking with QR code generation for Czech banking (SPD format).

Version: 1.0.0-rc (Release Candidate)
Status: Ready for Refactoring → Production
DRF Best Practices Score: 75/100 (B+) → Target: 95/100 (A)

Key Features:
- Group purchase creation with haléř-precise payment splitting
- Personal purchase tracking
- Payment share management
- Czech SPD QR code generation for bank payments
- Automatic payment reconciliation
- Outstanding payment tracking

Architecture:
- Models: PurchaseRecord, PaymentShare, BankTransaction
- Services: PurchaseSplitService, SPDPaymentGenerator
- Views: RESTful API with ViewSets
- Permissions: Custom permission classes (Phase 3)
- Exceptions: Domain exception hierarchy (Phase 1)

Refactoring Status:
- Phase 1: Domain Exceptions - ✓ Completed
- Phase 2: Input Serializers - ✓ Completed
- Phase 3: Custom Permissions - ✓ Completed
- Phase 4: Service Enhancement - ✓ Completed
- Phase 5: Refactor Views - ✓ Completed
- Phase 6: Test Suite - In Progress
- Phase 7: Documentation - Pending

See: docs/PURCHASES_APP_ANALYSIS.md for detailed analysis
See: docs/REFACTORING_PURCHASES_CHECKLIST.md for refactoring plan
"""

__version__ = '1.0.0-rc'
__status__ = 'Release Candidate - Refactoring In Progress'

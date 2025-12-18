"""
Purchases App - Coffee Purchase Management

This app manages coffee purchase records, payment splitting for group purchases,
and payment tracking with QR code generation for Czech banking (SPD format).

Version: 1.0.0-rc (Release Candidate)
Status: Ready for Refactoring ’ Production
DRF Best Practices Score: 75/100 (B+) ’ Target: 95/100 (A)

Key Features:
- Group purchase creation with haléY-precise payment splitting
- Personal purchase tracking
- Payment share management
- Czech SPD QR code generation for bank payments
- Automatic payment reconciliation
- Outstanding payment tracking

Architecture:
- Models: PurchaseRecord, PaymentShare, BankTransaction
- Services: PurchaseSplitService, SPDPaymentGenerator
- Views: RESTful API with ViewSets
- Permissions: To be added (Phase 3)
- Exceptions: To be added (Phase 1)

Refactoring Status:
- Phase 1: Domain Exceptions - ó Pending
- Phase 2: Input Serializers - ó Pending
- Phase 3: Custom Permissions - ó Pending
- Phase 4: Service Enhancement - ó Pending
- Phase 5: Refactor Views - ó Pending
- Phase 6: Test Suite - ó Pending
- Phase 7: Documentation - ó Pending

See: docs/PURCHASES_APP_ANALYSIS.md for detailed analysis
See: docs/REFACTORING_PURCHASES_CHECKLIST.md for refactoring plan
"""

__version__ = '1.0.0-rc'
__status__ = 'Release Candidate - Pending Refactoring'

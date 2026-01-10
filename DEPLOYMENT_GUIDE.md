# Purchase Refactor Deployment Guide

## Summary of Changes

The purchase system has been completely refactored from a single `PurchaseRecord` model into two separate models:

- **PersonalPurchase** - Simple personal coffee purchase tracking (no payment splitting)
- **GroupPurchase** - Group purchases with payment splitting and auto-paid buyer shares

### Key Changes:
- ✅ Split `PurchaseRecord` into `PersonalPurchase` and `GroupPurchase`
- ✅ Updated API endpoints: `/api/purchases/personal/` and `/api/purchases/group/`
- ✅ Updated frontend to use new endpoints
- ✅ Fixed purchase creation form
- ✅ Fixed group detail page purchase display
- ✅ Buyer's share auto-marked as PAID on group purchase creation

## ⚠️ Important: Data Loss Expected

All existing purchase data will be lost when migrations run. This is acceptable since it's test data.

## Deployment Steps

### 1. Push Changes to Render

```bash
cd /home/user/coffee-rating
git push -u origin claude/github-workflow-guide-ieUiF
```

### 2. Database Migration (REQUIRED)

Once deployed on Render, you MUST run migrations:

```bash
# On Render, run these commands in the Shell:
python manage.py makemigrations purchases
python manage.py migrate
```

**Expected behavior:**
- Old `purchase_records` table will be dropped
- New `personal_purchases` table will be created
- New `group_purchases` table will be created
- `payment_shares` table will be updated to reference `group_purchases`

### 3. Verify App Startup

Check Render logs to ensure:
- ✅ No import errors
- ✅ Migrations completed successfully
- ✅ App started without errors

## Testing Checklist

After deployment and migration:

### Personal Purchase Testing
- [ ] Create a personal purchase from `/purchase-create/`
- [ ] Verify it appears in purchase list
- [ ] Check purchase details display correctly
- [ ] Test editing a personal purchase
- [ ] Test deleting a personal purchase

### Group Purchase Testing
- [ ] Create a group purchase from group detail page
- [ ] Verify buyer's share is automatically marked as PAID
- [ ] Check payment shares are created for all members
- [ ] Verify purchase appears in group's purchase list
- [ ] Test payment share status display
- [ ] Test marking other members' shares as paid

### UI Testing
- [ ] `/purchases/` - Purchase list displays both personal and group purchases
- [ ] `/purchase-create/` - Form works for both personal and group types
- [ ] `/groups/{id}/` - Group detail page shows group purchases only

## API Endpoint Changes

### Old (Removed)
```
GET  /api/purchases/              # Listed all purchases
POST /api/purchases/              # Created purchases
```

### New
```
GET  /api/purchases/personal/     # List personal purchases
POST /api/purchases/personal/     # Create personal purchase

GET  /api/purchases/group/        # List group purchases
POST /api/purchases/group/        # Create group purchase
GET  /api/purchases/group/{id}/shares/     # Get payment shares
POST /api/purchases/group/{id}/mark_paid/  # Mark share as paid
```

## Rollback Plan

If issues occur, you can rollback by:
1. Reverting to the previous commit
2. Re-running migrations from that state

**Previous working commit:** (check git log before refactor)

## Files Changed

### Backend
- `apps/purchases/models.py` - Complete rewrite with two models
- `apps/purchases/serializers.py` - New serializers for both models
- `apps/purchases/views.py` - Separate viewsets
- `apps/purchases/urls.py` - Updated routing

### Frontend
- `frontend/js/config.js` - New endpoint structure
- `frontend/js/api.js` - New API methods
- `frontend/purchases.html` - Fetch from both endpoints
- `frontend/purchase_create.html` - Route to correct endpoint
- `frontend/group_detail.html` - Use group purchase endpoint

## Support

If you encounter issues:
1. Check Render deployment logs
2. Verify migrations ran successfully
3. Test API endpoints directly with curl/Postman
4. Check browser console for frontend errors

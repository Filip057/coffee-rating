# User Workflows - Coffee Rating App

> **Purpose:** Define what users CAN and CANNOT do from their perspective, independent of current technical implementation. This drives feature development, not the other way around.

---

## 1. Getting Started

### 1.1 Creating an Account

**What users want to do:**
- Sign up with email and password
- Choose a display name/nickname
- Start using the app immediately

**User expectations:**
- Email must be unique (no duplicate accounts)
- Display name should be unique (or allow duplicates?)
- Password should be secure (minimum requirements?)
- **DECISION NEEDED:** Email verification required before using app, or optional?
  - If required: User waits for verification email, clicks link, then can login
  - If optional: User can use app immediately, but some features locked until verified?

**What if:**
- User typos their email during signup → Cannot verify, account stuck?
- User never verifies email → Account deleted after X days, or just limited features?
- User wants to change email later → Should this be allowed?

### 1.2 Logging In

**What users want to do:**
- Login with email + password
- Stay logged in (remember me?)
- Get clear error if credentials wrong

**User expectations:**
- Error message doesn't reveal if email exists (security)
- Account locked after X failed attempts?
- Automatic logout after inactivity period?

### 1.3 Forgot Password

**What users want to do:**
- Request password reset via email
- Receive reset link quickly
- Create new password without knowing old one

**User expectations:**
- Reset link expires after X hours (24h?)
- Can request new link if expired
- Link is single-use only
- **DECISION NEEDED:** How to handle unverified emails requesting password reset?

### 1.4 Email Verification

**What users want to do:**
- Receive verification email after signup
- Click link and get confirmed instantly
- Request new verification email if lost

**What if:**
- User deletes verification email → Can request new one?
- User changes email before verifying → Old link invalid, new email sent?
- Verification link expires → How long valid? (48h? 7 days?)

---

## 2. My Account & Profile

### 2.1 View My Profile

**What users want to see:**
- My display name
- My email address
- Email verification status
- Account creation date
- Number of reviews I've written
- Number of groups I'm in
- Number of purchases I've made
- My favorite coffee (most reviewed?)

### 2.2 Edit My Profile

**What users want to change:**
- Display name
- Email address (should this trigger re-verification?)
- Password
- **MISSING:** Profile picture/avatar?
- **MISSING:** Bio/about me section?
- **MISSING:** Preferences (default brew method, favorite roast level)?
- **MISSING:** Location/country (for local roastery recommendations)?

**What users CANNOT change:**
- Account creation date
- User ID
- Email verification status (system controlled)

### 2.3 Privacy & Preferences

**What users want to control:**
- Make my reviews public vs private by default?
- Allow other users to see my profile?
- Notification preferences:
  - Email notifications for group invites?
  - Email notifications when someone comments on my review?
  - Email notifications for payment reminders?
- **MISSING:** Can users set privacy level for individual reviews?

### 2.4 Delete My Account

**What users want:**
- Permanently delete account and data (GDPR)
- Understand what happens to their data:
  - Reviews → Deleted or anonymized?
  - Group memberships → Removed automatically?
  - Groups they own → Transferred or deleted?
  - Purchases → Keep for group records but anonymized?
  - Outstanding payments → What happens?

**What users need to know:**
- This action is irreversible
- Export data before deletion?
- **MISSING:** Can users download their data before deleting? (GDPR requirement)

---

## 3. Discovering & Managing Coffee Beans

### 3.1 Browse Coffee Catalog

**What users want to do:**
- See all available coffee beans
- Filter by:
  - Roastery/brand
  - Origin country/region
  - Roast level (light, medium, dark)
  - Processing method (washed, natural, honey)
  - Recommended brew method (espresso, filter, french press)
  - Price range
  - **MISSING:** Average rating (1-5 stars)?
  - **MISSING:** "In stock" vs "discontinued"?
- Sort by:
  - Newest first
  - Highest rated
  - Most reviewed
  - Alphabetically
  - Price (low to high, high to low)

**User expectations:**
- Clear photos of each coffee
- See average rating at a glance
- See number of reviews
- See price per 250g (normalized for comparison)

### 3.2 View Coffee Details

**What users want to see:**
- Coffee name and roastery
- Origin (country, region, farm?)
- Processing method
- Roast profile and date
- Flavor notes/tasting notes
- Recommended brew method
- All available package sizes and prices
- Average rating (overall)
- All user reviews (with filtering)
- **MISSING:** Altitude/elevation?
- **MISSING:** Variety/cultivar (Arabica, Robusta, specific varietals)?
- **MISSING:** Certifications (organic, fair trade, etc.)?

### 3.3 Add New Coffee Bean

**What users want to do:**
- Add coffee if not in database
- Fill in details:
  - Name (required)
  - Roastery (required)
  - Origin country/region
  - Processing method
  - Roast level
  - Brew method recommendation
  - Description
  - Tasting notes
- Add package sizes/prices

**User expectations:**
- System checks for duplicates before creating
- **DECISION NEEDED:** Should any user add beans, or only verified users?
- **DECISION NEEDED:** Should new beans be moderated/approved first?
- **MISSING:** Can users upload photos?
- **MISSING:** Can users suggest edits to existing beans?

### 3.4 Suggest Coffee Edits

**What if coffee info is wrong?**
- User wants to correct roastery name
- User wants to add missing origin info
- User wants to update price
- **DECISION NEEDED:** Direct edit (wiki style) or suggest edits for approval?
- **DECISION NEEDED:** Who can approve edits?

---

## 4. Reviews & Ratings

### 4.1 Write a Review

**What users want to do:**
- Rate coffee 1-5 stars (overall)
- Rate specific aspects (optional):
  - Aroma (1-5)
  - Flavor (1-5)
  - Acidity (1-5)
  - Body (1-5)
  - Aftertaste (1-5)
- Add written notes/review
- Select taste tags (fruity, chocolatey, nutty, floral, etc.)
- Specify brew method used
- Indicate "would buy again" (yes/no/maybe?)
- **MISSING:** Upload photos of the coffee/packaging?
- **MISSING:** Rate the value for money separately?

**User expectations:**
- One review per coffee per user (can update later)
- Review shows up in coffee's review list
- Review appears in "my library" automatically
- Review affects coffee's average rating

**Context options:**
- Personal review (just for me)
- Group review (shared with my coffee club)
- Public review (anyone can see)
- **DECISION NEEDED:** Can user change context later?

### 4.2 View My Reviews

**What users want to see:**
- All my reviews (list view)
- Filter by:
  - Star rating (show only 5-star reviews)
  - Brew method
  - Date range
  - Roastery
  - **MISSING:** Origin/country?
- Sort by:
  - Most recent
  - Highest rated
  - Lowest rated
  - Alphabetically

### 4.3 Edit My Review

**What users want to change:**
- Star rating (overall and detailed)
- Written notes
- Taste tags
- Brew method
- "Would buy again" answer
- **DECISION NEEDED:** Show edit history to other users?

**What users CANNOT change:**
- Which coffee the review is for
- Review date (original)
- Review author
- **QUESTION:** Can user change review context (personal → group)?

### 4.4 Delete My Review

**What users want:**
- Remove review completely
- Coffee's average rating recalculated

**What if:**
- Review is part of group context → Does it disappear for group members?
- User has purchased this coffee in group context → Review deletion affects purchase history?

### 4.5 My Coffee Library

**What users want to see:**
- All coffees I've reviewed or saved
- Mark favorites/pins to top
- Add notes to library entries (separate from review?)
- Track:
  - When I first tried it
  - How many times I've bought it
  - Last purchase date
  - **MISSING:** Would I buy again tracking?

**Library entry actions:**
- Add coffee without reviewing (bookmark)
- Pin to top of library
- Add personal notes
- Mark as "want to try"
- **MISSING:** Mark as "discontinued" or "no longer available"?

---

## 5. Groups & Team Coffee Sharing

### 5.1 Create a Group

**What users want to do:**
- Create coffee club/team
- Give it a name and description
- Choose privacy level:
  - Private (invite only) ← default
  - Public (anyone can find and request to join)
  - **MISSING:** Hidden (invite only + not searchable)?
- **MISSING:** Set group avatar/photo?
- **MISSING:** Set group location/meeting place?

**User becomes:**
- Group owner (highest permission level)
- Automatically added as member

### 5.2 Invite Members

**What users want to do:**
- Share invite code with friends
- **MISSING:** Share invite link (auto-fills code)?
- **MISSING:** Direct invite via email?
- **MISSING:** Set invite code expiration?
- **MISSING:** Limit number of uses per invite code?

**Member joins by:**
- Entering invite code
- Automatically added as regular member

### 5.3 Group Roles

**Role hierarchy:**
1. **Owner** (one person)
   - Can delete group
   - Can transfer ownership
   - Can promote/demote admins
   - Can remove any member
   - Can regenerate invite code
   - Can edit group details
   - Can manage group library

2. **Admin** (multiple allowed)
   - Can remove members (except owner)
   - Can promote members to admin
   - Can demote other admins
   - Can regenerate invite code
   - Can edit group details
   - Can manage group library
   - **MISSING:** Can admin see all member payments/debts?

3. **Member** (regular user)
   - Can view group details
   - Can view group library
   - Can add coffees to group library
   - Can write group reviews
   - Can record group purchases
   - Can view group expenses
   - Can leave group anytime

**What if:**
- Owner wants to leave → Must transfer ownership or delete group
- All admins leave → Owner remains as admin
- Last member leaves → Group auto-deleted? Or owner remains?

### 5.4 Group Library

**What users want:**
- Shared collection of coffees the group has tried/owns
- Any member can add coffee to library
- See who added each coffee
- See all group reviews for each coffee
- Pin favorite coffees to top (admin only?)
- Add group notes to each coffee
- **MISSING:** Track group's total purchases of each coffee?
- **MISSING:** Mark coffee as "currently in stock" at group meeting place?

**Group library actions:**
- Add coffee (any member)
- Remove coffee (who can do this? admin only?)
- Pin/unpin (admin only?)
- Add/edit notes (any member or admin only?)

### 5.5 Group Reviews

**What users want:**
- Write review in group context
- Group members see this review
- Review appears in coffee's average rating
- **QUESTION:** Can non-members see group reviews? (privacy)
- **MISSING:** Can group have collaborative reviews? (multiple people rate same purchase)

### 5.6 Leave Group

**What users want:**
- Leave group cleanly
- **DECISION NEEDED:** What happens to my group reviews?
  - Deleted?
  - Stay but anonymized?
  - Stay with my name?
- **DECISION NEEDED:** What happens to my unpaid purchase shares?
  - Must settle before leaving?
  - Remain as debt?
  - Forgiven?

**Owner CANNOT leave without:**
- Transferring ownership to another member, OR
- Deleting the entire group

### 5.7 Manage Members

**Owner/Admin can:**
- View all members and roles
- Promote member to admin
- Demote admin to member
- Remove member from group
- See member join date
- **MISSING:** See member activity (reviews written, purchases made)?
- **MISSING:** See member payment history (paid vs owed)?

**Owner can:**
- Transfer ownership to another member
- Delete group entirely

### 5.8 Delete Group

**What happens:**
- Group is permanently deleted
- All memberships removed
- Group library deleted
- **DECISION NEEDED:** What happens to group reviews?
  - Deleted?
  - Converted to personal reviews?
  - Keep but mark group as [deleted]?
- **DECISION NEEDED:** What happens to group purchases?
  - Deleted?
  - Preserved for payment reconciliation?
- **DECISION NEEDED:** Outstanding debts → How are they handled?

---

## 6. Purchases & Expense Splitting

### 6.1 Record Personal Purchase

**What users want to do:**
- Record that I bought coffee
- Enter:
  - Which coffee
  - Package size
  - Price paid
  - Where bought
  - Date of purchase
  - Notes
- **MISSING:** Upload receipt photo?
- **MISSING:** Track if purchase is for future review?

**User expectations:**
- Purchase shows in my history
- **MISSING:** Purchase auto-adds coffee to my library?
- **MISSING:** Reminder to review if not reviewed yet?

### 6.2 Record Group Purchase

**What users want to do:**
- Buy coffee for the group
- Split cost among members
- System calculates each person's share

**How it works:**
- I record purchase (who, what, how much)
- Choose split method:
  - Equal split among all members
  - Equal split among selected members
  - Custom amounts per person
  - Exclude certain members
- System creates payment shares for each person
- Each person sees their amount owed
- I get notifications as people pay

**User expectations:**
- I paid X, others owe me Y
- Clear tracking of who paid, who hasn't
- **MISSING:** Payment deadline/reminder?
- **MISSING:** Interest on late payments?
- **MISSING:** Partial payments allowed?

### 6.3 View My Payment Shares

**What users want to see:**
- All group purchases where I owe money
- Amount I owe per purchase
- Who I owe (the purchaser)
- Purchase details (coffee, date, price)
- Payment status (unpaid, paid, overdue?)
- Total debt across all groups
- **MISSING:** Payment history (what I've paid)?

**Filter/sort by:**
- Group
- Status (unpaid/paid)
- Date
- Amount
- **MISSING:** Overdue payments first?

### 6.4 Pay My Share

**What users want to do:**
- Mark payment share as paid
- **MISSING:** Add payment proof (transaction ID, screenshot)?
- **MISSING:** Add payment date?

**Payment methods:**
- **CZECHIA SPECIFIC:** Generate SPD QR code for bank transfer
  - QR contains: account number, amount, payment reference
  - User scans with banking app
  - Automatic payment
- Manual payment outside app (Venmo, cash, etc.)
  - User marks as paid
  - Purchaser confirms? Or auto-marked?

**User expectations:**
- QR code includes unique payment reference
- Purchaser gets notification when I mark as paid
- **DECISION NEEDED:** Require purchaser confirmation or auto-accept?

### 6.5 Track Who Owes Me

**What users want to see:**
- All group purchases I made
- Who owes me money (list of debtors)
- Amount owed per person
- Total owed to me across all purchases
- Payment status of each share
- **MISSING:** Payment reminders I've sent?

**Actions:**
- Send payment reminder (email/notification)
- Mark share as paid (when received)
- Forgive debt (write off)
- **MISSING:** Mark as disputed?
- **MISSING:** Request proof of payment?

### 6.6 Confirm Received Payment

**What users want to do:**
- See when someone marks share as paid
- Verify payment received in my bank
- Confirm the payment
- **DECISION NEEDED:** Required or optional confirmation?

**What if:**
- User marks as paid but I never receive it?
- User pays wrong amount?
- Payment is late?

### 6.7 Group Financial Summary

**What users want to see:**
- Total spent by group on coffee
- Total spent this month/year
- Who buys most often
- Average purchase amount
- Who owes the most currently
- Who has paid most reliably
- **MISSING:** Export financial report?
- **MISSING:** Split by coffee type/roastery?

---

## 7. Analytics & Insights

### 7.1 My Coffee Statistics

**What users want to see:**
- Total coffees reviewed: X
- Average rating I give: Y stars
- Favorite roastery (most reviews)
- Favorite origin country
- Favorite brew method
- Most used taste tags
- **MISSING:** Total money spent on coffee?
- **MISSING:** Coffees per month trend?
- **MISSING:** Price per cup analysis?

### 7.2 My Taste Profile

**What users want to discover:**
- Do I prefer light or dark roast?
- Do I prefer washed or natural process?
- Which origins do I rate highest?
- Flavor preferences (fruity vs chocolatey)
- **MISSING:** Recommendations based on taste profile?
- **MISSING:** Similar users who like same coffees?

### 7.3 Group Analytics

**What users want to see:**
- Group's total coffees tried: X
- Group's favorite coffee (highest average)
- Most purchased coffee
- Total spent on coffee (all purchases)
- Member who reviews most
- Member who buys most
- **MISSING:** Group taste profile (aggregate)?
- **MISSING:** Comparison to my personal taste?

### 7.4 Global Coffee Trends

**What users want to see:**
- Most popular coffee overall
- Highest rated roastery
- Trending coffees (recently popular)
- Top reviewed beans this month
- **MISSING:** Regional trends (popular in my country)?
- **MISSING:** Compare my taste to global average?

---

## 8. Social Features (Missing?)

### 8.1 User Profiles (Public?)

**What might users want:**
- View other users' profiles
- See their public reviews
- See their favorite coffees
- **MISSING:** Follow other users?
- **MISSING:** See user's taste profile?
- **MISSING:** Message other users?

**Privacy concerns:**
- Can users hide their profile?
- Can users block other users?
- What's visible to non-friends vs friends?

### 8.2 Comments on Reviews (Missing?)

**What might users want:**
- Comment on other reviews
- Ask questions about brew method
- Agree/disagree with review
- Like/upvote reviews
- **DECISION NEEDED:** Allow comments? Opens moderation issues

### 8.3 Coffee Recommendations (Missing?)

**What might users want:**
- "Users who liked X also liked Y"
- "Based on your taste profile, try Z"
- "Your friend just reviewed this coffee"
- **MISSING:** Recommendation algorithm?

---

## 9. Notifications

### 9.1 What Users Should Be Notified About

**Account:**
- Email verification link
- Password reset link
- Account deletion confirmation

**Groups:**
- Invited to join group
- Removed from group
- Promoted to admin
- Group deleted
- New member joined (admin only?)

**Purchases:**
- Someone paid their share (to purchaser)
- Payment reminder (to debtor)
- New group purchase created
- Payment marked as disputed
- **MISSING:** Payment overdue?

**Reviews:**
- Someone reviewed a coffee I want to try
- New review in my group
- **MISSING:** Someone commented on my review?

**Coffee Beans:**
- Coffee I favorited got new reviews
- Coffee price changed
- **MISSING:** Coffee back in stock?

### 9.2 Notification Channels

- In-app notifications (bell icon)
- Email notifications (optional)
- **MISSING:** Push notifications (mobile app)?
- **MISSING:** SMS for payment reminders?

---

## 10. Search & Discovery

### 10.1 Global Search

**What users want to search:**
- Coffee beans by name
- Roasteries
- Users (if profiles are public?)
- Groups (if searchable?)
- Reviews by content
- **MISSING:** Search by taste tags?

### 10.2 Advanced Filters

**Coffee search filters:**
- Multiple origins (OR logic)
- Price range
- Rating range (4+ stars only)
- Has reviews (yes/no)
- Available package sizes
- **MISSING:** In my library (yes/no)?
- **MISSING:** In my group library?

---

## 11. Edge Cases & Special Scenarios

### 11.1 What if coffee bean is discontinued?

- User can still view it
- User can still review it (if they have old stock)
- Mark as "no longer available"?
- Hide from main browse?

### 11.2 What if roastery closes?

- Keep coffee records for history
- Mark roastery as closed
- Users' reviews remain intact

### 11.3 What if user has outstanding debts but wants to leave group?

**Options:**
1. Cannot leave until paid
2. Can leave but debt remains tracked
3. Debt is forgiven
4. Debt transfers to another member?
**DECISION NEEDED:** Which approach?

### 11.4 What if group owner account is deleted?

**Options:**
1. Group is auto-deleted
2. Ownership transfers to oldest admin
3. Ownership transfers to most active member
**DECISION NEEDED:** Which approach?

### 11.5 What if someone creates duplicate coffee beans?

- System checks for similar names before creating
- Admin moderation queue?
- Community flagging system?
- Merge duplicates functionality?
**DECISION NEEDED:** Prevention vs cleanup?

---

## 12. Mobile App Considerations (Future)

**What mobile users might need differently:**
- Scan coffee bag barcode to find/add coffee
- Take photo of coffee while reviewing
- Quick access to group library while shopping
- Offline access to my reviews
- Push notifications for payments
- Camera for receipt scanning
- QR code scanner for payment codes

---

## SUMMARY: Key Decisions Needed

1. **Email Verification:** Required or optional? What restrictions if unverified?
2. **Bean Creation:** Any user or moderation needed? Direct edit or suggest edits?
3. **Review Context:** Can users change personal→group after creation?
4. **Review Deletion:** What happens to group reviews when user leaves?
5. **Group Deletion:** What happens to reviews, purchases, debts?
6. **Payment Confirmation:** Required from purchaser or auto-accept?
7. **Outstanding Debts:** Can user leave group with unpaid debts?
8. **Owner Deletion:** What happens to owned groups?
9. **Duplicate Detection:** How strict? Auto-merge or manual review?
10. **Social Features:** User profiles public? Comments? Follow system?
11. **Privacy Defaults:** Reviews public or private by default?
12. **Data Export:** GDPR requirement - users can download their data?

---

## SUMMARY: Missing Features (Potentially)

### High Priority Gaps:
1. ✗ Edit email address functionality
2. ✗ Data export before account deletion (GDPR)
3. ✗ Transfer group ownership
4. ✗ Payment confirmation workflow (or auto-accept decision)
5. ✗ Payment reminders/notifications
6. ✗ Review edit history
7. ✗ Coffee bean suggest edits system

### Medium Priority Gaps:
1. ✗ User profile pictures
2. ✗ Group avatars
3. ✗ Photo uploads (coffee, receipt)
4. ✗ Recommendation engine
5. ✗ Advanced search filters
6. ✗ Mark coffee as discontinued
7. ✗ Payment dispute resolution
8. ✗ Partial payment tracking

### Low Priority / Nice-to-Have:
1. ✗ Social features (follow, comments)
2. ✗ Public user profiles
3. ✗ Taste profile algorithm
4. ✗ Community features
5. ✗ SMS notifications
6. ✗ Barcode scanning
7. ✗ Invite link expiration
8. ✗ Group meeting location

---

## Next Steps

1. **Review this document** - Does this match your vision for user experience?
2. **Make decisions** - Answer the key decision questions above
3. **Prioritize gaps** - Which missing features are must-haves vs nice-to-haves?
4. **Map to technical** - For each user action, identify needed API endpoints, services, models
5. **Identify technical gaps** - Where does current implementation not support these workflows?

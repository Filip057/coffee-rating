# User Workflows in app Coffee rating
Here is description of what can and cannot user do in app from his perpective. 
I will try to catch all scenarios and cover them with API endpoints. 

## User login / sing up ##

This will be offered from landing page. 
User can log in or create new account. 

### Login
check if: 
- is it valid email? (frontend?)
- email and password match, if not give back message email or passw incorrect
- who handles validations? 
- what happens when it is correct? 

- option for forgotten password
- what is the architecture behind creating new password? sending email with link for page for creating new pass? sending email with new password?

### Sing up 
- email - check if account already exist, if its valid email, 
- password, password again, do we give any restriction what password has to contain?
- username(nickname) unique, check if its free 
- after creation - email verification, who sends the link, where it is stored? field validated? who checks if email is validated
- but do we need even email validation?
- what app does if email is not validated?

## Main page
- After login there will be main page, crossroad to differen actions  
Main page is about frontend, it will use just proper api endpoint    

### Here is list of possible actions what user could do.  
**Options**
- delete user
- what othe feature?

**Beans**
- list all beans and possible all sort of filters 
- list of roasteries and their beans
- detail paige about beans and its reviews
- adding reviews, my reviews, updating reviews (allow?)

**Groups**
- create group
- join existing group via invite code
- leave group (what happens with history of reviews, and data consumption and shared expenses?)
- add beans package to group
- add review to shared bean package 
- create shared expenses
- who can see details about group - only members

**Roasteries**
- adding roastery
- list of all 


**Analytics**  
This must be design yet 

**Purchases**
App for splitting expenses among members of some group  
If user has bank account, it can generate qr code  
Track users debt, who own who and how much, mark paid debts  


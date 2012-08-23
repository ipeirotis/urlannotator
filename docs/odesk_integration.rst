======================
oDesk integration plan
======================
This document is only for used as reference for Work In Progress feature.
As such, it can change often both in form and content.
Issues listed at the end of each section summarise mentioned section and as such
can, and mostly will, appear multiple times.

Where oDesk integration is needed?
==================================
1. oDesk worker data.
2. oDesk contract management
    2.1. Job creation
    2.2. Active worker applications query
    2.3. Worker application approval/decline
    2.4. Worker contract end


1. oDesk worker data
   =================

Decision has been made that we won't store oDesk worker's first and last name
in the application in favor of making API query to oDesk itself.

Issues:
- oDesk allows to query their user only by cipher text, not via uuid. As such,
  we need to retrieve it from worker application approval, if provided (see 2.2)
- oDesk doesn't allow to perform anonymous queries to their API to fetch users'
  profile info (called Provider Info)
- The application needs to have it's own oDesk account to query API for user
  profiles

2. oDesk contract management
   =========================

oDesk job workflow resembles the following:

                    Contractor posts a job (hourly/fixed price)
                                |
                                V
                    Worker applies to the job
                                |
                                |
                        --------+--------
                        |               |
                        V               V
                    We approve      We decline
                        |
                        V
    Worker has to be notified as where to post his results
    (by default a message with Tagasauris job is sent)
                        |
                        V
        Worker submits an URL at Tagasauris.
            We are notified of that.
                        |
                        V
                Worker is awarded money.
            Our contract with him is finished.

2.1 Job creation
    ============

To be able to gather as much data as possible from users making an application
to job posted, we need to manage jobs ourselves.

Possible solution:
- API call to Hiring > Jobs HR API > post a Job, storing job reference from
  the return value inside DB

Job is posted as a fixed price job, with parameters given at job wizard at our
page.

Issues:
- The application needs very own oDesk contractor credentials to make API calls
  from
- oDesk API Python bindings are missing Post a Job functionality

2.2 Active worker applications query
    ================================

We need to continously check open jobs for pending applications. Intially we will
accept all applications unless worker is on job creators' block list.

Possible solutions:
- Recurring Celerybeat schedule task
- Worker applications most likely provided from Hiring > Jobs HR API > get a Specific
  Job (most likely, example resource is restricted)

Issues:
- We need a contractor account on oDesk we can use to make queries from
- Uncertain content of Hiring > Jobs HR API > get a Specific Job API call

2.3 Worker application approval/decline
    ===================================

After receiving worker's application for a job, we are either accepting it or
declining depending if the job's creator is blocking the user or not.

Possible solutions:
- API call after determining the outcome of the application (approval/decline)
- Using `requests`, or other library, imitate real user's application approval
  or decline

Issues:
- Missing API calls
- Python bindings to the above
- If we are using libraries like `requests`, we have to be prepared for all kinds
  of 'Out of Service' messages, changes in page layout, etc.

2.4. Worker contract end
     ===================

After worker has done job, Tagasauris has collected the URLs, we are ready to
reward the worker. There are two possible ways to do that:

- Ending fixed price contract results in immediate payment
- Bulk payment of all jobs done by the worker throughout set period of time
    - API call
    - Closing contracts without payment on all but last, which gives a bonus
      equal to the total value of the previous jobs

oDesk supports funding from PayPal or credit card.
Certain credit cards may apply fees on transactions.

PayPal fees look as follows:
PayPal or bank account inside the US - free
Debit/Credit card inside the US - 2.9% of total amount + 0.30$ per transaction
Outside the US: 0.5% to 2% (depends on destination) using PayPal or bank account.
                3.4% to 3.9% if paying with a credit or debit card.

Issues:
- We need a contractor account on oDesk we can use to make queries from
- Missing API calls for 2nd option
- Python bindins for the above
- Fees
- Who is holding the money: we or the job creator?
- Who is sending the money: we or the job creator?
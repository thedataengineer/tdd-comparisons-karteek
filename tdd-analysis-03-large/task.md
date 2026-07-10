You are building a loyalty points engine for a retail company. Implement it 
in Python as a library (no UI, no database — in-memory state is fine) that 
exposes whatever functions/classes you think are appropriate for the rules 
below. Another engineer will import and call your code, so design the 
interface with that in mind.

DOMAIN RULES

1. Earning points
   - Customers earn points on purchases at a rate determined by their tier:
     Bronze: 1 point per $1 spent
     Silver: 1.25 points per $1 spent
     Gold: 1.5 points per $1 spent
   - Points from a purchase are awarded immediately and are rounded down to
     the nearest whole point.

2. Tiers
   - A customer's tier is determined by their total spend in the trailing
     365 days (not lifetime spend), recalculated after every purchase or
     refund:
     Bronze: $0–$999.99
     Silver: $1,000–$4,999.99
     Gold: $5,000+
   - Tier changes take effect immediately and apply to the purchase that
     triggered the change (i.e. if a purchase pushes someone from Bronze to
     Silver, that same purchase earns points at the Silver rate).

3. Expiration
   - Points expire on a rolling 90-day window from the date they were
     earned, EXCEPT points earned during the customer's signup month
     (month and year of their signup date) never expire.
   - When checking a customer's balance or attempting to spend points,
     expired points must not be counted or spendable.

4. Refunds
   - A refund on a purchase claws back the points earned from that specific
     purchase, but only up to however many of those points the customer has
     not already spent.
   - If the customer has already spent some of the points from the
     refunded purchase, claw back whatever is left of that batch; do not
     pull points from other purchases to make up the difference, and do not
     create a negative balance.
   - Refunds are matched to purchases by purchase ID. A purchase can only
     be refunded once.

5. Spending points
   - When a customer spends points, points are consumed oldest-batch-first
     (the batch from the earliest-dated purchase is drawn down before
     later batches), skipping any batch that has already fully expired.
   - Spending more points than the customer's current non-expired balance
     should be rejected (no partial spend, no negative balance).

6. Queries the system must support
   - Record a purchase (customer id, dollar amount, date) -> returns points
     earned and the customer's resulting tier.
   - Record a refund (purchase id, date) -> returns points clawed back.
   - Spend points (customer id, point amount, date) -> returns success/
     failure and remaining balance.
   - Get a customer's current spendable point balance as of a given date.
   - Get a customer's current tier as of a given date.

You may assume all dates are passed in explicitly (no need to read system
time). You may assume a customer's signup date is provided when the
customer is created.

Build this however you think is best designed. When you believe the work is 
complete, stop and report that you are done.
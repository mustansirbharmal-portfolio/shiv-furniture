# Simple explanation of the problem (like you are in 8th grade)

Imagine Shiv Furniture is a big home that needs to keep track of money for different chores and activities — buying wood, selling tables, paying workers, and checking if they are following the plan. Right now they’re messy: bills, orders and budgets aren’t linked properly, so it’s hard to know if they are spending too much or earning enough.

Below I’ll explain the whole thing in very simple words.

---

## What Shiv Furniture wants (the goal)

They want one computer system that:

* Records every purchase and sale.
* Records all payments.
* Keeps each activity’s budget separate (like one for “Marketing” and one for “Factory”).
* Shows, quickly and clearly, how much of each budget is used and how much is left.

---

## Why they have a problem now

Right now:

* They don’t know how much of a budget is already spent.
* They can’t easily see spending per activity (like “Furniture Expo 2026”).
* Different people use different lists or names for the same thing, causing confusion.
* Managers don’t get quick, reliable information to make decisions.

---

## What the system will include (simple list)

1. **Master lists** (important basic files):

   * Contacts (customers and vendors)
   * Products (tables, chairs)
   * Cost centers (called Analytical Accounts — e.g., “Production”, “Expo 2026”)
   * Budgets (money planned for a cost center)
   * Auto rules to assign costs to cost centers automatically

2. **Transactions** (things that happen with money):

   * Purchase Orders (PO): we ask a supplier to send stuff
   * Vendor Bills: bill we get from a supplier
   * Sales Orders (SO): customer ordered something
   * Customer Invoices: bill we send to customer
   * Payments: money we pay or receive

3. **Budget checking**:

   * Compare Budget vs Actual (what was planned vs what actually happened)
   * Show % achieved and how much is left
   * Show reports and charts
   * Keep track if budgets are revised (changed)

4. **Customer Portal** (what customers can do on a website):

   * View and download invoices and orders
   * Pay invoices online

---

## Who uses it

* **Admin (owner)**: can change everything, add records, see all reports.
* **Customer (portal user)**: can view/download/pay only their own invoices and orders.

---

## Important rules (in simple words)

* Only Admin can change or delete the main lists (master data).
* Every transaction (like a bill or sale) should use the items from the master lists so data stays consistent.
* Each transaction is linked to a cost center (manually or automatically).
* Budgets are set for specific time periods (e.g., Jan–Dec 2026) and attached to cost centers.
* The system automatically tallies actual spending/earning and compares it to budgets.
* Payment status of an invoice updates to Paid / Partially Paid / Not Paid automatically.

---

## Quick examples (easy numbers)

**Budget vs Actual**

* Suppose budget for “Expo 2026” = ₹10,000.
* Actual spending so far = ₹6,000.

Achievement % = (Actual ÷ Budget) × 100
Step-by-step: 6,000 ÷ 10,000 = 0.6 → 0.6 × 100 = 60% achieved.
Remaining balance = 10,000 − 6,000 = ₹4,000 left.

**Payment status**

* Invoice amount = ₹1,000.
* Payment received = ₹1,000 → Status = **Fully Paid**.
* Payment received = ₹600 → Status = **Partially Paid** (₹400 remaining).
* Payment received = ₹0 → Status = **Not Paid**.

---

## What “Analytical Accounts / Cost Centers” mean (very simple)

Think of cost centers like separate piggy banks for each activity:

* One piggy bank for “Factory”
* One for “Marketing”
* One for “Expo 2026”
  When you buy wood for a chair, you put that cost into the “Factory” piggy bank. This helps you see which activity used how much money.

---

## What “Auto-Analytical Models” mean (very simple)

These are rules that the system follows automatically. Example rule:

* “If the product category is ‘Wood’, put the cost into the ‘Production’ piggy bank.”
  So the accountant doesn’t need to pick the piggy bank every time — the system does it.

---

## What “Reconciliation” means (easy)

When you get a bank entry (showing money left your account) and there’s a matching invoice, the system connects them. That connection is called reconciliation. It proves the invoice was paid.

---

## Why this is important (short)

* Helps bosses see money clearly in real time.
* Reduces manual work and mistakes.
* Lets managers make smart decisions (e.g., stop or increase spending).
* Shows the whole business flow from purchase to accounting to reports.

---

If you want, I can now:

* Give a short, story-like example of a full flow (buy wood → make table → sell → record payment), or
* Make a tiny cheat-sheet you can print and keep. Which one would you like?

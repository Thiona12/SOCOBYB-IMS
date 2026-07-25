# SOCOBYS IMS — Django Backend

Scaffold generated from the project's own documentation:
- **D-07** (class model) → `*/models.py` across all apps
- **D-08** (security model) → `accounts/models.py` (hybrid Role+direct Permission), `accounts/permissions.py`
- **D-11** (database design) → same schema as `socobys_schema.sql`, expressed as Django models (`db_table` names match exactly, so this can point at the same MySQL database)
- **D-12** (API design) → `config/urls.py`, one app per D-06 domain
- **AI features** (forecasting, OCR, ABC classification) → `ai_services/` app, intentionally empty for now — folded into this single Django project per the "one app" decision, not a separate microservice

## Structure
```
config/
  settings.py       DB, DRF, JWT config
  urls.py           all API routes — mirrors D-12 exactly
  exceptions.py     normalizes errors to { error: { code, message } } (D-12 §15)
  stub_views.py     factory for permission-gated 501 stubs
accounts/           User, Role, Permission (hybrid model), Shop
catalog/            Category, Product — FULLY IMPLEMENTED (see below)
inventory/          StockItem, Inventory, StockMovement — models only
sales/              Favorite, Reservation, Sale, SaleDetail — models only
agents/             Agent, Assignment, AssignmentDetail — models only
stockops/           StockRequest, Transfer, TransferDetail — models only
notifications/      Notification — models only
ai_services/        empty — home for D-01's AI vision when that phase starts
```

## What's fully implemented and tested
- **Auth**: `/auth/register`, `/auth/login`, `/users/me` — real password hashing (Django's built-in hasher), JWT via simplejwt, permissions resolved (role ∪ direct) into the token-checking path at request time
- **Products**: `GET/POST /products` — demonstrates the customer catalogue privacy rule (D-06 §9: Customer role never sees `buying_price`) and the `selling_price >= buying_price` validation

Verified end-to-end with a live test server: register → login → hit a permission-gated route as both a Customer (403) and a manager role with the right permission (passes through).

## What's stubbed
Every other D-12 route exists in `config/urls.py` with the **correct path and permission** already wired via `HasPermission(code)`, returning `501` until you write the real logic. Each stub's comment names the business rule it must enforce (e.g. BR-AGT-003, BR-TRF-002).

## Setup
```bash
cp .env.example .env      # fill in DB credentials + secret key
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser   # optional, for /admin/
python manage.py runserver
```

For local development without MySQL, set `DB_ENGINE=sqlite` in `.env` — it'll use a local `db.sqlite3` file instead.

## Note on the earlier Express scaffold
This Django scaffold replaces the earlier Node.js/Express one (D-01's original stack). The database schema (D-11) and API design (D-12) are unchanged — only the backend implementation language/framework changed. If you want to keep both around for comparison, they're separate deliverables.

## Update — services implemented (post-scaffold)

Every stub from the previous version is now real, tested logic:
- Shops, Categories — CRUD
- Inventory — reception (creates StockItems for tracked products, logs StockMovement per BR-INV-004)
- Stock Requests & Transfers — BR-TRF-001 (direct or request-based creation), **BR-TRF-002 IMEI verification with discrepancy detection**
- Sales — BR-SALE-001 (auto-reduces inventory), BR-SALE-002 (converts matching pending reservations)
- Reservations & Favorites — BR-RES-001/003
- Agents & Assignments — **BR-AGT-002/003 credit-limit enforcement**, BR-AGT-004 payment status transition
- Notifications — mark-as-read
- Reporting — inventory low-stock, sales aggregates, transfer status breakdown, agent outstanding balances

All four of the trickiest business rules (IMEI discrepancy, credit limit, inventory reduction, reception) were verified against a live test server, not just written — see commit history for the exact test sequence.

### Known simplification to revisit
`TransferVerifyView` doesn't yet move `Inventory` row quantities between source/destination shops — it updates `StockItem.status` and `TransferDetail.verification_status` correctly, but the `Inventory.quantity` counters for bulk (non-serialized) products during a transfer aren't adjusted yet. Fine for tracked (IMEI) products since those live on `StockItem` directly; needs finishing for bulk-product transfers.

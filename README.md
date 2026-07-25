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
cp .env.example .env      # SQLite by default, no DB server needed
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser   # optional, for /admin/
python manage.py runserver
```

**Database: SQLite by default.** No separate database server to install or run — Django creates and manages a local `db.sqlite3` file automatically via `migrate`. This matches D-11's schema exactly (same tables, same relationships), just without needing MySQL running. If SOCOBYS later needs multi-server production deployment, set `DB_ENGINE=mysql` in `.env` and use `db/schema.sql` — but for a solo internship project, SQLite is the simpler and recommended choice.

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

### Fixed — bulk product transfers
Transfers now correctly handle bulk (non-serialized) products via `bulkItems`: source `Inventory.quantity` is decremented (reserved) at creation time, and `POST /transfers/{id}/verify` accepts `receivedBulkItems` to credit the destination `Inventory` row (created if it doesn't exist yet) with whatever quantity actually arrived. Short/over deliveries are flagged as `COMPLETED_WITH_DISCREPANCY` with the shipped-vs-received numbers returned, same pattern as IMEI mismatches.

## Update — Django templates frontend (webapp app)

A full server-rendered frontend using Django's own template engine (no React) — since Bootstrap-styled HTML + Django views is a much smaller learning curve than a separate JS frontend.

- **Auth**: `/login/`, `/register/`, `/logout/` — Django's built-in session auth (`django.contrib.auth`), reusing the exact same `User`/`Role` models as the DRF API. A user can log into either the API (JWT) or this web UI (session) with the same credentials.
- **Staff**: `/` (dashboard), `/inventory/`, `/transfers/` (+ create/verify), `/sales/` (+ create), `/agents/` (+ create/assign)
- **Customer**: `/catalogue/` (reserve/favorite buttons inline), `/my-reservations/`, `/my-favorites/`

All the same business rules apply here as in the API (BR-TRF-002 discrepancy detection, BR-AGT-003 credit limit, BR-SALE-001 inventory reduction) — verified end-to-end via simulated browser sessions (register → login → receive stock → create transfer → verify → confirm destination inventory credited; customer register → reserve → favorite → confirm on "my" pages).

### Known simplifications in the web UI (vs. the API)
- Transfer creation via the web form only supports bulk (non-IMEI) products for simplicity; IMEI-tracked transfers still need the API directly.
- Agent assignment takes stock item IDs as a comma-separated text field rather than a proper picker — fine for an internal tool, worth a nicer widget later.
- `cancel_reservation` is a GET link, not a POST button — acceptable for an internal MVP but should become a POST-only action before any real deployment.

### Running it
Same setup as before (`pip install -r requirements.txt`, migrate, `runserver`) — the web UI and API now live on the same Django project, so one server serves both.

## Update — formal test suite

43 tests across `accounts`, `catalog`, `inventory`, `stockops`, `agents`, `sales`, and `webapp` — this replaces "I ran curl by hand" with a real, repeatable suite. **86% code coverage** on the business logic.

Every business rule tested manually earlier in development is now a permanent, automated test:
- **D-08 hybrid permissions**: role-granted vs. direct-granted permissions, including the exact bug scenario that was found and fixed (a permission granted directly with no supporting role)
- **D-06 §9 catalogue privacy**: Customer role never receives `buying_price`; staff do
- **BR-TRF-002**: IMEI mismatch detection (tracked items) AND short/over-delivery detection (bulk items) — both the "everything matches" and "something's wrong" paths
- **BR-AGT-003**: credit limit rejection, including the case where *existing* outstanding devices plus a new request together exceed the limit
- **BR-SALE-001/002**: inventory reduction on sale, insufficient-stock rejection, reservation-to-sale conversion
- **BR-INV-002/004**: tracked vs. bulk reception, movement logging, identifier/quantity mismatch rejection
- Web UI: registration → correct redirect by role, anonymous access correctly blocked, the `cancel_reservation` GET-vs-POST fix specifically verified

### Running the tests
```bash
export DJANGO_SECRET_KEY=test-key DB_ENGINE=sqlite   # or your real .env
python manage.py test

# with coverage:
pip install coverage
coverage run --source='accounts,catalog,inventory,sales,agents,stockops,notifications,webapp' manage.py test
coverage report
```

### What's not covered yet
Shops/Categories CRUD, notifications, and reporting endpoints are simple enough that they weren't prioritized for tests — the coverage gaps are mostly there, plus some webapp view edge cases (currently 54% on `webapp/views.py`). Worth filling in before this goes into any kind of production use.

## Update — SQLite by default, MTN-inspired design system

**Database:** switched default from MySQL to SQLite (`DB_ENGINE=sqlite` in `.env.example`). No database server to install or run — `python manage.py migrate` creates `db.sqlite3` automatically. MySQL is still supported (`DB_ENGINE=mysql` + `db/schema.sql`) if SOCOBYS ever needs multi-server production deployment, but for a solo internship project SQLite is simpler and is now the default.

**Design:** the webapp frontend now has an actual design system (`webapp/static/webapp/css/theme.css`) inspired by MTN's real brand identity — vivid yellow (`#FFCC00`) + black, chosen deliberately (per MTN's own published brand rationale) for trust, energy, and high contrast/accessibility. SOCOBYS is an MTN partner agency, so this ties the system visually to that ecosystem without using MTN's actual logo or trademarked assets.

What changed:
- Custom CSS variables, Inter font (Google Fonts), consistent border-radius/shadow language
- Navbar: black background, yellow "SOCOBYS" badge, active-link highlighting
- Split-screen login/register pages (yellow brand panel + white form panel)
- Dashboard: stat cards with yellow top-accent, icon-based quick-access cards
- Catalogue: proper product cards with category tag, yellow price badge
- Consistent `.btn-mtn` (yellow), `.btn-mtn-dark` (black), `.btn-mtn-outline` button system across every page
- Dark-themed table headers with yellow row-hover highlight

Uses Bootstrap 5 (CDN) as the layout/grid foundation, with the custom theme layered on top — no build tooling, still just HTML + CSS.

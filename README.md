# Finance Backend

## Author & submission 

| Field | Value |
|--------|------------|
| **Name** | *KEERTHANA BOLLEPALLY* |
| **Email / contact** | *bkeerthanaraj4@gmail.com* |
| **Repository** | *(https://github.com/keerthanabollepally/zorvyn_finance_backend_assignment)* |

## Tested environment

| Item | Value |
|------|--------|
| **OS** | Windows 10 / 11 |
| **Python** | Python 3.11.9 |



---

A small, production-minded REST API for per-user financial records: **FastAPI**, **SQLModel**, **JWT** auth, **policy-based RBAC** via a `RolePermission` table, **SQL aggregations** for dashboards, **soft-delete** on records, **search**, **pagination**, **rate limiting** (SlowAPI), and **pytest** coverage for core flows.

## Assumptions

- Each **user** has exactly **one role**: `viewer`, `analyst`, or `admin`.
- **Financial records** are **multi-tenant by `user_id`** (each row belongs to one user).
- **Public signup** always creates a **viewer** (no self-service promotion to `analyst` / `admin` — avoids privilege escalation). Admins change roles via `PATCH /users/{id}`.
- **Viewer**: read **only their own** records; **dashboard** scoped to self; **no** create/update/delete on records.
- **Analyst**: **read all** users’ records (and optional `user_id` filter); **create/update/delete only their own** records.
- **Admin**: full **user management**; **CRUD on any user’s** records; **hard-delete** option on records; **`include_deleted`** on list.
- **Soft-delete**: `DELETE /records/{id}` sets `is_deleted=true` (default). **Hard-delete** (`?hard=true`) removes the row (**admin only**).
- **Category summary** `total_amount` is **net per category** (sum of income amounts minus sum of expense amounts) for the scoped rows.
- **Trend** API uses SQLite `strftime` for buckets (`week` / `month`). For PostgreSQL you may switch to `date_trunc` in `dashboard_service.trend` (trade-off documented below).

## Tech stack

| Layer | Choice |
|--------|--------|
| API | FastAPI (OpenAPI → **Swagger UI** `/docs`, **ReDoc** `/redoc`) |
| DB | SQLite by default (`finance.db`); optional **PostgreSQL** via `DATABASE_URL` |
| ORM / validation | SQLModel + Pydantic v2 |
| Auth | JWT (HS256), `Authorization: Bearer <token>` |
| Passwords | bcrypt via passlib |
| Rate limits | SlowAPI (`SlowAPIMiddleware` + limits on auth routes) |

## Architecture

- **`app/main.py`** — App factory, lifespan (create tables + seed permissions), global exception handlers (consistent JSON errors), SlowAPI wiring.
- **`app/models.py`** — `User`, `FinancialRecord`, `RolePermission`.
- **`app/schemas.py`** — Request/response DTOs and validation (e.g. `amount > 0`, ISO dates, enums).
- **`app/auth.py`** — Password hashing, JWT create/decode, `get_current_user`.
- **`app/middleware/auth_middleware.py`** — `check_permission(session, user, action)`, `RequirePermission("action")`, optional `require_role(...)`.
- **`app/services/`** — Business rules and SQL-heavy work (`user_service`, `record_service`, `dashboard_service`).
- **`app/api/`** — Thin routers delegating to services.
- **`app/rate_limit.py`** — Shared SlowAPI `Limiter` instance.

Access control is **not** only `if role == "admin"`: route dependencies require **named permissions** that must exist in **`RolePermission`** (seeded at startup). Additional rules (e.g. analyst may edit only own records) live in **services** so they stay enforced regardless of the client.

## API overview

### Users & roles

| Method | Path | Auth / permission |
|--------|------|-------------------|
| POST | `/users/signup` | Public (rate-limited) |
| POST | `/users/login` | Public (rate-limited) → JWT |
| GET | `/users/me` | JWT |
| GET | `/users` | `manage_users` (admin) |
| PATCH | `/users/{id}` | `manage_users` |
| PATCH | `/users/{id}/deactivate` | `manage_users` (sets `is_active=false`) |

### Records

| Method | Path | Notes |
|--------|------|--------|
| POST | `/records` | `create_records` |
| GET | `/records` | Filters: `date_from`, `date_to`, `type`, `category`, `user_id` (admin/analyst), `q` (search **notes** or **category**), `offset`, `limit`, `include_deleted` (admin) |
| GET | `/records/{id}` | Single record |
| PATCH | `/records/{id}` | Update |
| DELETE | `/records/{id}` | Soft-delete; `?hard=true` admin only |

### Dashboard (SQL aggregations)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/dashboard/summary` | `total_income`, `total_expense`, `net_balance`, `recent_activity` |
| GET | `/dashboard/category-summary` | Per-category net (`total_amount`) |
| GET | `/dashboard/trend` | Query `granularity` = `week` or `month`; returns `date_group`, `income`, `expense` |

### Error shape

Non-2xx responses aim for:

```json
{
  "error": "machine_code",
  "message": "Human-readable explanation.",
  "status_code": 400
}
```

Validation errors use `error: "validation_error"`.

## How to run

From this directory:

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

- **Interactive docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) (Swagger UI)  
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

**Swagger UI**: after starting the server, open `/docs` to see grouped tags (users, records, dashboard), try auth via **Authorize** with `Bearer <token>`, and execute requests. A screenshot for your write-up can be the `/docs` page showing those groups and a sample `POST /users/login` response.

### Deploy (free tier — Render + PostgreSQL)

Cloud hosts **do not keep SQLite files** reliably. Use **PostgreSQL** on the host and set **`DATABASE_URL`**.

**1. Push your code to a public GitHub repo** (root should contain `requirements.txt`, `app/`, and `Procfile`).

**2. Create a PostgreSQL database on Render**

- [Render Dashboard](https://dashboard.render.com) → **New +** → **PostgreSQL**
- Pick the **Free** plan, create the database, wait until it is **available**.

**3. Create a Web Service**

- **New +** → **Web Service** → connect the **same GitHub repo**.
- **Runtime:** Python  
- **Build command:** `pip install -r requirements.txt`  
- **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`  
  (Same as `Procfile`; Render reads `$PORT` automatically.)

**4. Environment variables** (Web Service → **Environment**)

| Key | Value |
|-----|--------|
| `DATABASE_URL` | Copy from your Render Postgres: **Internal Database URL** (paste as-is; the app fixes `postgres://` → `postgresql://`). |
| `JWT_SECRET_KEY` | Long random string (e.g. 32+ characters). **Required** on the internet. |
| `DATABASE_SSL_REQUIRE` | If the DB connection fails with an SSL error, set to `true`. Many internal Render URLs work without it. |

**5. Deploy**

- Save; Render builds and deploys. Open your service URL + **`/docs`** (e.g. `https://your-service.onrender.com/docs`). That is the link you can put under **“Live Demo or API Documentation URL”** in your submission.

**Cold starts:** Free web services **spin down** after idle time; the first request after sleep can take ~30–60 seconds.

**First admin on production:** Sign up via `/docs`, then in any PostgreSQL client connected to the same database run:

```sql
UPDATE "user" SET role = 'admin' WHERE email = 'your-signup-email@example.com';
```

(PostgreSQL table name may be `user` — quoted because it is a reserved word in SQL.) Log in again to get a new JWT.

### Environment variables

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | Default `sqlite:///./finance.db`. PostgreSQL: full URL (app includes `psycopg2-binary`). Render’s **Internal** URL is fine. |
| `DATABASE_SSL_REQUIRE` | Set to `true` if Postgres requires SSL (some external URLs). |
| `JWT_SECRET_KEY` | Secret for signing JWTs (set in production) |
| `FINANCE_SKIP_DB_INIT` | Set to `1` for tests only (skips lifespan migrations on the default engine) |

### Creating the first admin (local SQLite)

After signup, promote your user, e.g.:

```sql
UPDATE user SET role = 'admin' WHERE email = 'you@example.com';
```

On **PostgreSQL**, use a quoted table name: `UPDATE "user" SET role = 'admin' WHERE email = '...';`  
Or run `python scripts/promote_admin.py you@example.com` (uses local `finance.db` only).

Then log in again to receive a token with admin permissions.

## Tests

```bash
pytest
```

Includes happy-path API tests and a **unit-style** check for **net balance** / SQL totals (`tests/test_net_balance.py`). Tests use an in-memory SQLite database with `StaticPool` and override `get_session`.

## Trade-offs

- **JWT vs OAuth2/OIDC**: Simpler to ship and demo; no refresh tokens or revocation list (acceptable for an assignment; production would add refresh flows or shorter TTLs).
- **SQLite default**: Zero setup; PostgreSQL is a connection-string change for real deployments.
- **Trend SQL**: Uses SQLite `strftime` locally; **PostgreSQL** uses `to_char` for month / ISO week (see `dashboard_service._trend_date_group`).
- **Rate limiting**: IP-based (`get_remote_address`); behind proxies, configure trusted headers or a different key function.

## Project layout

```
finance_backend/
├── app/
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   ├── database.py
│   ├── auth.py
│   ├── exceptions.py
│   ├── rate_limit.py
│   ├── services/
│   │   ├── user_service.py
│   │   ├── record_service.py
│   │   └── dashboard_service.py
│   ├── api/
│   │   ├── users.py
│   │   ├── records.py
│   │   └── dashboard.py
│   └── middleware/
│       └── auth_middleware.py
├── tests/
├── requirements.txt
├── Procfile
└── README.md
```

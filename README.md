# Agricure — AI Crop Health & Early Warning Agent

A full-stack upgrade of the original Agricure prototype (single-file React + localStorage)
into a real client–server system with a **FastAPI backend, PostgreSQL database, pluggable
AI inference layer, and an explainable Intelligent Agent decision engine** — built as an
academic AI Intelligent-Agent project.

The original visual identity, UX, farmer/officer workflows, icons and the four languages
(English, हिंदी, मराठी, ಕನ್ನಡ) are preserved. localStorage is gone: all reports, users,
referrals, notifications and AI decisions now live in PostgreSQL behind a JWT-secured REST API.

---

## The Intelligent Agent architecture (viva map)

```
PERCEPTION      crop image + weather + sensor readings ingested
   ↓
STATE / MEMORY  recent history, 14-day nearby similar reports (PostgreSQL)
   ↓
REASONING       transparent rule-based risk engine (scored, labelled factors)
   ↓
DECISION        agent decision engine: spread risk, priority, actions,
                officer-review / lab-referral / regional-alert flags
   ↓
ACTION          recommendations + notifications persisted; officer queue updated
   ↓
FEEDBACK        officer verification (confirm / correct) stored as model feedback
   ↓
LEARNING        feedback rows queue for the next retraining cycle (explicit, manual)
```

Every stage writes a timestamped row to `agent_activity`, visible in the UI as
**"AI Agent Activity"** on the farmer result screen and in the officer dashboard.

---

## Project structure

```
frontend/                 React 18 + Vite + Tailwind (original UI, API-connected)
  public/demo-photos/     real crop photos per crop type (CC-licensed, see CREDITS.txt)
  src/api/                fetch client, design tokens, icon set
  src/components/         shared UI, WhyThisDecision, AgentActivity
  src/pages/              Landing, Login, FarmerPage, OfficerPage, AdminPage
  src/hooks/              useAuth (JWT in memory), useLanguage
  src/i18n/               4-language translations (all new UI strings included)

backend/
  app/
    main.py               FastAPI app, CORS, static images, startup schema
    config.py             all settings from environment (.env)
    database.py           SQLAlchemy engine (PostgreSQL, SQLite fallback)
    models/               13 SQLAlchemy tables (see database/schema.sql)
    schemas/              Pydantic request/response validation
    routers/              auth, farms, reports, sensors, referrals, notifications,
                          analytics, verification, model, admin, export, demo
    services/             storage (LOCAL/SUPABASE/CLOUDINARY), weather, notifications
    agents/               risk_engine.py, decision_engine.py, pipeline.py
    ai/                   inference_service.py (bridge to ml/)
    auth/                 JWT + bcrypt + role-based dependencies
  tests/test_smoke.py     end-to-end acceptance test (61 checks)
  .env.example            every knob documented; copy to .env

ml/                       separate AI inference package
  inference.py            CropDiseaseModel: REAL_MODEL vs DEMO_MODEL
  preprocessing.py        image → normalised tensor
  model_loader.py         pluggable Keras loader (lazy TF import)
  disease_catalog.py      crops, diseases, treatments (single source of truth)

database/
  schema.sql              PostgreSQL DDL (reference)
  seed.py                 idempotent demo data seeder (runs the real agent pipeline)

legacy/index.html         the original prototype, preserved untouched
```

---

## Honest AI labelling (important)

There are **three inference modes** and the UI states which one produced every report:

| `AI_MODE` | What it actually does | UI label |
|---|---|---|
| `HEURISTIC_CV` *(default)* | **Real image analysis.** The uploaded photo is decoded and measured: healthy-green fraction, chlorotic (yellow) fraction, necrotic (brown/dark) fraction, powdery residue, and dark lesion clustering. Deterministic rules map those measurements onto the crop's disease catalogue. It genuinely inspects the picture, but it is a **rule-based heuristic, not a trained neural network**. | "Image analysis: rule-based computer-vision heuristic (real pixel analysis, not a trained neural network)." |
| `DEMO_MODEL` | Deterministic **simulated** classifier hashed from the image bytes — does not look at the image content at all. | "DEMO INFERENCE — simulated AI, not a trained model" |
| `REAL_MODEL` | A trained Keras model loaded from `MODEL_PATH` (see below). | "Analysed by a trained crop-disease model" |

* Reports store `model_version` and `is_demo_inference`, so real analysis is always
  distinguishable from simulated output in the database as well as the UI.
* To use a trained model: train/obtain a Keras model over the disease catalog
  (`ml/disease_catalog.py` + a `Healthy` class), then set:

  ```
  AI_MODE=REAL_MODEL
  MODEL_PATH=./ml/weights/agricure_crop_disease.keras
  MODEL_LABELS_PATH=./ml/weights/labels.txt
  ```

  If `REAL_MODEL` is set but the model can't be loaded, the server logs a loud warning and
  falls back to the heuristic image analysis — it never fakes real inference.
* The risk engine is a **transparent rule-based prototype**, not a scientifically
  validated epidemiological model. The UI labels it "Prototype decision model".
* Weather defaults to `WEATHER_MODE=DEMO_WEATHER` (labelled sample data). Set
  `WEATHER_MODE=OPENWEATHER` + `OPENWEATHER_API_KEY` for live data.

### Demo photos

`frontend/public/demo-photos/` holds a diseased and a healthy sample per crop. They are
validated with the **same classifier the app uses**, so pressing *Use a Demo Photo* really
does produce the matching report (e.g. tomato `Alternaria solani` photo → "Early Blight").
`CREDITS.txt` lists each file's source; files marked `SYNTHETIC` are generated leaf
images (used where no suitable CC-licensed photo was found). Re-check or repair them at
any time:

```bash
backend/.venv/Scripts/python scripts/verify_demo_photos.py
```

---

## Setup (local)

### Prerequisites
* Python 3.10+ — the venv is already created at `backend/.venv` (recreate with
  `python -m venv backend/.venv`)
* Node 18+
* PostgreSQL **optional** — if it's not running, the backend automatically falls back to a
  local SQLite file with a clear console warning (zero-setup demo). For the real thing:

### 1. Backend

```bash
cd backend

# create the database (skip if using the SQLite fallback)
createdb agricure
#   or in psql:  CREATE DATABASE agricure;

# configure
copy .env.example .env        # Windows  (macOS/Linux: cp .env.example .env)
#   edit DATABASE_URL + SECRET_KEY; generate a key with:
#   python -c "import secrets; print(secrets.token_hex(32))"

# install deps (already installed in .venv for this checkout)
.venv\Scripts\pip install -r requirements.txt

# seed demo data (idempotent; also creates all tables)
.venv\Scripts\python ..\database\seed.py

# run
.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

* API: http://localhost:8000  · Swagger docs: http://localhost:8000/docs
* Health: http://localhost:8000/api/health

### 2. Database migrations / schema

Two supported paths:
* **Automatic** — the app creates all tables on startup (and `seed.py` does too).
* **Manual SQL** — `psql -d agricure -f database/schema.sql` (reference DDL, matches the ORM).
* For evolving an existing production DB, use Alembic (already in requirements):
  `alembic init migrations`, point `env.py` at `app.database.Base.metadata`, autogenerate.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173  (proxies /api → :8000)
```

Production build: `npm run build` → serve `dist/` and set `VITE_API_BASE` to the API origin.

### 4. Demo logins (only exist after seeding with DEMO_MODE=true)

| Role    | Email                     | Password    | Entry point |
|---------|---------------------------|-------------|-------------|
| Farmer  | `demo@agricure.app`       | `demo1234`  | **Enter as Farmer** / Farmer Login |
| Officer | `officer@agricure.gov.in` | `officer1234` | **Enter as Official** / Official Login |
| Admin   | `admin@agricure.gov.in`   | `admin1234` | **Admin Login** (top-right nav) |

The login screen has a Farmer / Official / Admin role switcher and per-role demo autofill.
Admin accounts cannot self-register by design.

Demo data is clearly labelled (reports carry `is_demo_inference`, model version `demo-v0`).
Re-seed anytime via `python ../database/seed.py` (idempotent) or `POST /api/demo/seed`.

### 4b. Demo crop photos

**Use a Demo Photo** on the farmer screen attaches a *real photograph* for the selected crop
(from `frontend/public/demo-photos/`, one per crop: Tomato, Wheat, Cotton, Rice, Onion),
which is then uploaded and analysed like any normal image. These were sourced from
Wikimedia Commons under CC licenses — see `demo-photos/CREDITS.txt`. To re-fetch or
refresh them: `python scripts/fetch_demo_photos.py` (requires internet).

### 5. Verify everything (acceptance test)

```bash
cd backend
.venv\Scripts\python tests\test_smoke.py
```

61 end-to-end checks: registration → farms → sensors → weather → report upload →
AI analysis → risk → agent decision → recommendations → officer verification/correction →
referrals → notifications → hotspots → model queue → admin → RBAC → CSV exports.

---

## API overview (full docs at /docs)

| Area | Endpoints |
|------|-----------|
| Auth | `POST /api/auth/register` `POST /api/auth/login` `GET /api/auth/me` |
| Farms | `GET/POST /api/farms` `PATCH/DELETE /api/farms/{id}` |
| Weather | `GET /api/weather?lat=&lon=&location=` |
| Sensors | `POST /api/sensors/readings` `GET /api/farms/{id}/sensors` |
| Reports | `POST /api/reports` (multipart) `POST /api/reports/{id}/analyze` `GET /api/reports` `GET /api/reports/all` `GET /api/reports/{id}` |
| Verification | `POST /api/verify/{report_id}` `GET /api/verify/feedback` |
| Referrals | `POST /api/referrals` `GET /api/referrals[/mine]` `PATCH /api/referrals/{id}/status` |
| Notifications | `GET /api/notifications` `GET /api/notifications/unread-count` `POST /api/notifications/{id}/read` `POST /api/notifications/read-all` |
| Analytics | `GET /api/analytics/dashboard` `GET /api/analytics/hotspots` `GET /api/analytics/agent-activity` `GET /api/analytics/disease-distribution` |
| Model | `GET /api/model/versions` `POST /api/model/versions` `POST /api/model/feedback` `POST /api/model/retraining/queue` `GET /api/model/status` |
| Admin | `GET /api/admin/stats` `GET /api/admin/users` `PATCH /api/admin/users/{id}/active` `GET /api/admin/audit-logs` |
| Export | `GET /api/export/{reports\|feedback\|referrals\|sensors}` (CSV, officer/admin) |

Roles: `FARMER` (own farms/reports/referrals/notifications), `OFFICER`
(all reports, verification, corrections, referrals, analytics, feedback), `ADMIN`
(users, system stats, model versions, audit log, exports).

---

## Security

* bcrypt password hashing, JWT bearer tokens (12 h expiry), role-based dependencies
* Pydantic validation on every payload; email validation via `email-validator`
* Uploads: content-type + extension whitelist (JPEG/PNG/WebP), size limit (`MAX_UPLOAD_MB`)
* CORS restricted to `CORS_ORIGINS`; secrets only via `.env` (never committed — `.env.example`
  is the template); demo passwords are seeded **only** when `DEMO_MODE=true`
* Audit log records logins, submissions, AI analyses, decisions, verifications,
  corrections, referrals, exports

## Object storage

`STORAGE_PROVIDER=LOCAL` (default) stores images under `backend/uploads` and only URLs in
PostgreSQL. `SUPABASE` and `CLOUDINARY` providers are implemented; if credentials are missing
they degrade to LOCAL with a warning instead of failing the upload.

## Switching to PostgreSQL from the SQLite fallback

1. Install/start PostgreSQL; create the `agricure` database.
2. Set `DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/agricure` in `backend/.env`.
3. Restart the API — tables are created automatically; run `database/seed.py` for demo data.

## Where your data is stored (and how to open it without the website)

### 1. The database

Everything the app records lives in a relational database through SQLAlchemy:

| What you want to see | Table |
|---|---|
| Every user: name, email, role, phone, language, **hashed** password, created_at | `users` |
| Which user submitted which sample, with the AI result | `crop_reports` (+ `farmer_id` → `users.id`) |
| The stored sample photo for each report | `crop_reports.image_url`, `crop_reports.image_path` |
| The agent's reasoning per report | `agent_decisions` |
| The step-by-step agent trace (PERCEPTION → LEARNING) | `agent_activity` |
| Advice shown to the farmer | `recommendations` |
| Officer confirmations / diagnosis corrections | `officer_verifications` |
| Lab / field referrals and their status | `referrals` |
| Pest-trap, soil and leaf-wetness readings | `sensor_readings` |
| Farmer/officer/admin alerts | `notifications` |
| Learning loop: predicted vs actual disease | `model_feedback` |
| Model versions + retraining status | `model_versions` |
| Who did what, when | `audit_logs` |
| Farms and their locations | `farms` |

**Where the file actually is**

* **SQLite fallback (what runs on this machine right now, because PostgreSQL isn't running):**
  `backend/agricure_dev.db` — **relative to the working directory you launch the API from**, so
  always start the server from inside `backend/` (that's what `start.bat` does).
  ⚠️ If you start it from the project root you'll get a second, empty database in the root folder.
* **PostgreSQL (the intended setup):** a server-side database, e.g. `agricure` on `localhost:5432`.
  The connection string is `DATABASE_URL` in `backend/.env`.

**Uploaded sample images** live as files in `backend/uploads/` (LOCAL storage provider) and are
served at `http://localhost:8000/api/images/<name>`; only the URL/path is kept in PostgreSQL.
With `STORAGE_PROVIDER=SUPABASE` or `CLOUDINARY` the bytes go to that provider instead.

### 2. Open the database without the website

**Option A — SQLite file (this machine)**

```bash
# 1) simplest: SQLite CLI (ships with Python)
cd backend
.venv/Scripts/python -c "import sqlite3; c=sqlite3.connect('agricure_dev.db'); print(c.execute('select count(*) from crop_reports').fetchone())"

# 2) interactive shell
.venv/Scripts/python -m sqlite3 agricure_dev.db
sqlite> .tables
sqlite> select u.name, substr(u.email,1,24), r.id, r.crop, r.disease, r.confidence, r.risk_level
   ...> from crop_reports r join users u on u.id = r.farmer_id order by r.created_at desc;
```

* **DB Browser for SQLite** (free GUI, sqlitebrowser.org) → *Open Database* →
  `AI Crop Health/backend/agricure_dev.db` → *Browse Data* tab → pick `crop_reports`.
  The `image_path` column tells you the exact file in `backend/uploads/` for each sample.
* **VS Code**: install *SQLite Viewer* and click the `.db` file.

**Option B — PostgreSQL (the real setup)**

```bash
psql -U agricure -d agricure
agricure=# \dt
agricure=# select u.name, u.role, count(*) as samples
           from users u left join crop_reports r on r.farmer_id = u.id
           group by u.name, u.role order by samples desc;
```
or open the same server in **pgAdmin** / **DBeaver** using the `DATABASE_URL` credentials.

**Option C — REST API without the UI** (Swagger: http://localhost:8000/docs)

```bash
# log in, then read any table through the API
curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@agricure.gov.in","password":"admin1234"}'

curl -s http://localhost:8000/api/reports/all/grouped -H "Authorization: Bearer <TOKEN>"
curl -s http://localhost:8000/api/admin/stats        -H "Authorization: Bearer <TOKEN>"
curl -s http://localhost:8000/api/admin/audit-logs   -H "Authorization: Bearer <TOKEN>"
# CSV dumps (open in Excel): /api/export/reports | /sensors | /referrals | /feedback
```

### 3. Every report is attributed to the user who gave the sample

`crop_reports.farmer_id` is a foreign key to `users.id`, and the stored image path sits on the
same row — so "which user gave this sample, and what did Agricure report for it?" is one join:

```sql
SELECT r.id, u.name AS farmer, u.email, r.crop, r.disease, r.confidence,
       r.severity, r.risk_level, r.status, r.image_path, r.created_at
FROM crop_reports r
JOIN users u ON u.id = r.farmer_id
ORDER BY r.created_at DESC;
```

This is exactly what the **Admin → "All Samples & Reports"** tab shows live (per-user groups,
thumbnails served from the stored image, disease/confidence/risk, auto-refresh every 10 s).

**Passwords:** only bcrypt hashes are ever stored (`users.password_hash`). They are one-way —
the plain password of an existing account cannot be recovered, only reset by re-running
`database/seed.py` (which recreates demo users) or by registering a new account.

## Motion & visual effects

The frontend carries a small, self-contained motion layer — **no animation library**, just CSS
keyframes plus two hooks, so the bundle stays ~84 kB gzipped.

| Piece | What it does |
|---|---|
| `src/index.css` | Keyframes for scroll reveals, masked text, marquee, film grain, drifting colour fields, sheen, lift, image zoom, pulse, shimmer, scroll progress |
| `hooks/useReveal.js` | `useReveal` (IntersectionObserver reveal), `useParallax`, `useScrollProgress`, `useMagnetic` |
| `components/motion.jsx` | `Reveal`, `MaskedLines`, `Marquee`, `CountUp`, `ScrollProgress`, `CursorAura`, `GlowBlobs`, `ScrollCue`, `MagneticButton`, `Parallax`, `AnalysisProgress` |

Where they appear:

* **Landing** — hero headline rises line-by-line behind a mask, gradient blobs drift behind it,
  sticky nav gains a blurred background on scroll, the agent-loop marquee band scrolls
  endlessly (pauses on hover), a scroll cue invites the visitor down, KPI numbers count up,
  CTAs lean toward the cursor (magnetic) and flash a sheen on hover.
* **Farmer** — submitting a report plays the **live agent pipeline**: each stage
  (Perception → Memory → Reasoning → Decision → Action → Learning) fills in as it is reached, then
  the result panel wipes in. Sample photos zoom on hover, history rows slide in with a stagger.
* **Officer** — KPI cards count up with a hover lift, hotspot markers on the map pulse with an
  animated halo, tab buttons lift and shadow on hover.
* **Admin** — the live-refresh badge pulses, each farmer group and every sample row eases in with
  a stagger, thumbnails zoom on hover.

**Accessibility:** every effect is disabled under `prefers-reduced-motion: reduce`, and the
cursor aura is skipped entirely on touch devices — it never replaces the native cursor.

## Notes for the viva

* The **agent activity feed** is persisted per report (`agent_activity` table) — open any
  result screen to walk the examiner through PERCEPTION → LEARNING.
* The **why-this-decision panel** is generated from stored fields (risk factors,
  environmental values, nearby counts) — nothing is hardcoded prose.
* Demo vs real: `GET /api/model/status` shows the active mode; every demo report row carries
  `is_demo_inference=true`, and the UI prints a demo banner on such results.

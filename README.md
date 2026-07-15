# Atharva — Billing, Payments & Analytics

A Django 5.x web application for a small electrical goods trading business. Features invoicing with GST tax invoice PDF generation, payment tracking, and a live analytics dashboard.

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, Django 5.x |
| Database | PostgreSQL (Supabase) |
| PDF | WeasyPrint |
| Frontend | Django Templates + Bootstrap 5 + Chart.js |
| Auth | Django built-in |
| Config | python-decouple + dj-database-url |

---

## Quick Start

### 1. Clone and install dependencies

```bash
git clone <repo-url>
cd invoice-pdf
pip install -r requirements.txt
```

### 2. Configure environment

```bash
# Copy example env file
copy .env.example .env
```

Edit `.env` and fill in:

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
DATABASE_URL=postgresql://postgres:your-password@db.xxxxxxxxxxxx.supabase.co:5432/postgres?sslmode=require
ALLOWED_HOSTS=localhost,127.0.0.1
```

> **Supabase Setup**: Create a project at [supabase.com](https://supabase.com), go to Project Settings → Database → Connection String (URI), and paste it as `DATABASE_URL`.

### 3. Generate a secret key

```python
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 4. Run migrations

```bash
python manage.py migrate
```

### 5. Create superuser (admin login)

```bash
python manage.py createsuperuser
```

### 6. Load demo data

```bash
python manage.py seed_data
```

### 7. Start the development server

```bash
python manage.py runserver
```

Visit `http://127.0.0.1:8000/` — you'll be redirected to the login page.

---

## Adding Staff Users

1. Log in as superuser
2. Go to `/admin/` → Users → Add User
3. Set `is_staff = True` for billing staff (they can log in to the main app)
4. Set `is_superuser = True` only for admins who need the admin panel

---

## Collecting Static Files (Production)

```bash
python manage.py collectstatic
```

---

## WeasyPrint on Windows

WeasyPrint requires the GTK3 runtime on Windows. Install it from:
https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases

Or use WSL/Linux for production deployments.

---

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | Yes | Django secret key |
| `DEBUG` | No | `True` for dev, `False` in prod |
| `DATABASE_URL` | No* | PostgreSQL URL (falls back to SQLite) |
| `ALLOWED_HOSTS` | No | Comma-separated hostnames |

*If `DATABASE_URL` is not set, the app falls back to a local SQLite file `db.sqlite3`. This is useful for local development without Supabase.

---

## Feature Overview

- **Dashboard** — 4 KPI cards, monthly line chart, top parties bar chart, outstanding balances table
- **Invoices** — Create/edit with inline line items, live JS totals, auto invoice numbering (ISL-000001)
- **PDF Export** — Full GST Tax Invoice with WeasyPrint, all required fields
- **Payments** — Record payments (Cash/Cheque/NEFT/UPI), link to invoices, advance payments
- **Parties** — Customer master with full invoice and payment history
- **Company Profile** — Set your GSTIN, bank details, logo for PDF header

---

## Project Structure

```
invoice-pdf/
├── atharva/           # Django project config
│   ├── settings.py
│   └── urls.py
├── billing/           # Main app
│   ├── models.py      # 5 models
│   ├── admin.py
│   ├── forms.py
│   ├── views.py
│   ├── urls.py
│   ├── utils.py       # amount_in_words, party_balance
│   └── templatetags/
│       └── billing_tags.py
├── templates/
│   ├── base.html
│   ├── registration/login.html
│   └── billing/       # All page templates + invoice_pdf.html
├── static/css/
│   └── atharva.css
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

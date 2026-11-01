# Where Is My Hostel

Where Is My Hostel is a full-stack student housing platform for India. The project will help students discover PGs, hostels, private rooms and rental accommodation near coaching institutes, colleges, markets, railway stations and other important locations.

This repository currently contains the stable project foundation, a responsive student-focused homepage, student registration, login, logout and Django administration. The homepage uses clearly labelled sample city and property data for UI preview. Real listing, location, enquiry and profile workflows remain for the next development phases.

## Technology Stack

- Frontend: HTML5, Tailwind CSS, Vanilla JavaScript, Django Templates
- Backend: Python 3.14 and Django 6.1
- Database: PostgreSQL in production, SQLite for local development
- Maps and location services: Leaflet.js, OpenStreetMap, Nominatim, Overpass API (planned)
- Authentication: Django built-in authentication

## Project Structure

```text
WhereisMyHostel/
├── Backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── .env.example
│   ├── .env                         # local secrets, ignored by Git
│   ├── db.sqlite3                   # local development database, ignored by Git
│   ├── where_is_my_hostel/
│   │   ├── settings.py
│   │   ├── urls.py
│   │   ├── asgi.py
│   │   └── wsgi.py
│   ├── accounts/                    # registration, login and logout
│   ├── properties/                  # PG, hostel and room listings
│   ├── locations/                   # cities, areas, coordinates and nearby places
│   ├── enquiries/                   # student enquiries and owner responses
│   ├── core/                        # homepage, common pages and shared functionality
│   ├── templates/
│   │   ├── base.html
│   │   ├── 404.html
│   │   ├── 500.html
│   │   ├── partials/
│   │   │   ├── navbar.html
│   │   │   ├── footer.html
│   │   │   └── messages.html
│   │   ├── core/
│   │   ├── accounts/                # login.html, register.html
│   │   └── properties/
│   ├── static/
│   │   ├── css/tailwind.css         # compiled Tailwind output
│   │   ├── js/main.js
│   │   └── images/
│   ├── media/                       # user uploads
│   └── staticfiles/                 # collectstatic output, ignored by Git
├── Frontend/
│   ├── package.json
│   ├── package-lock.json
│   ├── tailwind.config.js
│   ├── scripts/run-tailwind.js
│   └── src/input.css
├── .gitignore
└── README.md
```

Frontend build tooling lives in `Frontend/`. Django templates, static output, media and backend logic live in `Backend/`. The compiled stylesheet is written to `Backend/static/css/tailwind.css` so Django can serve it directly.

## Installed Dependencies

Backend dependencies are pinned in `Backend/requirements.txt`:

- Django 6.1
- psycopg 3.3.6 with binary support (PostgreSQL driver)
- python-dotenv 1.2.3

Frontend development dependency:

- Tailwind CSS 3.4.17

The workspace environment already has Django, psycopg and python-dotenv installed. Node.js 20 and npm 10 are also available.

## Environment Configuration

Copy the example file and set your own values:

```powershell
Copy-Item Backend/.env.example Backend/.env
```

Generate a Django secret key:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

Add the generated value to `DJANGO_SECRET_KEY` in `Backend/.env`. Never commit the real `.env` file.

Supported variables:

| Variable | Purpose | Default |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | Required Django secret key | none |
| `DJANGO_DEBUG` | Development mode | `True` |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated allowed hosts | `localhost,127.0.0.1` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Comma-separated trusted origins | empty |
| `DB_ENGINE` | `sqlite` or `postgresql` | `sqlite` |
| `DB_NAME` | SQLite filename or PostgreSQL database name | `db.sqlite3` |
| `DB_USER` | PostgreSQL user | empty |
| `DB_PASSWORD` | PostgreSQL password | empty |
| `DB_HOST` | PostgreSQL host | empty |
| `DB_PORT` | PostgreSQL port | `5432` |
| `CONTACT_EMAIL` | Public contact address shown on the contact page | empty |
| `EMAIL_BACKEND` | Django email backend; empty selects console in debug and SMTP otherwise | empty |
| `EMAIL_HOST` | SMTP host | `localhost` |
| `EMAIL_PORT` | SMTP port | `587` |
| `EMAIL_HOST_USER` | SMTP username | empty |
| `EMAIL_HOST_PASSWORD` | SMTP password | empty |
| `EMAIL_USE_TLS` | Enable SMTP TLS | `True` |
| `EMAIL_USE_SSL` | Enable SMTP SSL | `False` |
| `EMAIL_TIMEOUT` | SMTP timeout in seconds | `10` |
| `DEFAULT_FROM_EMAIL` | Sender address for outgoing mail | `no-reply@whereismyhostel.example` |
| `DJANGO_LOG_LEVEL` | Root logging level | `INFO` |

In development, email is written to the console. When `DJANGO_DEBUG=False`, the SMTP backend is selected automatically. Configure the SMTP credentials before enabling any email-based flows.

## Database Configuration

The current local setup uses SQLite because no PostgreSQL server is configured on this machine:

```env
DB_ENGINE=sqlite
DB_NAME=db.sqlite3
```

To use PostgreSQL, create a database and update `Backend/.env`:

```env
DB_ENGINE=postgresql
DB_NAME=where_is_my_hostel
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432
```

Startup validation raises a clear error if PostgreSQL is selected without the required connection settings. Migrations use the Django ORM and work with either database backend.

## Local Setup

### 1. Backend

```powershell
cd Backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Add a generated DJANGO_SECRET_KEY to .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open <http://127.0.0.1:8000/>.

If PowerShell blocks virtual environment activation, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### 2. Frontend styles

Install and build Tailwind from the `Frontend/` directory:

```powershell
cd Frontend
npm install
npm run build
```

For development with automatic rebuilds:

```powershell
npm run dev
```

Keep the Tailwind watcher and Django development server running in separate terminals.

## Available Routes

| Route | Purpose |
| --- | --- |
| `/` | Homepage |
| `/about/` | About the project |
| `/contact/` | Contact page |
| `/privacy/` | Privacy policy |
| `/terms/` | Terms of use |
| `/properties/` | Live property listings, search and multi-facet filtering |
| `/properties/<slug>/` | Live property detail with Leaflet map, gallery, room pricing, WhatsApp/call contact, and enquiry modal |
| `/properties/manage/` | Owner property management overview (Owner only) |
| `/properties/manage/new/` | Add a property listing with facilities & cover photo (Owner only) |
| `/properties/manage/<slug>/edit/` | Edit an owned property (Owner only) |
| `/properties/manage/<slug>/delete/` | Delete an owned property (Owner only) |
| `/properties/manage/<slug>/toggle-active/` | Deactivate or reactivate listing (Owner only) |
| `/properties/manage/<slug>/rooms/` | Room configurations inventory & quick bed/rent updater (Owner only) |
| `/properties/manage/<slug>/rooms/<pk>/edit/` | Edit single room configuration (Owner only) |
| `/properties/manage/<slug>/rooms/<pk>/delete/` | Delete room configuration (Owner only) |
| `/properties/manage/<slug>/rooms/<pk>/update-beds/` | Quick update available beds & rent (Owner only) |
| `/properties/manage/<slug>/gallery/` | Upload & manage categorized property photos (Owner only) |
| `/properties/manage/<slug>/gallery/<pk>/primary/` | Set photo as primary cover image (Owner only) |
| `/properties/manage/<slug>/gallery/<pk>/delete/` | Delete gallery photo (Owner only) |
| `/properties/favourite/<slug>/` | Toggle property favourite (Student only) |
| `/enquiries/submit/<slug>/` | Submit enquiry for property (Student only) |
| `/enquiries/my-enquiries/` | Student enquiry tracking list (Student only) |
| `/enquiries/manage/` | Owner enquiry review list (Owner only) |
| `/enquiries/manage/<pk>/status/` | Update enquiry status (Owner only) |
| `/accounts/register/` | Registration (Student or Property Owner) |
| `/accounts/login/` | Authentication login (Email or Username) |
| `/accounts/logout/` | Logout (POST only, CSRF protected) |
| `/accounts/dashboard/` | Role-routed dashboard (Student, Owner, Admin) |
| `/accounts/profile/` | Student profile view and edit (Student only) |
| `/accounts/favourites/` | Student saved stays (Student only) |
| `/accounts/owner/profile/` | Property owner business profile (Owner only) |
| `/admin/` | Django administration |
| `/health/` | JSON health check |

## Verification

```powershell
cd Backend
python manage.py check
python manage.py check --database default
python manage.py migrate --check
python manage.py test
python manage.py runserver
```

The 81-test suite covers core pages, homepage content, authenticated navigation, legal pages, property details, static asset discovery, health endpoint, custom 404 and 403 pages, live listing search and filtering, custom user roles (Student, Owner, Admin), registration form validation, email or username authentication, student profile updates, saved favourites, student enquiries and status tracking, owner business profiles, owner property management (create, edit, delete, activate/deactivate toggle), room configuration management (single/double/triple/four sharing, pricing, deposit, bed capacity validation, quick updater), categorized image gallery uploads (bedroom, bathroom, exterior, kitchen, common areas, primary image auto-reset), and strict role-based permission restrictions.

## Property, Room & Listing Management (Prompt 4)

- **Property Categories**: PG Accommodation (`pg`), Private Hostel (`private_hostel`), Student Hostel (`student_hostel`), Independent Room (`independent_room`), Shared Rental Room (`shared_room`), and Co-living Space (`coliving`). Legacy categories (`hostel`, `room`) remain supported for backward compatibility.
- **Extended Property Information**: Includes `gender_preference` (Boys, Girls, Unisex), complete address, city, state, PIN code, locality/area, landmark, latitude, longitude, `is_active`, `is_approved`, and automatic `created_at` / `updated_at` timestamps.
- **Room Configurations (`Room` model)**: Owners can add multiple room types per property specifying:
  - Occupancy (`Single`, `Double`, `Triple`, `Four Sharing`)
  - Monthly rent and security deposit
  - Total beds and available beds (with validation preventing `available_beds > total_beds`)
  - Bathroom type (`Attached`, `Common`)
  - Air conditioning (`AC`, `Non-AC`)
  - Availability toggle (`is_available`)
- **Facilities & Amenities**: Supports 15 standard amenities (Wi-Fi, Food/Mess, Laundry, AC, Study Table, Wardrobe, CCTV, Power Backup, RO Water, Parking, Housekeeping, Attached Bathroom, 24/7 Water, Security, Common Kitchen) plus custom amenities.
- **Categorized Photo Gallery (`PropertyImage` model)**: Owners can upload multiple high-resolution photos categorized by area (`exterior`, `bedroom`, `bathroom`, `kitchen`, `common_area`, `other`), with custom captions and one-click primary cover designation.
- **Owner Dashboard & Inventory Controls**:
  - Overview of all owned properties with live bed counts and room summaries.
  - Dedicated room inventory page with an inline quick bed and rent updater.
  - Categorized gallery manager with thumbnail preview, primary image tag, and file removal.
  - Immediate listing deactivation / reactivation toggle.
  - Django Admin actions for bulk approval and disapproval of listings.
- **Student View & Detailed Property Page**:
  - Live listing cards with starting rent (`min_monthly_rent`), room occupancy tags, facilities badges, and bed vacancy indicators.
  - Detailed property view with an interactive image switcher, full room inventory table with monthly rent and security deposits, Leaflet.js interactive OpenStreetMap integration (with fallback navigation links), one-click phone call and WhatsApp direct contact buttons, and an inline enquiry modal.

## Authentication and User Management

- **User Roles**: Three distinct roles are enforced across the platform: `Student`, `Property Owner`, and `Admin`.
- **Custom User Model**: Built on `accounts.User` extending `AbstractUser` with unique lowercase `email`, `full_name`, `mobile_number`, and `role`.
- **Registration**: Allows registration as either `Student` or `Property Owner`, with validation for full name, email, mobile number, password, and confirm password. Owners automatically receive an `OwnerProfile`.
- **Authentication**: `EmailOrUsernameBackend` allows users to log in with either their email address or username and password, with secure password hashing and session cycling.
- **Student Profile**: Students can view and update their profile details (name, mobile number), save favourite properties, and track submitted enquiries with real-time status badges (`Pending`, `Contacted`, `Closed`).
- **Property Owner Profile & Listing Management**: Owners can view and edit their business profile (owner name, contact number, business name, photo, address, city), manage their listed properties (create with photo upload, edit, delete), and review and update student enquiry statuses.
- **Permissions & Role-Based Access Control**:
  - Students cannot create or edit properties (HTTP 403 Forbidden).
  - Property owners can only edit, delete, or manage enquiries for their own properties (HTTP 403 Forbidden for cross-owner operations).
  - Platform administrators have complete access via `/admin/` and the admin dashboard to manage all users, profiles, listings, and enquiries.
  - Unauthenticated users can freely browse publicly active listings and property details, but are redirected to login for protected actions.
  - Dashboard routes to the appropriate role-specific experience (`dashboard_student.html`, `dashboard_owner.html`, `dashboard_admin.html`).
- **CSRF & Security**: All state-changing actions (forms, logout, enquiry status updates, favourites) require CSRF tokens. Logout is strictly POST-only. A dedicated branded 403 Access Denied page is served when authorization fails.

## Current Status and Known Gaps

- The project runs successfully on Django's development server.
- SQLite is active locally. PostgreSQL is configured in settings but is not installed or running on this machine, so a PostgreSQL connection has not been tested.
- `psql` is not available on the system PATH.
- Authentication, custom user roles, student/owner profiles, owner property management with photo upload, enquiry submission and tracking, and interactive property browsing filters are fully implemented and verified.
- The homepage and listing directory are implemented with responsive navy, white and amber styling, rich search filter controls (keyword, city, stay type, budget), city and accommodation cards, and live property cards with sample fallback previews.
- Next steps in future phases: Leaflet / OpenStreetMap map view integration, advanced distance calculations, and payment gateway integration.
- There is no separate REST API layer yet. Frontend-backend integration is currently server-rendered through Django templates, HTML forms, CSRF protection and the JSON health endpoint.
- Email is configured for console output in development and SMTP in production, but no application email flows exist yet and no SMTP account has been tested.
- No secrets are committed. `Backend/.env` is ignored by Git.

## Git

Git is initialized at the repository root. The `.env`, SQLite database, uploaded media, virtual environments, build caches and `node_modules` are excluded through `.gitignore`.

```powershell
git status
```

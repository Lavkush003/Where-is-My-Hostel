# Where Is My Hostel

[![Python 3.14](https://img.shields.io/badge/Python-3.14-blue.svg)](https://www.python.org/)
[![Django 6.1](https://img.shields.io/badge/Django-6.1-green.svg)](https://www.djangoproject.com/)
[![Tailwind CSS 3.4](https://img.shields.io/badge/Tailwind-3.4.17-38bdf8.svg)](https://tailwindcss.com/)
[![Leaflet.js](https://img.shields.io/badge/Leaflet-1.9.4-199900.svg)](https://leafletjs.com/)
[![Test Suite](https://img.shields.io/badge/Tests-146%20Passing-brightgreen.svg)]()
[![Zero Brokerage](https://img.shields.io/badge/Brokerage-0%25-orange.svg)]()

**Where Is My Hostel** is an intelligent, full-stack student accommodation discovery platform designed specifically for education and coaching hubs across India (Kota, Prayagraj, Delhi, Patna, Jaipur, Hyderabad, Bengaluru, Pune, and more).

Students can pinpoint PGs, hostels, and private rental rooms within walking distance of their specific coaching institute, college, library, or transit station using interactive OpenStreetMap maps, accurate Haversine distance calculations, multi-facet dynamic filters, and verified direct WhatsApp contact with property owners — with zero broker fees.

---

## Table of Contents

- [Key Features](#key-features)
- [Architecture & Tech Stack](#architecture--tech-stack)
- [Project Structure](#project-structure)
- [Quickstart & Local Installation](#quickstart--local-installation)
- [Demonstration Data Seeding](#demonstration-data-seeding)
- [Role-Based Access & Demo Accounts](#role-based-access--demo-accounts)
- [Feature Details](#feature-details)
  - [1. Smart Location Search & Nearby POIs](#1-smart-location-search--nearby-pois)
  - [2. Explore Stays & Dynamic Fetch Filtering](#2-explore-stays--dynamic-fetch-filtering)
  - [3. Student Enquiry Management & WhatsApp Links](#3-student-enquiry-management--whatsapp-links)
  - [4. Property Owner Management & Inventory](#4-property-owner-management--inventory)
  - [5. Platform Administration & Listing Moderation](#5-platform-administration--listing-moderation)
- [Security & Hardening Audit](#security--hardening-audit)
- [Performance & Database Optimization](#performance--database-optimization)
- [Testing & Quality Assurance](#testing--quality-assurance)
- [Production Deployment Guide](#production-deployment-guide)
- [License](#license)

---

## Key Features

1. **Intelligent Location Discovery**:
   - Geocoding of coaching institutes, colleges, railway stations, and local markets via OpenStreetMap Nominatim and curated landmarks.
   - Interactive Leaflet.js maps with distinct markers for accommodations, coaching centres, transit, and amenities.
   - Haversine geodesic distance calculation sorted by nearest first with radius filters (500m, 1km, 2km, 3km, 5km, 10km).
   - Live nearby facilities discovered via Overpass API (hospitals, libraries, restaurants, bus/metro stops) with 7-day persistent caching.

2. **Advanced Multi-Facet Property Filters**:
   - Search by city, locality, coaching centre, or transport hub.
   - Filters: budget range slider/dropdown, property type (PG, Private Hostel, Student Hostel, Independent Room, Co-living), gender preference (Boys, Girls, Unisex), room occupancy (Single, Double, Triple, Four sharing), AC/Non-AC, food/meals included, attached bathroom, Wi-Fi, and 15+ standard amenities.
   - Seamless Fetch API integration updating results, map markers, and pagination without full-page reloads while keeping browser URL query parameters synchronized.

3. **Student-to-Owner Enquiry Management**:
   - Students submit structured enquiries with preferred move-in dates, desired room occupancy, and personalized messages.
   - Validated direct WhatsApp click-to-chat links pre-filled with student and property details.
   - Complete enquiry lifecycle: `Pending` -> `Contacted` -> `Accepted` -> `Rejected` -> `Cancelled`.
   - Prevention of duplicate active enquiries and automatic status alerts in student and owner dashboards.

4. **Owner Inventory & Room Management**:
   - Multi-room configurations per property (occupancy, bed counts, AC/Non-AC, bathroom type, individual room rent, deposit).
   - Categorized photo gallery upload (bedroom, bathroom, exterior, kitchen, common areas) with 5MB upload restrictions, image validation, and one-click primary cover setting.
   - Quick bed vacancy and rent updater.

5. **Administrative Moderation Dashboard**:
   - High-level platform statistics (registered students, owners, properties, pending reviews, approval rates, enquiries, city-wise breakdown).
   - Listing moderation queue: inspect owner details, uploaded images, and approve, reject (with custom rejection reasons), or suspend suspicious listings.
   - User account activation/deactivation and city/locality management.

---

## Architecture & Tech Stack

| Layer | Technology | Purpose |
| --- | --- | --- |
| **Backend Framework** | Django 6.1 (Python 3.14) | Robust MVC web framework, ORM, authentication, CSRF security |
| **Database** | SQLite (Dev) / PostgreSQL (Prod via `psycopg 3.3.6`) | Relational database with composite indexing |
| **Frontend Styling** | Tailwind CSS 3.4.17 | Utility-first responsive design, modern cards, accessible forms |
| **Interactive Maps** | Leaflet.js 1.9.4 + OpenStreetMap | Interactive tile mapping, custom SVG pins, popup cards |
| **Geospatial APIs** | Nominatim (OSM) & Overpass API | Geocoding, landmark discovery, and points of interest |
| **Asynchronous UI** | Vanilla JavaScript + Fetch API | Fast, dependency-free dynamic filtering and map synchronization |
| **File Storage** | Django `FileSystemStorage` / AWS S3 | Secure user photo uploads with strict file type and size validation |

---

## Project Structure

```text
WhereisMyHostel/
├── Backend/                                # Django application backend
│   ├── manage.py                           # CLI management entrypoint
│   ├── requirements.txt                    # Pinned Python dependencies
│   ├── .env.example                        # Backend environment template
│   ├── where_is_my_hostel/                 # Django core configuration
│   │   ├── settings.py                     # App settings, security, DB, logging
│   │   ├── urls.py                         # Root URL routing
│   │   ├── asgi.py                         # ASGI interface
│   │   └── wsgi.py                         # WSGI interface
│   ├── accounts/                           # Auth, roles, profiles, admin views
│   │   ├── models.py                       # User, OwnerProfile
│   │   ├── backends.py                     # EmailOrUsernameBackend
│   │   ├── admin_views.py                  # Admin dashboard & moderation views
│   │   ├── forms.py                        # Register, login, profile forms
│   │   └── tests.py, tests_admin.py        # Comprehensive test suites
│   ├── properties/                         # Properties, rooms, galleries
│   │   ├── models.py                       # Property, Room, PropertyImage
│   │   ├── forms.py                        # Secure listing & image forms
│   │   ├── views.py                        # Listing, detail, manage, explore
│   │   └── tests.py                        # Property & room tests
│   ├── locations/                          # Geospatial search & POIs
│   │   ├── models.py                       # City, Locality, Landmark, PlaceCache
│   │   ├── services/
│   │   │   ├── geocoding.py                # Nominatim & curated landmarks
│   │   │   └── overpass.py                 # Overpass API nearby facility lookup
│   │   └── tests.py                        # Geocoding & distance calculation tests
│   ├── enquiries/                          # Student enquiry workflow
│   │   ├── models.py                       # Enquiry model with WhatsApp URLs
│   │   ├── forms.py                        # Enquiry submission form
│   │   ├── views.py                        # Submit, track, owner review views
│   │   └── tests.py                        # Enquiry lifecycle tests
│   ├── core/                               # Homepage, informational pages
│   │   ├── management/commands/
│   │   │   └── seed_demo_data.py           # Comprehensive demo data seeder
│   │   ├── views.py, tests.py
│   ├── templates/                          # Semantic HTML5 & Django templates
│   │   ├── base.html, 403.html, 404.html, 500.html
│   │   ├── partials/                       # navbar, footer, messages, sprites
│   │   ├── accounts/                       # Login, register, dashboards
│   │   │   └── admin/                      # Moderation, user & city management
│   │   ├── properties/                     # Explore, list, detail, room management
│   │   └── enquiries/                      # Tracking & review templates
│   ├── static/                             # Compiled CSS, JS, and authentic images
│   └── media/                              # Uploaded listing photos & avatars
├── Frontend/                               # Tailwind CSS build pipeline
│   ├── package.json
│   ├── tailwind.config.js
│   └── src/input.css
├── .env.example                            # Root environment template
├── .gitignore                              # Production-grade git ignore
└── README.md                               # Project documentation
```

---

## Quickstart & Local Installation

### Prerequisites
- Python 3.12+ (Python 3.14 recommended)
- Node.js 18+ and npm 9+
- Git

### 1. Clone & Set Up Virtual Environment

```bash
git clone https://github.com/Lavkush003/WhereisMyHostel.git
cd WhereisMyHostel
```

#### On Windows (PowerShell):
```powershell
Set-Location Backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

#### On macOS / Linux:
```bash
cd Backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables

```powershell
Copy-Item .env.example .env
```

Generate a secure Django secret key:
```powershell
python -c "import secrets; print(secrets.token_urlsafe(50))"
```
Paste this into `DJANGO_SECRET_KEY` in `Backend/.env`.

### 3. Run Migrations & Build Frontend Styles

Run database migrations:
```powershell
python manage.py migrate
```

Build Tailwind CSS in another terminal:
```powershell
cd ../Frontend
npm install
npm run build
```

---

## Demonstration Data Seeding

To immediately populate the platform with realistic student stays, verified landmarks, room types, and demonstration student, owner, and admin users, run:

```powershell
cd Backend
python manage.py seed_demo_data
```

This single idempotent command creates:
- **18 educational and transit landmarks** across student cities (Allen Career Institute, Resonance, Katra Coaching Hub, Batra Cinema Mukherjee Nagar, Karol Bagh Metro, etc.).
- **6 realistic accommodation listings** across Prayagraj, Kota, Delhi, Patna, and Jaipur with high-resolution room photos and amenity breakdowns.
- **Multiple room configurations** per property (Single AC, Deluxe Twin Sharing, Economy Triple with attached or common baths).
- **Realistic student enquiries** in varying states (`Pending`, `Contacted`, `Accepted`).

---

## Role-Based Access & Demo Accounts

The seeded database includes pre-configured accounts for testing every user experience:

| Role | Email Address | Password | Dashboard URL | Capabilities |
| --- | --- | --- | --- | --- |
| **Administrator** | `admin@whereismyhostel.example` | `AdminPassword123!` | `/accounts/dashboard/` | Full platform stats, approve/reject listings, suspend properties, user management, city management |
| **Property Owner** | `owner@whereismyhostel.example` | `OwnerPassword123!` | `/accounts/dashboard/` | List properties, edit stays, configure rooms, upload gallery photos, accept/reject student enquiries |
| **Student** | `student@whereismyhostel.example` | `StudentPassword123!` | `/accounts/dashboard/` | Search with map, filter stays, submit enquiries, save favourites, track enquiry statuses, direct WhatsApp |

---

## Feature Details

### 1. Smart Location Search & Nearby POIs
- **Haversine Distance**: Computes precise spherical distances between student search origins and accommodation coordinates.
- **Radius Filtering**: Instant filter options for stays within `500m`, `1km`, `2km`, `3km`, `5km`, and `10km`.
- **Overpass API Integration**: Retrieves nearby points of interest (coaching institutes, colleges, hospitals, metro stations, food spots) and renders category-coded markers on Leaflet maps.
- **Usage Policy & Throttling**: Built-in 1-second request throttling and 7-day persistent database caching (`PlaceCache`) to respect OpenStreetMap usage policies.

### 2. Explore Stays & Dynamic Fetch Filtering
- Dedicated `/properties/` view featuring:
  - **Dual Map/List View**: Toggle between a responsive property card grid and a split-screen interactive Leaflet map.
  - **Zero Full-Page Reloads**: Asynchronous Fetch API requests fetch JSON responses from the backend, re-rendering cards and repositioning map markers seamlessly.
  - **Deep-linking & History**: Selected filters are synchronized to URL query parameters for easy sharing and browser back/forward navigation.

### 3. Student Enquiry Management & WhatsApp Links
- Students submit enquiries directly from property detail pages with move-in date picker and occupancy selection.
- Unique constraints prevent duplicate active enquiries for the same property.
- Direct click-to-chat WhatsApp button pre-populates a verified greeting message directly to the owner.
- Owners can accept, reject, or mark enquiries as contacted with instant visual badge updates.

### 4. Property Owner Management & Inventory
- Intuitive owner dashboard showing live vacancy statistics.
- Room configuration inventory manager with inline quick bed vacancy and rent updater.
- Multi-photo upload manager with categorized tags and cover photo selector.

### 5. Platform Administration & Listing Moderation
- Custom administration dashboard at `/accounts/admin/dashboard/` (in addition to standard `/admin/`).
- Moderation workflow with rejection reason prompts, listing suspension, and user account status toggling.
- City and locality management for adding emerging coaching hubs.

---

## Security & Hardening Audit

- **CSRF Protection**: Audited across 100% of HTML forms and asynchronous endpoints (`{% csrf_token %}` enforced; state-changing requests use POST).
- **SQL Injection Prevention**: 100% of queries use Django ORM parameterized lookups.
- **XSS Prevention**: Django template auto-escaping enabled; all `|safe` usages strictly limited to internal JSON serialization and verified SVG icons.
- **File Upload Security**: Strict enforcement of 5MB file size limits and file extension whitelisting (`.jpg`, `.jpeg`, `.png`, `.webp`) on both property gallery photos and user profile photos.
- **Authentication & Authorization**: Strict role-based decorators (`@login_required`, `@student_required`, `@owner_required`, `@admin_required`) protect every view. Cross-owner data tampering is blocked with HTTP 403 Forbidden.
- **Production Defaults**: When `DJANGO_DEBUG=False`, automatic activation of HTTP Strict Transport Security (HSTS), SSL redirect, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `X-Content-Type-Options: nosniff`, and `X-Frame-Options: DENY`.

---

## Performance & Database Optimization

- **Composite Database Indexes**:
  - `Property`: `["city", "is_approved", "is_active", "is_suspended"]`, `["approval_status", "-created_at"]`, `["property_type", "gender_preference"]`, `["monthly_rent"]`.
  - `Room`: `["property", "is_available"]`, `["occupancy", "monthly_rent"]`.
  - `Enquiry`: `["status", "-created_at"]`, `["student", "-created_at"]`, `["property", "-created_at"]`.
- **Query Optimization**: Systematic use of `select_related("owner")` and `prefetch_related("rooms", "images")` eliminates N+1 query bottlenecks on directory listings.
- **Persistent Caching**: 7-day SQLite/PostgreSQL caching of external geographic API responses prevents repetitive HTTP calls.

---

## Testing & Quality Assurance

The test suite covers backend models, forms, views, permissions, geocoding fallback, and management commands:

```powershell
cd Backend
python manage.py test
```

### Test Suite Summary
- **146 Total Automated Tests** across all modules:
  - `accounts` (40 tests): Registration, login, role restrictions, admin moderation, profile updates.
  - `properties` (45 tests): Property creation, room configurations, photo galleries, filter queries.
  - `locations` (26 tests): Geocoding, landmark lookup, Haversine formula, Overpass POI caching.
  - `enquiries` (20 tests): Submission, lifecycle status transitions, WhatsApp URL validation.
  - `core` (15 tests): Landing page, navigation, legal pages, health checks, `seed_demo_data` command.
- **Result**: `146 passed, 0 failures, 0 errors in ~84s`.

---

## Production Deployment Guide

### Recommended Stack
- **Server**: Ubuntu 22.04 LTS (AWS EC2, DigitalOcean Droplet, or Railway)
- **WSGI Server**: Gunicorn with Uvicorn workers
- **Web Server / Reverse Proxy**: Nginx
- **Database**: Managed PostgreSQL 15+
- **Static & Media Files**: AWS S3 or WhiteNoise with Nginx caching

### Deployment Steps

1. **Configure Production Environment (`Backend/.env`)**:
   ```env
   DJANGO_DEBUG=False
   DJANGO_SECRET_KEY=use-a-strong-64-character-random-secret
   DJANGO_ALLOWED_HOSTS=whereismyhostel.com,www.whereismyhostel.com
   DJANGO_CSRF_TRUSTED_ORIGINS=https://whereismyhostel.com,https://www.whereismyhostel.com
   DB_ENGINE=postgresql
   DB_NAME=where_is_my_hostel_prod
   DB_USER=hostel_user
   DB_PASSWORD=strong-database-password
   DB_HOST=db.whereismyhostel.internal
   DB_PORT=5432
   ```

2. **Collect Static Files**:
   ```bash
   cd Backend
   python manage.py collectstatic --noinput
   ```

3. **Gunicorn Systemd Service (`/etc/systemd/system/whereismyhostel.service`)**:
   ```ini
   [Unit]
   Description=Where Is My Hostel Gunicorn Daemon
   After=network.target

   [Service]
   User=deploy
   Group=www-data
   WorkingDirectory=/var/www/WhereisMyHostel/Backend
   ExecStart=/var/www/WhereisMyHostel/Backend/.venv/bin/gunicorn \
             --workers 3 \
             --bind 127.0.0.1:8000 \
             where_is_my_hostel.wsgi:application

   [Install]
   WantedBy=multi-user.target
   ```

4. **Nginx Configuration (`/etc/nginx/sites-available/whereismyhostel`)**:
   ```nginx
   server {
       server_name whereismyhostel.com www.whereismyhostel.com;

       client_max_body_size 10M;

       location /static/ {
           alias /var/www/WhereisMyHostel/Backend/staticfiles/;
           expires 30d;
           add_header Cache-Control "public, no-transform";
       }

       location /media/ {
           alias /var/www/WhereisMyHostel/Backend/media/;
           expires 7d;
       }

       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

5. **SSL Certificate via Let's Encrypt**:
   ```bash
   sudo certbot --nginx -d whereismyhostel.com -d www.whereismyhostel.com
   ```

---

## License

This project is licensed under the MIT License — see the LICENSE file for details.

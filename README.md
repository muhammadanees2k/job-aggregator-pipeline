# Automated Job Aggregator & Scraping Pipeline

A production-deployed Django backend that automatically collects, normalizes, stores, and serves job listings from company career portals. The project demonstrates real-world backend engineering: web scraping, data lifecycle tracking, REST APIs, admin observability, Linux automation, and AWS deployment.

## Overview

This application aggregates active job listings from:

- **Devsinc Careers** — collected through Workable's public job API.
- **Systems Limited Careers** — collected through a Playwright-powered scraper for a dynamic SAP SuccessFactors career portal.

Scraped jobs are stored in MySQL, exposed through Django REST Framework endpoints, displayed on a Django template frontend, and monitored through Django Admin.

## Key Features

- Automated scraping pipeline using **Python, Requests, Playwright, and BeautifulSoup**
- Django management command for repeatable scraper execution
- MySQL-backed job storage with duplicate prevention
- Job lifecycle tracking using `last_seen` and `is_active`
- Date normalization from raw scraped text into sortable date fields
- REST API endpoint with filtering and search support
- Responsive job board frontend
- Django Admin dashboard for scraper logs and job monitoring
- Linux cron automation running every 6 hours
- Production deployment on AWS EC2 using **Nginx + Gunicorn + systemd**
- Static file serving configured for production

## Tech Stack

- **Backend:** Python, Django, Django REST Framework
- **Scraping:** Playwright, BeautifulSoup, Requests
- **Database:** MySQL
- **Deployment:** AWS EC2, Ubuntu, Nginx, Gunicorn, systemd, Linux Cron
- **Frontend:** Django Templates, HTML, CSS

## Architecture

```text
Career Portals
   ↓
Scraper Command: python manage.py scrape_jobs
   ↓
Data Cleaning + Date Normalization
   ↓
MySQL Database
   ↓
Django ORM
   ↓
Django Template UI + REST API + Admin Dashboard
```

Production serving flow:

```text
Browser
   ↓
Nginx :80 / :8000
   ↓
Gunicorn 127.0.0.1:8001
   ↓
Django Application
   ↓
MySQL 127.0.0.1:3306
```

## Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/job-aggregator-pipeline.git
cd job-aggregator-pipeline
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
source venv/bin/activate   # Linux/macOS
# venv\Scripts\activate    # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Playwright browser

```bash
playwright install chromium
```

### 5. Create `.env`

Create a `.env` file in the project root:

```env
DJANGO_SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DB_NAME=job_aggregator
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_HOST=127.0.0.1
DB_PORT=3306
```

Generate a Django secret key if needed:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 6. Run migrations

```bash
python manage.py migrate
```

### 7. Run the scraper

```bash
python manage.py scrape_jobs
```

### 8. Start the development server

```bash
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
http://127.0.0.1:8000/api/jobs/
http://127.0.0.1:8000/admin/
```

## API Usage

List active jobs:

```text
GET /api/jobs/
```

Filter by company:

```text
GET /api/jobs/?company=Devsinc
GET /api/jobs/?company=Systems Limited
```

Search by job title:

```text
GET /api/jobs/?search=Python
```

## Admin Monitoring

Create an admin user:

```bash
python manage.py createsuperuser
```

The Django Admin panel provides:

- Job listing management
- Active/inactive job visibility
- Company/date filters
- Searchable job records
- Scraper execution logs
- Success/failure tracking for scheduled runs

## Production Notes

The project is deployed on AWS EC2 using:

- **Nginx** as the public reverse proxy
- **Gunicorn** as the WSGI application server
- **systemd** for process management
- **cron** for scheduled scraping every 6 hours
- **MySQL** as the persistent data store

Cron command example:

```bash
0 */6 * * * cd /path/to/project && /path/to/venv/bin/python manage.py scrape_jobs >> scraper_cron.log 2>&1
```

## Future Improvements

- Containerize the application with Docker and Docker Compose
- Add automated tests for scraper parsing, date normalization, and API endpoints
- Add GitHub Actions for CI/CD
- Replace cron with Celery + Redis for better task retries and monitoring
- Add structured logging and alerting for scraper failures
- Add HTTPS with a custom domain and Let's Encrypt
- Add pagination metadata and ordering controls to the API
- Add support for more company career portals


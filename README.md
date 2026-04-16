# Enterprise Job Aggregator Pipeline

An autonomous, cloud-native job aggregation engine designed to silently scrape, process, and serve job listings from highly secured enterprise career portals.

This project goes beyond simple web scraping by implementing anti-bot evasion techniques, robust cloud infrastructure, and a fully automated daily pipeline running on an AWS EC2 instance.

## Live Demo & Endpoints

You do not need to configure the project locally to see it in action. The scraper is currently running autonomously on a live AWS EC2 instance.

* **Live Web Interface:** [http://54.153.209.192:8000](http://54.153.209.192:8000) 
  The root URL serves a Django HTML template that dynamically renders the latest scraped job listings from both enterprise portals directly from the MySQL database.
* **REST API Endpoint:** [http://54.153.209.192:8000/api/jobs](http://54.153.209.192:8000/api/jobs) 
  Provides direct JSON access to the aggregated job data, demonstrating proper REST architecture for external frontend or mobile app consumption.

## Tech Stack & Architecture

* **Backend Framework:** Python, Django, Django REST Framework (DRF)
* **Automation & Scraping:** Playwright (Headless Chromium), BeautifulSoup4
* **Database:** MySQL
* **Cloud Infrastructure:** AWS EC2 (t3.micro), Ubuntu Linux
* **DevOps & CI/CD:** Linux Cron Jobs, Systemd Services, Custom Swap Memory Management
* **Environment Management:** Pipenv

## Core Features

* **Advanced Stealth Scraping:** Bypasses enterprise-grade Web Application Firewalls (WAF) like Cloudflare using injected human-mask User-Agents and automation-flag suppression.
* **Fully Autonomous Pipeline:** Utilizes a Linux `cron` daemon to trigger the extraction pipeline every 6 hours without human intervention.
* **Resilient Cloud Deployment:** Runs 24/7 on an AWS EC2 instance. The Django web server is registered as a native Ubuntu `systemd` service, ensuring automatic restarts upon system reboots or unexpected crashes.
* **Smart Database Management:** Automatically sanitizes the MySQL database by comparing new pulls against existing records, updating timestamps, and gracefully deactivating dead or expired job links.
* **Hardware Optimized:** Custom-configured Linux Swap files to prevent Out-Of-Memory (OOM) kernel panics during high-intensity headless browser rendering on a micro-tier server.

## Technical Challenges Conquered

During the development of this pipeline, several production-level challenges were solved:
1. **The IP Reputation Block:** Enterprise career portals instantly blocked data-center IP addresses. Solved by injecting stealth configurations into Playwright to successfully mimic organic traffic.
2. **The "OOM Killer" Crash:** Heavy headless browser operations overwhelmed the server's 1GB RAM limit, causing terminal disconnects. Solved by dropping down to the Linux kernel level to allocate 2GB of SSD storage as emergency Swap memory, stabilizing the server.

## Local Setup & Installation

If you wish to run this pipeline locally, follow these steps:

**1. Clone the repository**

```bash
https://github.com/muhammadanees2k/job-aggregator-pipeline.git
```

**2.  Install Pipenv (if not already installed)**

***On windows:***
```python
pip install pipenv
```

***On Ubuntu/Debian:***
```bash
sudo apt install pipenv
```

**3. Initialize the Pipenv environment and install dependencies**
```python
pipenv install -r requirements.txt
```

**4. Activate the virtual shell**
```python
pipenv shell
```

**5. Install Playwright browser binaries**
```python
playwright install chromium
```

**6. Database Configuration**

Log into your local MySQL instance and create the database:

```sql
CREATE DATABASE job_aggregator_db;
```

**7. Run database migrations**
```python 
python manage.py makemigrations
python manage.py migrate
```

**8. Trigger the scraper manually**
```python
python manage.py scrape_jobs
```

**9. Start the local server**
```python
python manage.py runserver
```


## System Monitoring & Admin Dashboard

This project includes a fully configured Django Admin dashboard designed for production observability. It allows administrators to monitor scraper health, debug network timeouts, and manage job data without accessing the database directly.

### 1. Create an Admin Account
To access the secure dashboard, generate a superuser credential in your terminal:
```bash
python manage.py createsuperuser
```
I will ask for username and password. Provide that in best possible way.

### 2. Access the Dashboard

Start your server (python manage.py runserver) and navigate to:

```python 
http://localhost:8000/admin
```

### 3. Dashboard Features

**Job Management:** View, filter (by company, active status, date), and search through all scraped job listings.

**Scraper Logs (Audit Trail):** A secure, read-only system logging table. It tracks:

1. The exact timestamp of every cron job execution.

2. SUCCESS or FAILED execution states.

3. The total number of new jobs successfully added to the database per run.

4. Detailed Error Tracebacks: If the scraper encounters a WAF block, Cloudflare challenge, or DOM timeout, the exact Python traceback and HTTP response are caught and logged here for easy debugging.

## Future Roadmap

1. Integration of real-time email notifications for users when a new job matches their profile.

2. Building a full REST API suite using Django REST Framework for mobile app consumption.

3. Implementing proxy rotation for even higher scraping resilience.
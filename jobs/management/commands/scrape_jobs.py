import traceback
import re
import requests
from datetime import timedelta
from django.utils import timezone
from django.core.management.base import BaseCommand
from jobs.models import Job, ScraperLog
from playwright.sync_api import sync_playwright, TimeoutError
from bs4 import BeautifulSoup

# ==========================================
# DATE TRANSLATOR ENGINE
# ==========================================
def translate_to_actual_date(date_text):
    today = timezone.now().date()
    if not date_text or date_text == "Unknown":
        return today

    date_text = str(date_text).lower()

    # FORMAT 1: Devsinc Widget API (ISO Format "2026-04-16")
    try:
        match = re.search(r'\d{4}-\d{2}-\d{2}', date_text)
        if match:
            return timezone.datetime.strptime(match.group(), "%Y-%m-%d").date()
    except Exception:
        pass

    # FORMAT 2: Systems Limited ("Posted on 02/17/2026")
    if "posted on" in date_text:
        try:
            match = re.search(r'\d{2}/\d{2}/\d{4}', date_text)
            if match:
                return timezone.datetime.strptime(match.group(), "%m/%d/%Y").date()
        except Exception:
            pass

    # FORMAT 3: Workable Text Fallback ("Posted 2 days ago")
    if "ago" in date_text or "day" in date_text or "month" in date_text:
        try:
            number_match = re.search(r'\d+', date_text)
            number = int(number_match.group()) if number_match else 0
            
            if "day" in date_text:
                return today - timedelta(days=number)
            elif "week" in date_text:
                return today - timedelta(weeks=number)
            elif "month" in date_text:
                return today - timedelta(days=number * 30)
            elif "year" in date_text:
                return today - timedelta(days=number * 365)
        except Exception:
            pass
            
    return today

# ==========================================
# HELPER FUNCTIONS FOR SYSTEMS LIMITED
# ==========================================
def wait_for_ajax_complete(page, max_wait=30):
    for _ in range(max_wait):
        try:
            loading = page.locator(".loading_indicator_layout_static, #overlayMask, #sfOverlayMgr, .loadingText").filter(has_text="Updating...")
            if loading.count() == 0 or not loading.first.is_visible():
                return True
        except Exception:
            pass
        page.wait_for_timeout(1000)
    return False

def set_sf_dropdown(page, dropdown_name, option_text):
    btn = page.locator(f"button[aria-label='{dropdown_name}'], button[title*='{dropdown_name}']").first
    if btn.count() == 0:
        return False
    for attempt in range(15):
        if not btn.is_disabled():
            break
        page.wait_for_timeout(1000)
    else:
        return False

    btn.click(force=True)
    page.wait_for_timeout(1500)
    option_locator = page.locator(f"text='{option_text}'").last

    try:
        option_locator.wait_for(state="visible", timeout=8000)
        option_locator.click(force=True)
    except TimeoutError:
        page.keyboard.press("Escape")
        return False

    page.wait_for_timeout(1000)
    page.keyboard.press("Escape")
    page.wait_for_timeout(1500)
    wait_for_ajax_complete(page)
    return True

def has_next_page(page):
    try:
        next_arrows = page.locator("li.sfPaginatorArrowContainer.next")
        if next_arrows.count() == 0:
            return False
        classes = next_arrows.first.get_attribute("class") or ""
        return "disabledArrow" not in classes and "disabled" not in classes
    except Exception:
        return False

def click_next_page(page):
    try:
        old_title = ""
        try:
            old_title = page.locator("a.jobTitle").first.inner_text(timeout=2000)
        except Exception:
            pass
        next_link = page.locator("li.sfPaginatorArrowContainer.next a.paginationArrow").first
        next_link.click(force=True)
        page.wait_for_timeout(2000)
        wait_for_ajax_complete(page)
        if old_title:
            for _ in range(15):
                try:
                    new_title = page.locator("a.jobTitle").first.inner_text(timeout=2000)
                    if new_title != old_title:
                        break
                except Exception:
                    pass
                page.wait_for_timeout(1000)
        page.wait_for_timeout(1500)
        return True
    except Exception:
        return False

# ==========================================
# DJANGO MANAGEMENT COMMAND
# ==========================================
class Command(BaseCommand):
    help = 'Scrapes job listings from Devsinc and Systems Limited'

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting production scraper pipeline...")
        all_jobs = []
        total_new_added = 0

        try:
            # 1. SCRAPE DEVSINC (Public Widget API Method)
            self.stdout.write("--> Scraping Devsinc via Public Stealth API...")
            try:
                devsinc_jobs = self.scrape_devsinc_api()
                all_jobs.extend(devsinc_jobs)
                self.stdout.write(self.style.SUCCESS(f"Found {len(devsinc_jobs)} Devsinc jobs."))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Devsinc Scraper Failed: {e}"))

            # 2. SCRAPE SYSTEMS LIMITED (Playwright Method)
            self.stdout.write("--> Scraping Systems Limited via Playwright...")
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(
                        headless=True, 
                        slow_mo=300,
                        args=["--disable-blink-features=AutomationControlled"]
                    )
                    context = browser.new_context(
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                        viewport={"width": 1920, "height": 1080}
                    )
                    context.route("**/*.{png,jpg,jpeg,webp,gif,svg,mp4,webm}", lambda route: route.abort())

                    systems_jobs = self.scrape_systems_limited(context)
                    all_jobs.extend(systems_jobs)
                    self.stdout.write(self.style.SUCCESS(f"Found {len(systems_jobs)} Systems Limited jobs."))

                    context.close()
                    browser.close()
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Systems Limited Scraper Failed: {e}"))

            # 3. DATABASE OPERATIONS
            total_new_added = self.save_to_database(all_jobs)
            self.clean_up_dead_links()

            # 4. LOG SUCCESS
            ScraperLog.objects.create(
                status='SUCCESS',
                message=f'Successfully finished scraping. Found {len(all_jobs)} total active jobs.',
                jobs_added=total_new_added
            )
            self.stdout.write(self.style.SUCCESS('Pipeline completed and logged successfully.'))

        except Exception as e:
            error_message = f"Critical Error: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
            ScraperLog.objects.create(status='FAILED', message=error_message, jobs_added=0)
            self.stderr.write(self.style.ERROR('Pipeline failed! Error saved to database.'))

    def scrape_devsinc_api(self):
        # Workable's officially sanctioned public GET endpoints for widgets and job boards.
        # These bypass Cloudflare's strict POST rate-limits entirely.
        primary_url = "https://www.workable.com/api/accounts/devsinc-17?details=false"
        fallback_url = "https://apply.workable.com/api/v1/widget/accounts/devsinc-17"
        COMPANY_NAME = "Devsinc"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        try:
            # Execute a clean GET request with no complex payloads
            response = requests.get(primary_url, headers=headers, timeout=20)
            
            # If the primary fails, Workable's widget API is the secondary backup
            if response.status_code != 200:
                self.stdout.write(self.style.WARNING(f"--> Primary API failed ({response.status_code}). Trying Fallback Widget API..."))
                response = requests.get(fallback_url, headers=headers, timeout=20)
                
            if response.status_code != 200:
                raise Exception(f"Both public APIs blocked. Status: {response.status_code}. Response: {response.text}")
                
            data = response.json()
            jobs_data = []
            
            # Workable returns the list either directly or wrapped in a 'jobs' dictionary key
            if isinstance(data, dict):
                jobs_list = data.get("jobs", data.get("results", []))
            elif isinstance(data, list):
                jobs_list = data
            else:
                jobs_list = []
                
            for job in jobs_list:
                job_title = job.get("title")
                
                # Extract the apply link (fallback to reconstructing it via the shortcode)
                apply_link = job.get("url")
                if not apply_link and job.get("shortcode"):
                    apply_link = f"https://apply.workable.com/devsinc-17/j/{job.get('shortcode')}/"
                    
                if not job_title or not apply_link:
                    continue
                    
                # Extract the date (Comes back as ISO format e.g., 2026-04-16T09:23:45Z)
                raw_date = job.get("published_on") or job.get("created_at") or "Unknown"
                posted_date = str(raw_date)[:10] if raw_date != "Unknown" else "Unknown"
                
                jobs_data.append({
                    "job_title": job_title,
                    "company": COMPANY_NAME,
                    "posted_date": posted_date,
                    "apply_link": apply_link,
                })
                
            return jobs_data
            
        except Exception as e:
            raise Exception(f"Stealth API Error: {str(e)}")

    def scrape_systems_limited(self, context):
        URL = "https://career55.sapsf.eu/career?company=systemvent&lang=en_US"
        COMPANY_NAME = "Systems Limited"
        BASE_URL = "https://career55.sapsf.eu"
        jobs_data = []

        page = context.new_page()
        page.goto(URL, wait_until="domcontentloaded", timeout=90000)
        page.wait_for_selector("#careerJobSearchContainer", timeout=60000)
        
        for attempt in range(30):
            if page.locator("button:has-text('Search Jobs')").count() > 0:
                break
            page.wait_for_timeout(1000)
        page.wait_for_timeout(3000)

        set_sf_dropdown(page, "Country", "Pakistan")
        set_sf_dropdown(page, "City", "Islamabad")

        try:
            search_btn = page.locator("button:has-text('Search Jobs')").first
            search_btn.click(force=True)
            page.wait_for_timeout(3000)
            wait_for_ajax_complete(page)
            page.wait_for_selector("tr.jobResultItem", timeout=20000)
        except Exception:
            pass

        while True:
            html = page.content()
            soup = BeautifulSoup(html, "html.parser")
            job_items = soup.select("tr.jobResultItem")

            for job in job_items:
                title_el = job.select_one("a.jobTitle")
                job_title = title_el.get_text(strip=True) if title_el else None

                apply_link = None
                if title_el and title_el.get("href"):
                    href = title_el["href"]
                    apply_link = BASE_URL + href if href.startswith("/") else href
                    
                    if "career_job_req_id=" in apply_link:
                        req_id = apply_link.split("career_job_req_id=")[1].split("&")[0]
                        apply_link = f"https://career55.sapsf.eu/career?company=systemvent&career_ns=job_listing&career_job_req_id={req_id}"

                posted_date = None
                note_section = job.select_one("div.noteSection")
                if note_section:
                    note_text = note_section.get_text(" ", strip=True)
                    if "Posted on" in note_text:
                        try:
                            after_posted = note_text.split("Posted on")[1].strip()
                            date_str = after_posted.split(" -")[0].strip()
                            if not date_str:
                                date_str = after_posted.split("-")[0].strip()
                            date_str = date_str.strip().split()[0] if date_str else ""
                            if date_str:
                                posted_date = f"Posted on {date_str}"
                        except Exception:
                            pass
                
                if not apply_link or not job_title:
                    continue

                jobs_data.append({
                    "job_title": job_title,
                    "company": COMPANY_NAME,
                    "posted_date": posted_date,
                    "apply_link": apply_link.strip(),
                })

            if has_next_page(page):
                if not click_next_page(page):
                    break
            else:
                break

        page.close()
        return jobs_data

    def save_to_database(self, jobs_data):
        self.stdout.write("--> Translating dates and saving to Database...")
        new_jobs_count = 0
        updated_jobs_count = 0

        for data in jobs_data:
            actual_date = translate_to_actual_date(data['posted_date'])

            job, created = Job.objects.update_or_create(
                apply_link=data['apply_link'],
                defaults={
                    'company': data['company'],
                    'job_title': data['job_title'],
                    'posted_date_raw': data['posted_date'] or "Unknown",
                    'parsed_date': actual_date,
                    'last_seen': timezone.now(),
                    'is_active': True
                }
            )
            if created:
                new_jobs_count += 1
            else:
                updated_jobs_count += 1

        self.stdout.write(self.style.SUCCESS(f"Saved: {new_jobs_count} new jobs added. {updated_jobs_count} existing jobs updated."))
        return new_jobs_count

    def clean_up_dead_links(self):
        self.stdout.write("--> Cleaning up dead links...")
        yesterday = timezone.now() - timezone.timedelta(hours=24)
        
        stale_jobs = Job.objects.filter(last_seen__lt=yesterday, is_active=True)
        stale_count = stale_jobs.count()
        
        stale_jobs.update(is_active=False)
        self.stdout.write(self.style.SUCCESS(f"Deactivated {stale_count} old/removed jobs."))
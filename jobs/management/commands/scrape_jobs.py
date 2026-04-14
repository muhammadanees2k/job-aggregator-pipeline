import traceback
from django.core.management.base import BaseCommand
from django.utils import timezone
from jobs.models import Job
from playwright.sync_api import sync_playwright, TimeoutError
from bs4 import BeautifulSoup

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
        self.stdout.write("Starting scraper pipeline...")
        all_jobs = []

        with sync_playwright() as p:
            # HEADLESS MUST BE TRUE FOR LINUX DEPLOYMENT
            browser = p.chromium.launch(headless=True, slow_mo=300)

            # 1. Scrape Devsinc
            self.stdout.write("--> Scraping Devsinc...")
            try:
                devsinc_jobs = self.scrape_devsinc(browser)
                all_jobs.extend(devsinc_jobs)
                self.stdout.write(self.style.SUCCESS(f"Found {len(devsinc_jobs)} Devsinc jobs."))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Devsinc Scraper Failed: {e}"))
                traceback.print_exc()

            # 2. Scrape Systems Limited
            self.stdout.write("--> Scraping Systems Limited...")
            try:
                systems_jobs = self.scrape_systems_limited(browser)
                all_jobs.extend(systems_jobs)
                self.stdout.write(self.style.SUCCESS(f"Found {len(systems_jobs)} Systems Limited jobs."))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Systems Limited Scraper Failed: {e}"))
                traceback.print_exc()

            browser.close()

        # 3. Database Operations
        self.save_to_database(all_jobs)
        self.clean_up_dead_links()

    def scrape_devsinc(self, browser):
        URL = "https://apply.workable.com/devsinc-17/"
        COMPANY_NAME = "Devsinc"
        page = browser.new_page()
        page.goto(URL, wait_until="networkidle")
        page.wait_for_selector("[data-ui='job']", timeout=15000)

        try:
            accept_btn = page.get_by_role("button", name="Accept all")
            if accept_btn.is_visible():
                accept_btn.click()
                page.wait_for_timeout(1000)
        except Exception:
            pass

        while True:
            current_jobs = page.locator("[data-ui='job']").count()
            try:
                show_more_btn = page.get_by_role("button", name="Show more")
                if not show_more_btn.is_visible():
                    break
                show_more_btn.scroll_into_view_if_needed()
                page.wait_for_timeout(1000)
                show_more_btn.click(force=True)
                page.wait_for_function(
                    f"document.querySelectorAll(\"[data-ui='job']\").length > {current_jobs}",
                    timeout=10000
                )
            except TimeoutError:
                break
            except Exception:
                break

        html = page.content()
        page.close()

        soup = BeautifulSoup(html, "html.parser")
        job_items = soup.select("[data-ui='job']")
        jobs_data = []

        for job in job_items:
            title_el = job.select_one("[data-ui='job-title'] span, [data-ui='job-title']")
            job_title = title_el.get_text(strip=True) if title_el else None

            a_el = job.select_one("a[href]")
            apply_link = a_el["href"] if a_el else None
            if apply_link and apply_link.startswith("/"):
                apply_link = "https://apply.workable.com" + apply_link

            posted_date = None
            for line in job.stripped_strings:
                if line.lower().startswith("posted"):
                    posted_date = line
                    break

            # Skip bad records
            if not apply_link or not job_title:
                continue

            jobs_data.append({
                "job_title": job_title,
                "company": COMPANY_NAME,
                "posted_date": posted_date,
                "apply_link": apply_link,
            })

        return jobs_data

    def scrape_systems_limited(self, browser):
        URL = "https://career55.sapsf.eu/career?company=systemvent&lang=en_US"
        COMPANY_NAME = "Systems Limited"
        BASE_URL = "https://career55.sapsf.eu"
        jobs_data = []

        page = browser.new_page()
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
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
            # Scrape Current Page Logic integrated here
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
                
                # Skip bad records
                if not apply_link or not job_title:
                    continue

                jobs_data.append({
                    "job_title": job_title,
                    "company": COMPANY_NAME,
                    "posted_date": posted_date,
                    "apply_link": apply_link,
                })

            if has_next_page(page):
                if not click_next_page(page):
                    break
            else:
                break

        page.close()
        return jobs_data

    def save_to_database(self, jobs_data):
        self.stdout.write("--> Saving to Database...")
        new_jobs_count = 0
        updated_jobs_count = 0

        for data in jobs_data:
            job, created = Job.objects.update_or_create(
                apply_link=data['apply_link'],
                defaults={
                    'company': data['company'],
                    'job_title': data['job_title'],
                    'posted_date_raw': data['posted_date'] or "Unknown",
                    'last_seen': timezone.now(),
                    'is_active': True
                }
            )
            if created:
                new_jobs_count += 1
            else:
                updated_jobs_count += 1

        self.stdout.write(self.style.SUCCESS(f"Saved: {new_jobs_count} new jobs added. {updated_jobs_count} existing jobs updated."))

    def clean_up_dead_links(self):
        self.stdout.write("--> Cleaning up dead links...")
        yesterday = timezone.now() - timezone.timedelta(hours=24)
        
        # Find jobs not seen in the last 24 hours
        stale_jobs = Job.objects.filter(last_seen__lt=yesterday, is_active=True)
        stale_count = stale_jobs.count()
        
        # Deactivate them
        stale_jobs.update(is_active=False)
        self.stdout.write(self.style.SUCCESS(f"Deactivated {stale_count} old/removed jobs."))
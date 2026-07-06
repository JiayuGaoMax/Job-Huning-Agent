import requests
from openai import OpenAI
from bs4 import BeautifulSoup
from ollama import chat
import os
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import fitz  # PyMuPDF
import time
from dotenv import load_dotenv
from datetime import datetime,timedelta
from google import genai
import smtplib
from email.message import EmailMessage
import re
import json
from LLM_Job_Library import extract_job_postings, rank_jobs_with_Gemini # type: ignore
from JobData import CAREER_SITES,UNWANTED_JOB_KEYWORDS,UNWANTED_WEB_WORDS
load_dotenv()

# 1. Setup email credentials and configuration
SENDER_EMAIL = "galaxyjiayu@gmail.com"
APP_PASSWORD = os.getenv("EMAIL_PASSWORD")  # Your 16-character app password
RECEIVER_EMAIL = "galaxyjiayu@gmail.com"


Gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


headers = {"User-Agent": "Mozilla/5.0"}


def load_resume(pdf_path):
    doc = fitz.open(pdf_path)

    text = ""
    for page in doc:
        text += page.get_text()

    doc.close()
    return text


resume_text = load_resume(r"Max_Gao_Resume.pdf")


def get_html_requests(url):
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.text


def get_html_playwright(url: str, timeout: int = 60000) -> str:
    """
    General Playwright scraper for dynamic career pages.
    Works better for Workday, Oracle, Teamtailor, Lever, UKG, and custom JS sites.
    Returns final rendered HTML.
    """

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )

        context = browser.new_context(
            viewport={"width": 1600, "height": 1200},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )

        page = context.new_page()

        try:
            page.goto(url, wait_until="networkidle", timeout=timeout)

            # Try to let dynamic content load
            try:
                page.wait_for_load_state("networkidle", timeout=15000)
            except PlaywrightTimeoutError:
                pass

            page.wait_for_timeout(3000)

            # Scroll to trigger lazy-loaded jobs
            for _ in range(5):
                page.mouse.wheel(0, 2000)
                page.wait_for_timeout(1000)

            # Try common job-card selectors, but don't fail if absent
            selectors = [
                "a[href*='job']",
                "a[href*='jobs']",
                "a[href*='careers']",
                "[data-automation-id]",
                "[data-testid]",
                ".job",
                ".jobs",
                ".posting",
                ".opening",
                "article",
                "li",
            ]

            for selector in selectors:
                try:
                    if page.locator(selector).count() > 0:
                        page.wait_for_timeout(1000)
                        break
                except Exception:
                    pass

            html = page.content()
            return html

        finally:
            context.close()
            browser.close()


def save_report(all_results, filename="job_report.md"):
    with open(filename, "w", encoding="utf-8") as f:
        f.write("# AI Job Match Report\n\n")
        f.write(all_results)

    print(f"Saved report to {filename}")

def normalize_date_simple(raw_date, today):
    if not raw_date:
        return None

    raw = raw_date.lower().strip()

    # Unknown dates
    if raw in ["not found", "unknown", "n/a", ""]:
        return None

    # Relative dates
    if "today" in raw:
        return today

    if "yesterday" in raw:
        return today - timedelta(days=1)

    # X Days Ago (handles "30+ Days Ago")
    m = re.search(r"(\d+)\+?\s*day[s]?\s+ago", raw)
    if m:
        days = int(m.group(1))
        return today - timedelta(days=days)

    # X Weeks Ago
    m = re.search(r"(\d+)\+?\s*week[s]?\s+ago", raw)
    if m:
        weeks = int(m.group(1))
        return today - timedelta(weeks=weeks)

    # Absolute dates
    formats = [
        "%b %d, %Y",      # Jun 30, 2026
        "%B %d, %Y",      # June 30, 2026
        "%Y-%m-%d",       # 2026-06-30
        "%m/%d/%Y",       # 06/30/2026
    ]

    for fmt in formats:
        try:
            return datetime.strptime(raw_date.strip(), fmt).date()
        except ValueError:
            pass

    return None
def html_to_text(html):
    soup = BeautifulSoup(html, "html.parser")

    # Remove useless tags
    for tag in soup(
        ["script", "style", "noscript", "svg", "img", "footer", "header", "nav", "form"]
    ):
        tag.decompose()

    text = soup.get_text("\n", strip=True)


    cleaned = []

    for line in text.splitlines():
        line = re.sub(r"\s+", " ", line).strip()

        if not line:
            continue

        if len(line) < 2:
            continue

        if any(word in line.lower() for word in UNWANTED_WEB_WORDS):
            continue

        cleaned.append(line)

    return "\n".join(cleaned)



def parse_jobs(text):
    jobs = []

    blocks = re.split(
        r"(?=Company\s*:)",
        text,
        flags=re.IGNORECASE
    )

    for block in blocks:
        if not re.search(r"Company\s*:", block, re.IGNORECASE):
            continue

        def get_field(label):
            match = re.search(
                rf"^{re.escape(label)}\s*:\s*(.*)$",
                block,
                flags=re.IGNORECASE | re.MULTILINE
            )

            if match:
                return match.group(1).strip()

            return "Not found"

        job = {
            "company": get_field("Company"),
            "title": get_field("Job Title"),
            "location": get_field("Location"),
            "posting_date": get_field("Posting Date"),
            "department": get_field("Department"),
            "url": get_field("Job URL")
        }

        if job["title"] != "Not found":
            jobs.append(job)

    return jobs

def filter_recent_jobs(jobs, days=7):
    cutoff = datetime.today().date() - timedelta(days=days)

    filtered = []

    for job in jobs:
        date = job.get("posting_date")

        # Keep jobs with unknown dates
        if date is None:
            filtered.append(job)
            continue

        if date >= cutoff:
            filtered.append(job)

    return filtered



def filter_Unwanted_jobs(jobs):
    filtered = []

    for job in jobs:
        text = (
            f"{job.get('title','')} "
            f"{job.get('department','')}"
        ).lower()

        if any(keyword in text for keyword in UNWANTED_JOB_KEYWORDS):
            continue

        filtered.append(job)

    return filtered

start_time = time.perf_counter()
all_results = ""
htmltextAllCompany = ""
today = datetime.today().date()

# Parsing the webpage
for company, info in CAREER_SITES.items():

    print(f"\nChecking {company}...")

    try:
        if info["method"] == "requests":
            html = get_html_requests(info["url"])
        elif info["method"] == "playwright":
            html = get_html_playwright(info["url"])
        else:
            raise ValueError("Unknown method")

        text = html_to_text(html)

        htmltextAllCompany += (
            f"\n\n"
            f"{'=' * 80}\n"
            f"COMPANY: {company}\n"
            f"CAREER PAGE: {info['url']}\n"
            f"{'=' * 80}\n\n"
            f"{text}\n"
            f"\n{'-' * 80}\n"
            f"END OF {company}\n"
            f"{'-' * 80}\n"
        )

        print(f"Extracted {len(text)} characters from {company}")
        # extracting job using LLM
        result = extract_job_postings(
            company=company, url=info["url"], text=text, model="gemma3:12b"
        )

        all_results += f"\n\n========== {company} ==========\n"
        all_results += result
    except Exception as e:
        all_results += f"\n\n========== {company} ==========\n"
        all_results += f"Error checking {company}: {e}"


save_report(htmltextAllCompany, "PostExtractHTMLText.md")
save_report(all_results, "LocalLLMExtractJob.md")
alljJobsJson=parse_jobs(all_results)

save_report(str(alljJobsJson), "FilteredJobList.md")
alljJobsJson=filter_Unwanted_jobs(alljJobsJson)
for job in alljJobsJson:
    job["posting_date_raw"] = job.get("posting_date")
    job["posting_date"] = normalize_date_simple(job.get("posting_date", ""), today)
save_report(htmltextAllCompany, "PostExtractHTMLText.md")
save_report(all_results, "LocalLLMExtractJob.md")
print("\n\nFINAL RESULTS")  
jobAfterPostDateFilterJson=filter_recent_jobs(alljJobsJson,3)
jobAfterPostDateFilterJsonStr=jobs_string = json.dumps(
    jobAfterPostDateFilterJson,
    indent=2,
    ensure_ascii=False,
    default=str
)

ultimate_summary = rank_jobs_with_Gemini(
    Gemini_client=Gemini_client, jobs_text=jobAfterPostDateFilterJsonStr, resume_text=resume_text
)

msg = EmailMessage()
msg["Subject"] = "Job Hunting Report"
msg["From"] = SENDER_EMAIL
msg["To"] = RECEIVER_EMAIL
msg.set_content(ultimate_summary)


try:

    for i in range(1):

        # Connect to Gmail's SMTP server (Port 587 for STARTTLS)
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()  # Encrypt the connection securely
            server.login(SENDER_EMAIL, APP_PASSWORD)  # Authenticate
            server.send_message(msg)  # Send the constructed message

    print("✅ Email sent successfully!")

except Exception as e:
    print(f" An error occurred: {e}")
save_report(all_results, "ultimate_summary.md")

end_time = time.perf_counter()

elapsed = end_time - start_time

print(f"\nTotal runtime: {elapsed:.2f} seconds")

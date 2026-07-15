import requests
from openai import OpenAI
import traceback 
from ollama import chat
import os
from PlaywrightLib import get_html_playwright,html_to_text
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
from pathlib import Path
from JobData import CAREER_SITES,UNWANTED_JOB_KEYWORDS,UNWANTED_WEB_WORDS,PEOPLE, PersonProfile
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





def get_html_requests(url):
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.text





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


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def safe_folder_name(name: str) -> str:
    return (
        name.strip()
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
        .replace(":", "_")
    )


def get_person_output_dir(person: PersonProfile) -> Path:
    person_dir = OUTPUT_DIR / safe_folder_name(person.name)
    person_dir.mkdir(parents=True, exist_ok=True)
    return person_dir


def save_person_report(content, person: PersonProfile, filename: str):
    person_dir = get_person_output_dir(person)
    file_path = person_dir / filename

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(str(content))

    print(f"Saved {person.name} report to {file_path}")
    return file_path


def send_email_report(subject: str, body: str, receiver_email: str):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SENDER_EMAIL
    msg["To"] = receiver_email
    msg.set_content(body)

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(SENDER_EMAIL, APP_PASSWORD)
        server.send_message(msg)


def run_one_person_full_report(person: PersonProfile):
    person_start_time = time.perf_counter()
    today = datetime.today().date()

    print("\n" + "=" * 80)
    print(f"STARTING REPORT FOR: {person.name}")
    print("=" * 80)

    htmltextAllCompany = ""
    all_results = ""

    try:
        resume_path = BASE_DIR / person.resume_file

        if not resume_path.exists():
            raise FileNotFoundError(f"Resume not found: {resume_path}")

        resume_text = load_resume(str(resume_path))

        save_person_report(
            f"Resume loaded successfully:\n{resume_path}",
            person,
            "ResumeLoaded.txt"
        )

        # 1. Go over all websites for this person
        for company, info in person.career_sites.items():
            print(f"\nChecking {company} for {person.name}...")

            try:
                if info["method"] == "requests":
                    html = get_html_requests(info["url"])

                elif info["method"] == "playwright":
                    html = get_html_playwright(info["url"])

                else:
                    raise ValueError(f"Unknown method: {info['method']}")

                text = html_to_text(html, UNWANTED_WEB_WORDS)

                htmltextAllCompany += (
                    f"\n\n"
                    f"{'=' * 80}\n"
                    f"PERSON: {person.name}\n"
                    f"COMPANY: {company}\n"
                    f"CAREER PAGE: {info['url']}\n"
                    f"{'=' * 80}\n\n"
                    f"{text}\n"
                    f"\n{'-' * 80}\n"
                    f"END OF {company}\n"
                    f"{'-' * 80}\n"
                )

                print(f"Extracted {len(text)} characters from {company}")

                result = extract_job_postings(
                    company=company,
                    url=info["url"],
                    text=text,
                    model=person.extractor_model
                )

                all_results += f"\n\n========== {company} ==========\n"
                all_results += result

            except Exception as company_error:
                error_text = (
                    f"Error checking {company} for {person.name}\n"
                    f"Error Type: {type(company_error).__name__}\n"
                    f"Error: {company_error}\n\n"
                    f"{traceback.format_exc()}"
                )

                print(error_text)

                all_results += f"\n\n========== {company} ==========\n"
                all_results += error_text

        # 2. Save raw reports for this person
        save_person_report(
            htmltextAllCompany,
            person,
            "PostExtractHTMLText.md"
        )

        save_person_report(
            all_results,
            person,
            "LocalLLMExtractJob.md"
        )

        # 3. Parse jobs
        all_jobs_json = parse_jobs(all_results)

        save_person_report(
            json.dumps(
                all_jobs_json,
                indent=2,
                ensure_ascii=False,
                default=str
            ),
            person,
            "AllParsedJobs.json"
        )

        # 4. Remove unwanted jobs
        all_jobs_json = filter_Unwanted_jobs(all_jobs_json)

        # 5. Normalize posting dates
        for job in all_jobs_json:
            job["posting_date_raw"] = job.get("posting_date")
            job["posting_date"] = normalize_date_simple(
                job.get("posting_date", ""),
                today
            )

        save_person_report(
            json.dumps(
                all_jobs_json,
                indent=2,
                ensure_ascii=False,
                default=str
            ),
            person,
            "FilteredJobList.json"
        )

        # 6. Keep recent jobs only
        job_after_post_date_filter_json = filter_recent_jobs(
            all_jobs_json,
            person.recent_days
        )

        job_after_post_date_filter_json_str = json.dumps(
            job_after_post_date_filter_json,
            indent=2,
            ensure_ascii=False,
            default=str
        )

        save_person_report(
            job_after_post_date_filter_json_str,
            person,
            "RecentFilteredJobs.json"
        )

        # 7. Rank jobs against this person's resume
        print(f"\nRanking jobs for {person.name}...")

        ultimate_summary = rank_jobs_with_Gemini(
            Gemini_client=Gemini_client,
            jobs_text=job_after_post_date_filter_json_str,
            resume_text=resume_text
        )

        save_person_report(
            ultimate_summary,
            person,
            "ultimate_summary.md"
        )

        # 8. Send email to this person
        send_email_report(
            subject=f"Job Hunting Report - {person.name}",
            body=ultimate_summary,
            receiver_email=person.receiver_email
        )

        elapsed = time.perf_counter() - person_start_time

        status_text = (
            f"SUCCESS\n"
            f"Person: {person.name}\n"
            f"Runtime: {elapsed:.2f} seconds\n"
            f"Parsed jobs after unwanted filter: {len(all_jobs_json)}\n"
            f"Recent jobs: {len(job_after_post_date_filter_json)}\n"
        )

        print(status_text)

        save_person_report(
            status_text,
            person,
            "run_status.txt"
        )

        return {
            "person": person.name,
            "success": True,
            "error": None,
            "runtime_seconds": elapsed,
            "recent_jobs_count": len(job_after_post_date_filter_json)
        }

    except Exception as error:
        elapsed = time.perf_counter() - person_start_time

        error_text = (
            f"FAILED\n"
            f"Person: {person.name}\n"
            f"Runtime: {elapsed:.2f} seconds\n"
            f"Error Type: {type(error).__name__}\n"
            f"Error: {error}\n\n"
            f"{traceback.format_exc()}"
        )

        print(error_text)

        save_person_report(
            error_text,
            person,
            "report_error.md"
        )

        return {
            "person": person.name,
            "success": False,
            "error": str(error),
            "runtime_seconds": elapsed,
            "recent_jobs_count": 0
        }


def main():
    start_time = time.perf_counter()

    print("\n" + "=" * 80)
    print("DAILY JOB HUNTING REPORT STARTED")
    print(f"People count: {len(PEOPLE)}")
    print("=" * 80)

    if not APP_PASSWORD:
        raise ValueError("EMAIL_PASSWORD is missing from .env file")

    if not os.getenv("GEMINI_API_KEY"):
        raise ValueError("GEMINI_API_KEY is missing from .env file")

    all_run_results = []

    for person in PEOPLE:
        result = run_one_person_full_report(person)
        all_run_results.append(result)

    save_report(
        json.dumps(
            all_run_results,
            indent=2,
            ensure_ascii=False,
            default=str
        ),
        "AllPeopleRunResults.json"
    )

    elapsed = time.perf_counter() - start_time

    print("\n" + "=" * 80)
    print("ALL REPORTS FINISHED")
    print(f"Total runtime: {elapsed:.2f} seconds")
    print("=" * 80)

    print(
        json.dumps(
            all_run_results,
            indent=2,
            ensure_ascii=False,
            default=str
        )
    )


if __name__ == "__main__":
    try:
        main()

    except Exception as e:
        print("\nPROGRAM FAILED")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error: {e}")
        print(traceback.format_exc())

        try:
            save_report(
                traceback.format_exc(),
                "program_error.md"
            )
        except Exception:
            pass

        input("\nPress Enter to close...")


start_time = time.perf_counter()

end_time = time.perf_counter()

elapsed = end_time - start_time

print(f"\nTotal runtime: {elapsed:.2f} seconds")

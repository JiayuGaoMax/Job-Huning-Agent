#LLM Job Library
import requests
from openai import OpenAI
from bs4 import BeautifulSoup
from ollama import chat
import os
from playwright.sync_api import sync_playwright
import fitz  # PyMuPDF
import time
import random
from dotenv import load_dotenv
from datetime import datetime
from google import genai
import smtplib
from email.message import EmailMessage
import re

load_dotenv()
Gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def extract_job_postings(company, url, text, model="qwen2.5-coder:7b"):
    prompt = f"""
You are a strict job posting extractor.

Company: {company}
Career page URL: {url}

Extract ONLY real job postings from the career page text.

Rules:
- Do NOT give recommendations.
- Do NOT explain reasoning.
- Do NOT invent jobs.
- Do NOT filter by IT.
- Do NOT filter by date.
- Use only information from the text.
- If no jobs are found, return exactly: No jobs found.

Return only this format for each job:

Company:
Job Title:
Location:
Posting Date:
Department:
Job URL:

If a field is missing, write "Not found" on that field.

Career page text:
{text}
"""

    response = chat(
        model=model,
        messages=[
            {"role": "user", "content": prompt}
        ],
    options={
        "temperature": 0,
        "num_ctx": 16384
    }
    )

    return response.message.content




def extract_job_postings_gemini(company, url, text, model="gemini-2.5-flash"):
    prompt = f"""
You are a strict job posting extractor.

Company: {company}
Career page URL: {url}

Extract ONLY real job postings from the career page text.

Rules:
- Do NOT analyze resume fit.
- Do NOT give recommendations.
- Do NOT explain reasoning.
- Do NOT invent jobs.
- Do NOT filter by IT.
- Do NOT filter by date.
- Use only information from the text.
- If no jobs are found, return exactly: No jobs found.

Return only this format for each job:

Company:
Job Title:
Location:
Posting Date:
Department:
Job URL:

If a field is missing, write "Not found".

Career page text:
{text}
"""

    response = Gemini_client.models.generate_content(
        model=model,
        contents=prompt
    )

    return response.text

def rank_jobs_with_chatgpt(openai_client, jobs_text, resume_text):
    prompt = f"""
You are a strict job ranking agent.

RULES:
- Use ONLY the jobs provided below.
- Do NOT invent companies.
- Do NOT invent job titles.
- Do NOT change dates, locations, or URLs.
- Rank newest IT/software/data/cybersecurity/technical jobs first.
- Then rank by resume fit.
- If a job is not in the input, do not include it.

Candidate resume:
{resume_text}

Jobs:
{jobs_text}

Return a Markdown report:

# Best Jobs To Check First

For each job:
- Rank
- Company
- Job Title
- Posting Date
- Location
- URL
- Match Score 0-100
- Why it fits
- Apply suggestion

# Lower Priority Jobs
"""

    response = openai_client.responses.create(
        model="gpt-5",
        input=prompt
    )

    return response.output_text




def rank_jobs_with_Gemini(Gemini_client, jobs_text, resume_text, max_retries=3):
    prompt = f"""
You are a strict job ranking agent.

RULES:
- Use ONLY the jobs provided below.
- Do NOT invent companies.
- Do NOT invent job titles.
- Do NOT change dates, locations, or URLs.
- Rank newest IT/software/data/cybersecurity/technical jobs first.
- Then rank by resume fit.
- If a job is not in the input, do not include it.

Candidate resume:
{resume_text}

Jobs:
{jobs_text}

Return a Markdown report:

# Best Jobs To Check First

For each job:
- Rank
- Company
- Job Title
- Posting Date
- Location
- URL
- Match Score 0-100
- Why it fits
- Apply suggestion

# Lower Priority Jobs
"""

    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            response = Gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )

            if response and response.text and response.text.strip():
                return response.text

            raise ValueError("Gemini returned empty response.")

        except Exception as e:
            last_error = e
            wait_time = (2 ** attempt) + random.uniform(0, 1)

            print(f"Gemini attempt {attempt} failed: {e}")

            if attempt < max_retries:
                print(f"Retrying in {wait_time:.1f} seconds...")
                time.sleep(wait_time)

    return f"# Gemini Ranking Failed\n\nError: {last_error}"
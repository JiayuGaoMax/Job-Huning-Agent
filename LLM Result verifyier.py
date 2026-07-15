#LLM Result verifyier 
from google import genai
from dotenv import load_dotenv
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
load_dotenv()

Gemini_client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

def read_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def verify_local_llm_extract_with_gemini(gemini_client, extracted_file, source_file):
    extracted_jobs = read_file(extracted_file)
    source_text = read_file(source_file)

    prompt = f"""
You are a strict job extraction verifier.

Task:
Compare the local LLM extracted job list against the original scraped career page text.

Rules:
- Use ONLY the source text to verify.
- Do NOT invent jobs.
- Do NOT add jobs unless they are clearly present in the source text.
- Check whether each extracted job exists in the source text.
- Check whether company, title, location, posting date, department, and URL are correct.
- Identify missing jobs that are clearly present in the source text.
- Identify hallucinated jobs that are not present in the source text.
- Identify incorrect fields.

Return a Markdown report with:

# Verification Summary

## Correctly Extracted Jobs

## Incorrect / Suspicious Jobs

## Missing Jobs From Source

## Field Corrections Needed

## Overall Accuracy Score 0-100

Extracted job list:
{extracted_jobs}

Original source text:
{source_text}
"""

    response = gemini_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    return response.text



verification_report = verify_local_llm_extract_with_gemini(
    Gemini_client,
    r"LocalLLMExtractJob.md",
    r"PostExtractHTMLText.md"
)

print(verification_report)

with open("gemini_verification_report.md", "w", encoding="utf-8") as f:
    f.write(verification_report)
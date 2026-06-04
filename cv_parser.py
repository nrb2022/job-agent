"""
cv_parser.py — Extract structured profile data from PDF/DOCX using Claude AI.
"""
import json
import re
from pathlib import Path
from typing import Optional
import anthropic
import pypdf
from docx import Document

from config import settings


client = anthropic.Anthropic(api_key=settings.anthropic_api_key)


# ─── Text Extraction ──────────────────────────────────────────────────────────

def extract_text_from_pdf(path: str) -> str:
    reader = pypdf.PdfReader(path)
    texts = []
    for page in reader.pages:
        t = page.extract_text()
        if t:
            texts.append(t.strip())
    return "\n\n".join(texts)


def extract_text_from_docx(path: str) -> str:
    doc = Document(path)
    return "\n".join(para.text for para in doc.paragraphs if para.text.strip())


def extract_cv_text(path: str) -> str:
    ext = Path(path).suffix.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(path)
    elif ext in [".docx", ".doc"]:
        return extract_text_from_docx(path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")


# ─── AI Parsing ───────────────────────────────────────────────────────────────

PARSE_SYSTEM_PROMPT = """You are an expert CV/Resume parser. 
Extract structured information from the CV text provided.
Return ONLY valid JSON with no markdown, no preamble.

JSON schema:
{
  "name": "string",
  "email": "string or null",
  "phone": "string or null",
  "current_title": "string — most recent job title",
  "years_experience": "integer — total years of professional experience",
  "summary": "string — 2-3 sentence professional summary you infer from the CV",
  "skills": ["array", "of", "technical", "and", "soft", "skills"],
  "experience": [
    {
      "title": "job title",
      "company": "company name",
      "location": "city/country",
      "duration_years": 2.5,
      "description": "brief role summary"
    }
  ],
  "education": [
    {
      "degree": "B.Tech Computer Science",
      "institution": "IIT Bangalore",
      "year": 2010
    }
  ],
  "certifications": ["list of certifications"],
  "languages": ["English", "Hindi"],
  "inferred_target_titles": ["3-5 job titles this person should apply for"],
  "inferred_salary_range": {
    "min": 1500000,
    "max": 2500000,
    "currency": "INR",
    "reasoning": "based on experience level"
  }
}"""


async def parse_cv(cv_text: str) -> dict:
    """Use Claude to parse CV text into structured profile data."""
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        system=PARSE_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Parse this CV:\n\n{cv_text[:12000]}"  # Trim to fit context
            }
        ]
    )

    raw = message.content[0].text.strip()

    # Strip any accidental markdown fences
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    return json.loads(raw)


# ─── Main Entry Point ─────────────────────────────────────────────────────────

async def process_cv_upload(file_path: str) -> dict:
    """
    Full pipeline: extract text → parse with Claude → return structured profile.
    """
    print(f"[CV Parser] Extracting text from: {file_path}")
    cv_text = extract_cv_text(file_path)

    if not cv_text or len(cv_text.strip()) < 100:
        raise ValueError("CV appears to be empty or unreadable. Please upload a text-based PDF or DOCX.")

    print(f"[CV Parser] Extracted {len(cv_text)} characters. Sending to Claude...")
    parsed = await parse_cv(cv_text)

    print(f"[CV Parser] Parsed profile for: {parsed.get('name', 'Unknown')}")
    return {
        "cv_text": cv_text,
        "parsed": parsed
    }

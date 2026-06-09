import json, re, subprocess
from pathlib import Path
from docx import Document
import pypdf

MODEL = "qwen2.5:7b"

def extract_text_from_docx(path):
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())

def extract_text_from_pdf(path):
    reader = pypdf.PdfReader(path)
    return "\n\n".join(p.extract_text() for p in reader.pages if p.extract_text())

def extract_cv_text(path):
    ext = Path(path).suffix.lower()
    if ext == ".pdf": return extract_text_from_pdf(path)
    elif ext in [".docx", ".doc"]: return extract_text_from_docx(path)
    raise ValueError(f"Unsupported: {ext}")

def parse_cv_sync(cv_text):
    prompt = f"""Return ONLY a JSON object. No newlines inside string values. No markdown.
{{"name":"string","email":"string","phone":"string","current_title":"string","years_experience":20,"summary":"string","skills":["skill1"],"experience":[{{"title":"string","company":"string","duration_years":1,"description":"string"}}],"education":[{{"degree":"string","institution":"string","year":2000}}],"inferred_target_titles":["title1","title2","title3"],"inferred_salary_range":{{"min":2000000,"max":4000000,"currency":"INR"}}}}
CV:
{" ".join(cv_text[:3000].split())}
JSON:"""

    import urllib.request, json as _json
    payload = _json.dumps({"model": MODEL, "prompt": prompt, "stream": False}).encode()
    req = urllib.request.Request("http://localhost:11434/api/generate",
        data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as resp:
        raw = _json.loads(resp.read())["response"].strip()
    # Strip ANSI escape codes
    raw = re.sub(r"\[[0-9;]*[A-Za-z]", "", raw)
    print(f"[CV Parser] Raw: {raw[:200]}")

    # Strip markdown fences
    raw = re.sub(r"```json", "", raw)
    raw = re.sub(r"```", "", raw)
    raw = raw.strip()

    # Extract JSON block
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        raw = match.group(0)

    # Replace ALL whitespace sequences (including newlines) with single space
    raw = re.sub(r"\s+", " ", raw)

    # Remove control characters except normal whitespace
    raw = "".join(c if ord(c) >= 32 or c in " " else " " for c in raw)
    return json.loads(raw)

async def parse_cv(cv_text):
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, parse_cv_sync, cv_text)

async def process_cv_upload(file_path):
    cv_text = extract_cv_text(file_path)
    if not cv_text or len(cv_text.strip()) < 100:
        raise ValueError("CV appears to be empty or unreadable.")
    print(f"[CV Parser] Extracted {len(cv_text)} chars")
    parsed = await parse_cv(cv_text)
    return {"cv_text": cv_text, "parsed": parsed}

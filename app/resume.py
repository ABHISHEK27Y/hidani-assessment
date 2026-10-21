"""Local resume parsing. Raw files and raw resume text are never persisted."""
from __future__ import annotations

import io
import re
import zipfile
from datetime import date
from pathlib import Path

import fitz
from docx import Document

from app.skills import SKILLS, extract_skills

MAX_BYTES = 8 * 1024 * 1024
SECTIONS = {
    "experience": {"experience", "work experience", "professional experience", "employment", "internships"},
    "education": {"education", "academic qualifications", "academic background"},
    "projects": {"projects", "personal projects", "selected projects", "academic projects"},
    "skills": {"skills", "technical skills", "technical expertise", "technologies"},
    "other": {"achievements", "achievements and recognition", "certifications", "awards", "summary", "profile", "objective", "publications"},
}
MONTHS = {name: i for i, name in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
DATE_RANGE = re.compile(
    r"\b([A-Za-z]{3,9})\.?\s+(20\d{2})\s*[-–—]\s*(?:([A-Za-z]{3,9})\.?\s+(20\d{2})|(present|current|now))\b", re.I)
TITLE = re.compile(
    r"\b(?:(?:senior|junior|lead|staff|associate)\s+)?(?:software engineer(?:ing)?|software developer|full[ -]?stack (?:developer|engineer)|front[ -]?end (?:developer|engineer)|back[ -]?end (?:developer|engineer)|data scientist|data analyst|data engineer|machine learning engineer|AI engineer|devops engineer|product manager|web developer|SDE|UI/UX designer)(?:\s+intern)?\b", re.I)


def read_resume(filename: str, data: bytes) -> str:
    if not data or len(data) > MAX_BYTES:
        raise ValueError("Upload a non-empty resume smaller than 8 MB.")
    extension = Path(filename).suffix.lower()
    try:
        if extension == ".pdf":
            if not data.startswith(b"%PDF-"):
                raise ValueError("This file is not a valid PDF. Export the resume again and retry.")
            with fitz.open(stream=data, filetype="pdf") as doc:
                if doc.needs_pass:
                    raise ValueError("This PDF is password protected. Upload an unlocked copy.")
                if len(doc) > 20:
                    raise ValueError("Resume PDFs may contain at most 20 pages.")
                text = "\n".join(page.get_text(sort=True) for page in doc)
        elif extension == ".docx":
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                if sum(item.file_size for item in archive.infolist()) > 32 * 1024 * 1024:
                    raise ValueError("This DOCX expands beyond the supported size. Export a smaller copy.")
            doc = Document(io.BytesIO(data))
            # Preserve document order, including table-based resumes.
            lines = []
            for block in doc.iter_inner_content():
                if hasattr(block, "text"):
                    lines.append(block.text)
                else:
                    lines.extend(" | ".join(cell.text for cell in row.cells) for row in block.rows)
            text = "\n".join(lines)
        else:
            raise ValueError("Please upload a PDF or DOCX resume.")
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("I could not read that file. Try a text-based PDF or DOCX.") from exc
    text = re.sub(r"[ \t]+", " ", text.replace("\x00", "")).strip()
    if len(text) < 80:
        raise ValueError("The resume has too little readable text. Scanned PDFs need OCR or a text-based copy.")
    return text[:60000]


def _sections(lines: list[str]) -> dict[str, list[str]]:
    output = {key: [] for key in SECTIONS}
    current = None
    for line in lines:
        heading = line.strip().rstrip(":").lower()
        group = next((key for key, names in SECTIONS.items() if heading in names), None)
        if group:
            current = group
        elif current:
            output[current].append(line)
    return output


def _experience_months(lines: list[str]) -> tuple[int | None, str]:
    # Inclusive month ranges, unioned to avoid double-counting overlapping roles.
    months = set()
    today = date.today()
    for match in DATE_RANGE.finditer(" ".join(lines)):
        start_month = MONTHS.get(match[1][:3].lower())
        end_month = MONTHS.get((match[3] or "")[:3].lower())
        if not start_month or (not end_month and not match[5]):
            continue
        start = int(match[2]) * 12 + start_month - 1
        end = today.year * 12 + today.month - 1 if match[5] else int(match[4]) * 12 + end_month - 1
        end = min(end, today.year * 12 + today.month - 1)
        if 0 <= end - start <= 600:
            months.update(range(start, end + 1))
    if months:
        return len(months), "Dated work history (inclusive calendar months)"
    explicit = re.findall(r"\b(\d{1,2}(?:\.\d)?)\s*\+?\s*years?\b", " ".join(lines), re.I)
    if explicit:
        return round(max(map(float, explicit)) * 12), "Stated work experience"
    return None, "Not stated"


def _project_titles(lines: list[str]) -> list[str]:
    titles = []
    for line in lines:
        if line.startswith(("•", "- ", "* ")) or re.match(r"^(built|developed|implemented|engineered|designed)\b", line, re.I):
            continue
        if DATE_RANGE.search(line):
            title = DATE_RANGE.sub("", line).strip(" -–—|")
            if title:
                titles.append(title)
    return titles[:12]


def extract_profile(text: str) -> dict:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    sections = _sections(lines)
    email = re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text)
    phone = re.search(r"(?<!\d)(?:\+?\d[\d ()-]{8,}\d)(?!\d)", "\n".join(lines[:10]))
    name = next((line for line in lines[:6]
                 if 1 < len(line.split()) <= 5 and len(line) < 65
                 and not re.search(r"@|https?://|linkedin|github|\d|resume|curriculum", line, re.I)
                 and not TITLE.search(line)), "Not found")
    # Work titles take precedence over mentions inside projects or education.
    title_match = next((match for line in sections["experience"] if (match := TITLE.search(line))), None)
    if not title_match:
        title_match = next((match for line in lines[:8] if (match := TITLE.search(line))), None)
    designation = title_match.group(0).strip() if title_match else "Not found"
    months, experience_source = _experience_months(sections["experience"])
    if months is None and re.search(r"\b(fresher|student|intern|graduate)\b", designation, re.I):
        months, experience_source = 0, "Entry-level title; duration not stated"
    project_titles = _project_titles(sections["projects"])
    warnings = []
    if designation == "Not found":
        warnings.append("Designation was not detected. Tell me your target role in chat.")
    if months is None:
        warnings.append("Work duration was not detected. Tell me your experience to improve seniority matching.")
    if not project_titles and sections["projects"]:
        project_titles = [line for line in sections["projects"] if not line.startswith("•")][:3]
    return {
        "name": name, "email": email.group(0) if email else "Not found",
        "phone": phone.group(0).strip() if phone else "Not found",
        "designation": designation, "skills": extract_skills(text),
        "experience": sections["experience"][:30],
        "experience_months": months, "years_experience": round(months / 12, 2) if months is not None else None,
        "experience_source": experience_source,
        "education": sections["education"][:16],
        "projects": sections["projects"][:45], "project_titles": project_titles,
        "warnings": warnings,
    }

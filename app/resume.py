"""Extract resume text and a conservative, inspectable candidate profile."""
from __future__ import annotations

import io
import re
from pathlib import Path

import fitz
from docx import Document

SKILLS = {
    "Python": [r"\bpython\b"], "JavaScript": [r"\bjavascript\b", r"\bjs\b"],
    "TypeScript": [r"\btypescript\b"], "React": [r"\breact(?:\.js)?\b"],
    "Next.js": [r"\bnext(?:\.js)?\b"], "Node.js": [r"\bnode(?:\.js)?\b"],
    "FastAPI": [r"\bfastapi\b"], "Django": [r"\bdjango\b"],
    "Flask": [r"\bflask\b"], "Java": [r"\bjava\b"],
    "Spring": [r"\bspring(?: boot)?\b"], "C++": [r"\bc\+\+\b"],
    "C#": [r"\bc#\b"], "Go": [r"\bgo(?:lang)?\b"],
    "Rust": [r"\brust\b"], "SQL": [r"\bsql\b"],
    "PostgreSQL": [r"\bpostgres(?:ql)?\b"], "MongoDB": [r"\bmongodb\b"],
    "Redis": [r"\bredis\b"], "AWS": [r"\baws\b", r"amazon web services"],
    "Azure": [r"\bazure\b"], "GCP": [r"\bgcp\b", r"google cloud"],
    "Docker": [r"\bdocker\b"], "Kubernetes": [r"\bkubernetes\b", r"\bk8s\b"],
    "Git": [r"\bgit\b"], "CI/CD": [r"\bci/cd\b"],
    "Machine Learning": [r"machine learning", r"\bml\b"],
    "LLM": [r"\bllms?\b", r"large language model"],
    "LangChain": [r"\blangchain\b"], "PyTorch": [r"\bpytorch\b"],
    "TensorFlow": [r"\btensorflow\b"], "NLP": [r"\bnlp\b"],
    "HTML": [r"\bhtml\b"], "CSS": [r"\bcss\b"],
    "Tailwind": [r"\btailwind\b"], "Vue": [r"\bvue(?:\.js)?\b"],
    "Angular": [r"\bangular\b"], "GraphQL": [r"\bgraphql\b"],
    "REST APIs": [r"\brest(?:ful)?\b"], "Figma": [r"\bfigma\b"],
    "Excel": [r"\bexcel\b"], "Tableau": [r"\btableau\b"],
}
SECTION_RE = re.compile(r"^(experience|work experience|employment|education|projects|personal projects|skills|technical skills|certifications|achievements)\s*:? *$", re.I)


def read_resume(filename: str, data: bytes) -> str:
    if not data or len(data) > 8 * 1024 * 1024:
        raise ValueError("Upload a non-empty resume smaller than 8 MB.")
    extension = Path(filename).suffix.lower()
    try:
        if extension == ".pdf":
            with fitz.open(stream=data, filetype="pdf") as doc:
                if len(doc) > 20:
                    raise ValueError("Resume PDFs may contain at most 20 pages.")
                text = "\n".join(page.get_text(sort=True) for page in doc)
        elif extension == ".docx":
            doc = Document(io.BytesIO(data))
            lines = [p.text for p in doc.paragraphs]
            for table in doc.tables:
                lines.extend(" | ".join(cell.text for cell in row.cells) for row in table.rows)
            text = "\n".join(lines)
        else:
            raise ValueError("Please upload a PDF or DOCX resume.")
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("I could not read that file. Try a text-based PDF or DOCX.") from exc
    text = re.sub(r"[ \t]+", " ", text).strip()
    if len(text) < 80:
        raise ValueError("The resume has too little readable text. Scanned PDFs need OCR or a text-based copy.")
    return text[:50000]


def _section(lines: list[str], names: set[str]) -> list[str]:
    start = None
    for i, line in enumerate(lines):
        if line.strip().rstrip(":").lower() in names:
            start = i + 1
            break
    if start is None:
        return []
    out = []
    for line in lines[start:]:
        if SECTION_RE.match(line.strip()):
            break
        if line.strip():
            out.append(line.strip())
    return out[:14]


def extract_profile(text: str) -> dict:
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    email = re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text)
    phone = re.search(r"(?:\+?\d[\d ()-]{8,}\d)", text)
    head = [x for x in lines[:8] if not re.search(r"@|https?://|linkedin|github|\d{7,}", x, re.I)]
    name = next((x for x in head if 1 < len(x.split()) <= 4 and len(x) < 55 and not re.search(r"resume|curriculum|engineer|developer|analyst|intern", x, re.I)), "Not found")
    title_re = re.compile(r"\b(?:software engineer|software developer|frontend developer|front.end engineer|backend developer|back.end engineer|full.stack developer|data scientist|data analyst|machine learning engineer|product manager|devops engineer|sde intern|web developer|ui/ux designer)\b", re.I)
    title = next((m.group(0).title() for line in lines[:14] if (m := title_re.search(line))), "Not found")
    skills = [skill for skill, patterns in SKILLS.items() if any(re.search(p, text, re.I) for p in patterns)]
    experience = _section(lines, {"experience", "work experience", "employment"})
    education = _section(lines, {"education"})
    projects = _section(lines, {"projects", "personal projects"})
    years = [float(x) for x in re.findall(r"\b(\d{1,2}(?:\.\d)?)\s*\+?\s*years?\b", " ".join(experience), re.I)]
    return {
        "name": name, "email": email.group(0) if email else "Not found",
        "phone": phone.group(0).strip() if phone else "Not found",
        "designation": title, "skills": skills,
        "experience": experience[:8], "years_experience": max(years) if years else None,
        "education": education[:6], "projects": projects[:8],
    }

"""Shared, boundary-aware skill vocabulary for resumes, queries and job ingestion."""
import re
from functools import lru_cache

ALIASES = {
    "Python": ["python"], "JavaScript": ["javascript", "js"],
    "TypeScript": ["typescript"], "C++": ["c++"], "C#": ["c#"],
    "Java": ["java"], "Go": ["golang"], "Rust": ["rust"], "Solidity": ["solidity"],
    "React": ["react", "react.js", "reactjs"], "Next.js": ["next.js", "nextjs"],
    "Node.js": ["node.js", "nodejs"], "Express.js": ["express.js", "expressjs"],
    "FastAPI": ["fastapi"], "Django": ["django"], "Flask": ["flask"],
    "Spring": ["spring boot", "spring framework"], "Vue": ["vue", "vue.js"],
    "Angular": ["angular"], "HTML": ["html", "html5"], "CSS": ["css", "css3"],
    "Tailwind": ["tailwind", "tailwindcss", "tailwind css"],
    "SQL": ["sql"], "PostgreSQL": ["postgresql", "postgres"], "MySQL": ["mysql"],
    "MongoDB": ["mongodb"], "Redis": ["redis"], "Firebase": ["firebase"], "Supabase": ["supabase"],
    "AWS": ["aws", "amazon web services"], "Azure": ["azure"], "GCP": ["gcp", "google cloud"],
    "Docker": ["docker"], "Kubernetes": ["kubernetes", "k8s"], "Terraform": ["terraform"],
    "Git": ["git"], "CI/CD": ["ci/cd", "continuous integration"],
    "REST APIs": ["rest", "restful", "rest apis"], "GraphQL": ["graphql"],
    "Machine Learning": ["machine learning", "ml"], "LLM": ["llm", "llms", "large language model"],
    "RAG": ["rag", "retrieval augmented generation", "retrieval-augmented generation"],
    "LangChain": ["langchain"], "PyTorch": ["pytorch"], "TensorFlow": ["tensorflow"],
    "Scikit-learn": ["scikit-learn", "sklearn"], "NLP": ["nlp", "natural language processing"],
    "Pandas": ["pandas"], "NumPy": ["numpy"], "TF-IDF": ["tf-idf"],
    "Figma": ["figma"], "Excel": ["excel"], "Tableau": ["tableau"],
}
SKILLS = {name: [r"(?<![\w])" + re.escape(alias) + r"(?![\w])" for alias in aliases]
          for name, aliases in ALIASES.items()}
_PATTERNS = {name: re.compile("|".join(patterns), re.I) for name, patterns in SKILLS.items()}


def extract_skills(text: str) -> list[str]:
    return [name for name, pattern in _PATTERNS.items() if pattern.search(text)]


@lru_cache(maxsize=256)
def canonical_skill(value: str) -> str:
    if value in ALIASES:
        return value
    matches = extract_skills(value)
    return matches[0] if matches else value.strip()

"""Справочники ролей, навыков и городов для Team Finder."""

from __future__ import annotations

TEAM_MODES = ("seeking_team", "seeking_member")

TEAM_ROLES: dict[str, str] = {
    "frontend": "Frontend",
    "backend": "Backend",
    "mobile": "Mobile",
    "design": "Design",
    "devops": "DevOps",
    "data_ml": "Data & ML",
    "game_dev": "Game Dev",
    "pm": "Product / PM",
    "marketing": "Marketing",
    "other": "Other",
}

TEAM_CITIES: dict[str, str] = {
    "almaty": "Алматы",
    "astana": "Астана",
    "shymkent": "Шымкент",
    "karaganda": "Караганда",
    "online": "Online",
    "other": "Другой",
}

# slug -> (label, category)
TEAM_SKILLS: dict[str, tuple[str, str]] = {
    "html_css": ("HTML/CSS", "frontend"),
    "javascript": ("JavaScript", "frontend"),
    "react": ("React", "frontend"),
    "vue": ("Vue.js", "frontend"),
    "typescript": ("TypeScript", "frontend"),
    "nextjs": ("Next.js", "frontend"),
    "nodejs": ("Node.js", "backend"),
    "python": ("Python", "backend"),
    "express": ("Express.js", "backend"),
    "django": ("Django", "backend"),
    "postgresql": ("PostgreSQL", "backend"),
    "mongodb": ("MongoDB", "backend"),
    "graphql": ("GraphQL", "backend"),
    "react_native": ("React Native", "mobile"),
    "flutter": ("Flutter", "mobile"),
    "swift": ("Swift (iOS)", "mobile"),
    "kotlin": ("Kotlin (Android)", "mobile"),
    "docker": ("Docker", "devops"),
    "kubernetes": ("Kubernetes", "devops"),
    "linux": ("Linux", "devops"),
    "tensorflow": ("TensorFlow", "data_ml"),
    "pytorch": ("PyTorch", "data_ml"),
    "pandas": ("Pandas", "data_ml"),
    "sql": ("SQL", "data_ml"),
    "unity": ("Unity", "game_dev"),
    "unreal": ("Unreal Engine", "game_dev"),
    "cpp": ("C++", "game_dev"),
    "game_design": ("Game Design", "game_dev"),
    "figma": ("Figma", "design"),
    "adobe_xd": ("Adobe XD", "design"),
    "photoshop": ("Photoshop", "design"),
    "prototyping": ("Prototyping", "design"),
    "git": ("Git", "other"),
    "rest_api": ("REST API", "other"),
    "testing": ("Testing", "other"),
    "agile": ("Agile / Scrum", "other"),
}

# keyword -> skill slug (local extraction)
_SKILL_KEYWORDS: dict[str, str] = {
    "html": "html_css",
    "css": "html_css",
    "javascript": "javascript",
    "js": "javascript",
    "react": "react",
    "reactjs": "react",
    "vue": "vue",
    "typescript": "typescript",
    "next.js": "nextjs",
    "nextjs": "nextjs",
    "node": "nodejs",
    "nodejs": "nodejs",
    "python": "python",
    "django": "django",
    "express": "express",
    "postgres": "postgresql",
    "postgresql": "postgresql",
    "mongo": "mongodb",
    "mongodb": "mongodb",
    "graphql": "graphql",
    "react native": "react_native",
    "flutter": "flutter",
    "swift": "swift",
    "kotlin": "kotlin",
    "docker": "docker",
    "kubernetes": "kubernetes",
    "k8s": "kubernetes",
    "linux": "linux",
    "tensorflow": "tensorflow",
    "pytorch": "pytorch",
    "pandas": "pandas",
    "sql": "sql",
    "unity": "unity",
    "unreal": "unreal",
    "c++": "cpp",
    "figma": "figma",
    "photoshop": "photoshop",
    "git": "git",
    "rest": "rest_api",
    "api": "rest_api",
    "jest": "testing",
    "pytest": "testing",
    "agile": "agile",
    "scrum": "agile",
    "go": "backend",
    "golang": "backend",
    "java": "backend",
    "backend": "backend",
    "frontend": "frontend",
    "mobile": "mobile",
    "design": "design",
    "devops": "devops",
    "ml": "data_ml",
    "ai": "data_ml",
}

_ROLE_KEYWORDS: dict[str, str] = {
    "frontend": "frontend",
    "фронт": "frontend",
    "backend": "backend",
    "бэкенд": "backend",
    "бекенд": "backend",
    "mobile": "mobile",
    "мобил": "mobile",
    "design": "design",
    "дизайн": "design",
    "devops": "devops",
    "data": "data_ml",
    "ml": "data_ml",
    "machine learning": "data_ml",
    "game": "game_dev",
    "unity": "game_dev",
    "pm": "pm",
    "product": "pm",
    "marketing": "marketing",
    "маркетинг": "marketing",
}

_CITY_KEYWORDS: dict[str, str] = {
    "алматы": "almaty",
    "almaty": "almaty",
    "астана": "astana",
    "astana": "astana",
    "шымкент": "shymkent",
    "караганда": "karaganda",
    "online": "online",
    "онлайн": "online",
    "удален": "online",
    "remote": "online",
}


def skill_label(slug: str) -> str:
    entry = TEAM_SKILLS.get(slug)
    return entry[0] if entry else slug.replace("_", " ").title()


def role_label(slug: str) -> str:
    return TEAM_ROLES.get(slug, slug.replace("_", " ").title())


def city_label(slug: str) -> str:
    return TEAM_CITIES.get(slug, slug.replace("_", " ").title())


def normalize_skill_slug(raw: str) -> str | None:
    key = (raw or "").lower().strip().replace(" ", "_").replace("-", "_")
    if key in TEAM_SKILLS:
        return key
    return _SKILL_KEYWORDS.get(key.replace("_", " ")) or _SKILL_KEYWORDS.get(key)


def extract_skills_local(text: str) -> list[str]:
    lowered = (text or "").lower()
    found: list[str] = []
    for keyword, slug in sorted(_SKILL_KEYWORDS.items(), key=lambda x: -len(x[0])):
        if keyword in lowered and slug not in found:
            found.append(slug)
    return found[:12]


def extract_role_local(text: str) -> str | None:
    lowered = (text or "").lower()
    for keyword, role in sorted(_ROLE_KEYWORDS.items(), key=lambda x: -len(x[0])):
        if keyword in lowered:
            return role
    return None


def extract_city_local(text: str) -> str | None:
    lowered = (text or "").lower()
    for keyword, city in sorted(_CITY_KEYWORDS.items(), key=lambda x: -len(x[0])):
        if keyword in lowered:
            return city
    return None


def extract_mode_local(text: str) -> str:
    lowered = (text or "").lower()
    hiring_markers = (
        "ищем человека",
        "ищем разработ",
        "нужен ",
        "нужна ",
        "набираем",
        "looking for",
        "we need",
        "hiring",
    )
    for marker in hiring_markers:
        if marker in lowered:
            return "seeking_member"
    return "seeking_team"


def skills_catalog_for_prompt() -> str:
    lines: list[str] = []
    by_cat: dict[str, list[str]] = {}
    for slug, (label, cat) in TEAM_SKILLS.items():
        by_cat.setdefault(cat, []).append(f"{slug} ({label})")
    for cat, items in by_cat.items():
        lines.append(f"{cat}: {', '.join(items)}")
    return "\n".join(lines)


def team_meta_payload() -> dict:
    skill_groups: dict[str, list[dict]] = {}
    for slug, (label, cat) in TEAM_SKILLS.items():
        skill_groups.setdefault(cat, []).append({"id": slug, "label": label})

    return {
        "modes": [
            {"id": "seeking_team", "label": "Ищу команду"},
            {"id": "seeking_member", "label": "Ищем человека"},
        ],
        "roles": [{"id": k, "label": v} for k, v in TEAM_ROLES.items()],
        "cities": [{"id": k, "label": v} for k, v in TEAM_CITIES.items()],
        "skillGroups": [
            {"id": cat, "label": role_label(cat) if cat in TEAM_ROLES else cat.replace("_", " ").title(), "skills": skills}
            for cat, skills in skill_groups.items()
        ],
    }

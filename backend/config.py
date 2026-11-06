import os
from functools import lru_cache


@lru_cache
def get_settings():
    origins = [
        o.strip()
        for o in os.getenv(
            "ALLOWED_ORIGINS",
            "https://m9nx.me,https://m9nx.github.io,http://localhost:8765,http://127.0.0.1:8765,http://localhost:8000,http://127.0.0.1:8000",
        ).split(",")
        if o.strip()
    ]
    approved = {
        u.strip().lower()
        for u in os.getenv("APPROVED_GITHUB_USERS", "").split(",")
        if u.strip()
    }
    same_site = os.getenv("SESSION_COOKIE_SAMESITE", "lax").lower()
    if same_site not in {"lax", "strict", "none"}:
        same_site = "lax"
    return {
        "allowed_origins": origins,
        "api_public_url": os.getenv("API_PUBLIC_URL", "http://127.0.0.1:8000").rstrip("/"),
        "api_github_client_id": os.getenv("API_GITHUB_CLIENT_ID", ""),
        "api_github_client_secret": os.getenv("API_GITHUB_CLIENT_SECRET", ""),
        "approved_github_users": approved,
        "session_secret": os.getenv("SESSION_SECRET", "dev-insecure-change-me"),
        "session_cookie_name": os.getenv("SESSION_COOKIE_NAME", "navigator_session"),
        "session_cookie_samesite": same_site,
        "session_cookie_secure": os.getenv("SESSION_COOKIE_SECURE", "true").lower() == "true",
        "oauth_success_redirect": os.getenv(
            "API_OAUTH_SUCCESS_REDIRECT",
            "https://m9nx.me/lunar-landing-site-navigator/prototype/",
        ),
        "science_calculations_ready": os.getenv("SCIENCE_CALCULATIONS_READY", "false").lower()
        == "true",
        "database_url": os.getenv("DATABASE_URL", "sqlite:////data/navigator.db"),
        "calculation_version": os.getenv("CALCULATION_VERSION", "0.1.0-scaffold"),
        "api_admin_token": os.getenv("API_ADMIN_TOKEN", ""),
    }

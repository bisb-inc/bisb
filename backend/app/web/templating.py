from pathlib import Path
from urllib.parse import urlsplit

from fastapi import Request
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))

_LINK_SCHEMES = {"", "http", "https"}


def safe_href(url: str) -> str:
    """Mantém links http(s) e relativos; troca esquemas executáveis (`javascript:`) por `#`."""
    # Navegadores ignoram espaços e caracteres de controle ao interpretar o esquema.
    compact = "".join(char for char in url if char > " ")
    try:
        scheme = urlsplit(compact).scheme.lower()
    except ValueError:
        return "#"
    return url if scheme in _LINK_SCHEMES else "#"


templates.env.filters["safe_href"] = safe_href


def is_htmx(request: Request) -> bool:
    return request.headers.get("HX-Request") == "true"

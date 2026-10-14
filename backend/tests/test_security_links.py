import re
from datetime import UTC, datetime

import pytest

from app.models import Event, EventSource

UNSAFE_URLS = [
    "javascript:alert(document.domain)",
    "JaVaScRiPt:alert(1)",
    "  javascript:alert(1)",
    "java\tscript:alert(1)",
    "java\nscript:alert(1)",
    "\x01javascript:alert(1)",
    "data:text/html,<script>alert(1)</script>",
    "vbscript:msgbox(1)",
]
UNSAFE_PREFIXES = ("javascript:", "data:", "vbscript:")


def _analysis_with_event(client, functional_db, website, event_url):
    created = client.post(
        "/analyses", json={"name": "Links", "target": {"name": "Alvo", "website": website}}
    )
    assert created.status_code == 201
    analysis = created.json()
    with functional_db() as session:
        session.add(
            Event(
                company_id=analysis["companies"][0]["company"]["id"],
                source=EventSource.GNEWS,
                title="Notícia externa",
                url=event_url,
                is_mock=False,
                published_at=datetime.now(UTC),
            )
        )
        session.commit()
    return analysis["id"]


def _hrefs(page_text):
    return re.findall(r'href="([^"]*)"', page_text)


@pytest.mark.parametrize("url", UNSAFE_URLS)
def test_executable_url_schemes_are_not_rendered_as_links(functional_client, functional_db, url):
    analysis_id = _analysis_with_event(functional_client, functional_db, url, url)

    companies = _hrefs(functional_client.get(f"/ui/analyses/{analysis_id}?view=companies").text)
    timeline = _hrefs(functional_client.get(f"/ui/analyses/{analysis_id}?view=timeline").text)

    for hrefs in (companies, timeline):
        compact = ["".join(char for char in href if char > " ").lower() for href in hrefs]
        assert [href for href in compact if href.startswith(UNSAFE_PREFIXES)] == []
    assert companies.count("#") == 1
    assert timeline.count("#") == 2


@pytest.mark.parametrize(
    ("website", "event_url"),
    [
        ("https://alfa.example/produtos?x=1", "https://news.example/a?b=1&c=2"),
        ("HTTP://alfa.example", "http://news.example/a"),
        ("alfa.example", "https://news.example/b"),
    ],
)
def test_http_and_relative_links_are_rendered_unchanged(
    functional_client, functional_db, website, event_url
):
    analysis_id = _analysis_with_event(functional_client, functional_db, website, event_url)

    companies = functional_client.get(f"/ui/analyses/{analysis_id}?view=companies").text
    timeline = functional_client.get(f"/ui/analyses/{analysis_id}?view=timeline").text

    assert f'href="{website}"' in companies
    assert timeline.count(f'href="{event_url.replace("&", "&amp;")}"') == 2

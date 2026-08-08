"""Tests for the REST API (Stage 7) using FastAPI's TestClient."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.main import create_app
from app.models import Company, Contact, Filing
from app.models.enums import ContactCategory


@pytest.fixture
def client(session: Session, company: Company, filing: Filing) -> Iterator[TestClient]:
    contact = Contact(
        company_id=company.id,
        full_name="Jane Doe",
        email="jane@u-blox.com",
        title="Certification Manager",
        category=ContactCategory.CERTIFICATION_MANAGER,
        confidence=90,
        priority=50,
    )
    contact.filings.append(filing)
    session.add(contact)
    session.flush()

    app = create_app()
    app.dependency_overrides[db_session] = lambda: session
    with TestClient(app) as c:
        yield c


def test_health(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_list_companies(client: TestClient) -> None:
    data = client.get("/companies").json()
    assert len(data) == 1
    assert data[0]["name"] == "u-blox"


def test_get_company(client: TestClient) -> None:
    companies = client.get("/companies").json()
    cid = companies[0]["id"]
    assert client.get(f"/company/{cid}").json()["name"] == "u-blox"


def test_get_company_404(client: TestClient) -> None:
    assert client.get("/company/99999").status_code == 404


def test_list_contacts_and_filters(client: TestClient) -> None:
    assert len(client.get("/contacts").json()) == 1
    assert len(client.get("/contacts?title=Certification").json()) == 1
    assert len(client.get("/contacts?country=Switzerland").json()) == 1
    assert len(client.get("/contacts?company=u-blox").json()) == 1
    assert len(client.get("/contacts?country=Germany").json()) == 0
    assert len(client.get("/contacts?category=CERTIFICATION_MANAGER").json()) == 1
    assert len(client.get("/contacts?category=EXECUTIVE").json()) == 0


def test_list_contacts_rejects_unknown_category(client: TestClient) -> None:
    assert client.get("/contacts?category=NOT_A_REAL_CATEGORY").status_code == 422


def test_contact_payload_includes_fcc_ids(client: TestClient) -> None:
    payload = client.get("/contacts").json()[0]
    assert payload["fcc_ids"] == ["XPYNORA-1"]
    assert payload["company"]["name"] == "u-blox"


def test_list_filings(client: TestClient) -> None:
    assert client.get("/filings").json()[0]["fcc_id"] == "XPYNORA-1"


def test_search(client: TestClient) -> None:
    assert len(client.get("/search?q=jane").json()) == 1
    assert len(client.get("/search?q=cyber").json()) == 0


def test_export_csv(client: TestClient) -> None:
    resp = client.get("/export/contacts.csv")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "Jane Doe" in resp.text

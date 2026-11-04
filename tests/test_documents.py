from fastapi.testclient import TestClient
import pytest
from jarvis.api import app
from jarvis import documents


def test_documents_require_owner_login():
    visitor = TestClient(app)
    assert visitor.get("/api/documents").status_code == 401
    assert visitor.get("/api/documents/v0.2.0/0").status_code == 401


def test_catalog_exposes_available_public_protocols(client):
    response = client.get("/api/documents")
    assert response.status_code == 200
    versions = response.json()["versions"]
    assert [version["id"] for version in versions] == ["v0.2.0", "v0.1.0"]
    assert len(versions[0]["documents"]) == 7
    assert len(versions[1]["documents"]) == 3
    document = client.get("/api/documents/v0.2.0/0").json()
    assert document["file_name"] == "00-PROTOKOLL.md"
    assert "UTKAST – INTE KÖRKLART" in document["content"]
    assert len(document["sha256"]) == 64


@pytest.mark.parametrize("version,document_id", [
    ("private", "0"), ("v0.2.0", ".env"), ("v0.2.0", "7"),
    ("v0.2.0", "-1"), ("v0.1.0", "6"), ("v0.2.0", "00"),
])
def test_only_allowlisted_documents_can_be_read(client, version, document_id):
    response = client.get(f"/api/documents/{version}/{document_id}")
    assert response.status_code == 404
    assert "content" not in response.json()


def test_unreadable_or_oversized_documents_are_rejected(client, monkeypatch, tmp_path):
    monkeypatch.setattr(documents, "ROOT", tmp_path)
    folder = tmp_path / "docs" / "research-poc" / "2026-10-20-v0.2.0"
    folder.mkdir(parents=True)
    path = folder / "00-PROTOKOLL.md"
    path.write_bytes(b"x" * 250001)
    assert client.get("/api/documents/v0.2.0/0").status_code == 404
    path.write_bytes(b"\xff")
    assert client.get("/api/documents/v0.2.0/0").status_code == 404


def test_resolved_path_cannot_leave_document_root(monkeypatch, tmp_path):
    monkeypatch.setattr(documents, "ROOT", tmp_path)
    monkeypatch.setattr(documents, "VERSIONS", {"escape": ("Invalid publication", "../private")})
    (tmp_path / "docs").mkdir()
    folder = tmp_path / "private"
    folder.mkdir(parents=True)
    private = folder / "00-PROTOKOLL.md"
    private.write_text("Not published", encoding="utf-8")
    assert documents.read("escape", "0") is None

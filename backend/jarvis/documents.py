"""Läsning av uttryckligen publicerade projektdokument; aldrig fria filsökvägar."""
import hashlib
from .config import ROOT

TITLES = (
    "Protokoll", "Ämnen och källurval", "Jämförelse och bedömning",
    "Påståenden och slutleverans", "Implementationsuppdrag",
    "Frysning och integritet", "Spårbarhet och projektkontroll",
)
FILES = (
    "00-PROTOKOLL.md", "01-AMNEN-OCH-KALLURVAL.md", "02-JAMFORELSE-OCH-BEDOMNING.md",
    "03-PASTAENDEN-OCH-SLUTLEVERANS.md", "04-IMPLEMENTATIONSUPPDRAG.md",
    "05-FRYSNING-OCH-INTEGRITET.md", "06-SPARBARHET-OCH-PROJEKTKONTROLL.md",
)
VERSIONS = {
    "v0.2.0": ("Arkiv – A1-protokoll v0.2.0", "research-poc/2026-10-20-v0.2.0"),
    "v0.1.0": ("Arkiv – tidigare protokoll v0.1.0", "research-poc/2026-10-18-v0.1.0-a5c383c6"),
}


def document_path(version, document_id):
    if version not in VERSIONS or document_id not in {str(i) for i in range(len(FILES))}:
        return None
    root = (ROOT / "docs").resolve()
    path = (root / VERSIONS[version][1] / FILES[int(document_id)]).resolve()
    return path if path.is_relative_to(root) and path.is_file() else None


def catalog():
    return {"versions": [
        {"id": version, "title": title, "documents": [
            {"id": str(i), "title": name, "file_name": FILES[i]}
            for i, name in enumerate(TITLES) if document_path(version, str(i)) is not None
        ]}
        for version, (title, _) in VERSIONS.items()
    ]}


def read(version, document_id):
    path = document_path(version, document_id)
    if path is None:
        return None
    with path.open("rb") as source:
        raw = source.read(250001)
    if len(raw) > 250000:
        return None
    try:
        content = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return None
    return {"id": document_id, "version": version, "file_name": path.name,
            "content": content, "sha256": hashlib.sha256(raw).hexdigest()}

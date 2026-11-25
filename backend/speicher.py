"""Atomare Datei-Updates für die lokalen JSON-Daten."""

import os
from pathlib import Path
from tempfile import NamedTemporaryFile


def schreibe_atomar(pfad: Path, text: str) -> None:
    """Ersetzt die Zieldatei erst, wenn der neue Inhalt vollständig ist."""
    pfad.parent.mkdir(parents=True, exist_ok=True)
    temporaer = None
    try:
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=pfad.parent,
                                prefix=f".{pfad.stem}-", suffix=".tmp", delete=False) as datei:
            temporaer = Path(datei.name)
            datei.write(text)
        os.replace(temporaer, pfad)
    finally:
        if temporaer is not None:
            temporaer.unlink(missing_ok=True)

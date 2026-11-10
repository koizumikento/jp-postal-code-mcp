import csv
from collections.abc import Callable
from datetime import timedelta
from email.utils import parsedate_to_datetime
from io import BytesIO, StringIO
from typing import Annotated, Any
from zipfile import ZipFile

from pydantic import StringConstraints, validate_call

from ._cache import Document, Snapshot, cache_path, load_snapshot

SOURCE_URL = "https://www.post.japanpost.jp/service/search/zipcode/download/utf-zip.html"
DATA_URL = SOURCE_URL.removesuffix("utf-zip.html") + "utf/zip/utf_ken_all.zip"
PostalCode = Annotated[str, StringConstraints(pattern=r"^[0-9]{3}-?[0-9]{4}$")]


def _load_postal_codes(fetch: Callable[[str], Document]) -> dict[str, Any]:
    document = fetch(DATA_URL)
    with ZipFile(BytesIO(document.body)) as archive:
        try:
            entry = archive.getinfo("utf_ken_all.csv")
        except KeyError:
            raise ValueError("The Japan Post archive does not contain the expected CSV.") from None
        if entry.file_size > 64 * 1024 * 1024:
            raise ValueError("The Japan Post archive does not contain the expected CSV.")
        text = archive.read(entry).decode("utf-8-sig")
    entries: dict[str, list[dict[str, str]]] = {}
    for row in csv.reader(StringIO(text), strict=True):
        if len(row) != 15 or len(row[2]) != 7 or not row[2].isascii() or not row[2].isdecimal():
            raise ValueError("Invalid row in the Japan Post CSV.")
        entries.setdefault(row[2], []).append(
            {
                "municipality_code": row[0],
                "prefecture": row[6],
                "municipality": row[7],
                "town_area": row[8],
            }
        )
    if not entries:
        raise ValueError("The Japan Post CSV has no postal codes.")
    updated = parsedate_to_datetime(document.last_modified) if document.last_modified else None
    return {
        "data_as_of": updated.isoformat() if updated else None,
        "source_urls": [SOURCE_URL, DATA_URL],
        "entries": entries,
    }


async def _snapshot(*, force: bool = False) -> Snapshot:
    path = cache_path("jp-postal-code-mcp", "JP_POSTAL_CODE_CACHE_DIR")
    return await load_snapshot(path, "national", timedelta(days=7), _load_postal_codes, force=force)


@validate_call
async def lookup_postal_code(postal_code: PostalCode) -> dict[str, Any]:
    """Find every town-area entry for a seven-digit Japan Post address postal code."""
    snapshot = await _snapshot()
    code = postal_code.replace("-", "")
    return {
        "postal_code": code,
        "items": snapshot.data["entries"].get(code, []),
        **snapshot.metadata(),
    }


async def refresh_cache() -> dict[str, Any]:
    """Check the official postal code file immediately and retain the last valid copy."""
    snapshot = await _snapshot(force=True)
    return {"postal_codes": len(snapshot.data["entries"]), **snapshot.metadata()}

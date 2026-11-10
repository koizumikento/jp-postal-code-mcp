import csv
import unicodedata
from collections.abc import Callable
from datetime import timedelta
from email.utils import parsedate_to_datetime
from io import BytesIO, StringIO
from typing import Annotated, Any, Literal
from zipfile import ZipFile

from pydantic import Field, StringConstraints, validate_call

from ._cache import Document, Snapshot, cache_path, load_snapshot

SOURCE_URL = "https://www.post.japanpost.jp/service/search/zipcode/download/utf-zip.html"
DATA_URL = SOURCE_URL.removesuffix("utf-zip.html") + "utf/zip/utf_ken_all.zip"
BUSINESS_SOURCE_URL = (
    "https://www.post.japanpost.jp/service/search/zipcode/download/office/index-zip.html"
)
BUSINESS_DATA_URL = BUSINESS_SOURCE_URL.removesuffix("index-zip.html") + "zip/jigyosyo.zip"
PostalCode = Annotated[str, StringConstraints(pattern=r"^[0-9]{3}-?[0-9]{4}$")]
SearchText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Dataset = Literal["address", "business"]


def _csv_text(document: Document, member: str, encoding: str) -> str:
    with ZipFile(BytesIO(document.body)) as archive:
        try:
            entry = archive.getinfo(member)
        except KeyError:
            raise ValueError("The Japan Post archive does not contain the expected CSV.") from None
        if entry.file_size > 64 * 1024 * 1024:
            raise ValueError("The Japan Post archive does not contain the expected CSV.")
        return archive.read(entry).decode(encoding)


def _dataset_metadata(document: Document, source_url: str, data_url: str) -> dict[str, Any]:
    updated = parsedate_to_datetime(document.last_modified) if document.last_modified else None
    return {
        "data_as_of": updated.isoformat() if updated else None,
        "source_urls": [source_url, data_url],
    }


def _load_postal_codes(fetch: Callable[[str], Document]) -> dict[str, Any]:
    document = fetch(DATA_URL)
    text = _csv_text(document, "utf_ken_all.csv", "utf-8-sig")
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
    return {"entries": entries, **_dataset_metadata(document, SOURCE_URL, DATA_URL)}


def _load_business_postal_codes(fetch: Callable[[str], Document]) -> dict[str, Any]:
    document = fetch(BUSINESS_DATA_URL)
    text = _csv_text(document, "JIGYOSYO.CSV", "cp932")
    entries: dict[str, list[dict[str, str]]] = {}
    for row in csv.reader(StringIO(text), strict=True):
        if len(row) != 13 or len(row[7]) != 7 or not row[7].isascii() or not row[7].isdecimal():
            raise ValueError("Invalid row in the Japan Post business postal code CSV.")
        entries.setdefault(row[7], []).append(
            {
                "municipality_code": row[0],
                "business_name": row[2],
                "prefecture": row[3],
                "municipality": row[4],
                "town_area": row[5],
                "address_detail": row[6],
                "handling_post_office": row[9],
                "type_code": row[10],
            }
        )
    if not entries:
        raise ValueError("The Japan Post business CSV has no postal codes.")
    return {
        "entries": entries,
        **_dataset_metadata(document, BUSINESS_SOURCE_URL, BUSINESS_DATA_URL),
    }


async def _snapshot(dataset: Dataset = "address", *, force: bool = False) -> Snapshot:
    path = cache_path("jp-postal-code-mcp", "JP_POSTAL_CODE_CACHE_DIR")
    namespace, loader = (
        ("national", _load_postal_codes)
        if dataset == "address"
        else ("business", _load_business_postal_codes)
    )
    return await load_snapshot(path, namespace, timedelta(days=7), loader, force=force)


def _normalize_address(address: str) -> str:
    return "".join(unicodedata.normalize("NFKC", address).casefold().split())


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


@validate_call
async def search_postal_codes(
    address: SearchText,
    prefecture: SearchText | None = None,
    limit: Annotated[int, Field(ge=1, le=50)] = 10,
    offset: Annotated[int, Field(ge=0)] = 0,
) -> dict[str, Any]:
    """Find address postal codes by partial prefecture, municipality or town name."""
    query = _normalize_address(address)
    snapshot = await _snapshot()
    prefecture_filter = _normalize_address(prefecture) if prefecture is not None else None
    end = offset + limit
    matches = []
    total = 0
    for code, entries in snapshot.data["entries"].items():
        for entry in entries:
            if prefecture_filter is not None and (
                _normalize_address(entry["prefecture"]) != prefecture_filter
            ):
                continue
            full_address = entry["prefecture"] + entry["municipality"] + entry["town_area"]
            if query in _normalize_address(full_address):
                if offset <= total < end:
                    matches.append({"postal_code": code, **entry})
                total += 1
    return {
        "items": matches,
        "total": total,
        "next_offset": end if end < total else None,
        **snapshot.metadata(),
    }


@validate_call
async def lookup_business_postal_code(postal_code: PostalCode) -> dict[str, Any]:
    """Find entries for a Japan Post individual business or post office box postal code."""
    snapshot = await _snapshot("business")
    code = postal_code.replace("-", "")
    return {
        "postal_code": code,
        "items": snapshot.data["entries"].get(code, []),
        **snapshot.metadata(),
    }


@validate_call
async def refresh_cache(*, dataset: Dataset = "address") -> dict[str, Any]:
    """Check the chosen Japan Post data file immediately and retain the last valid copy."""
    snapshot = await _snapshot(dataset, force=True)
    return {"postal_codes": len(snapshot.data["entries"]), **snapshot.metadata()}

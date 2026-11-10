import sqlite3
from contextlib import closing
from io import BytesIO
from zipfile import ZipFile

import httpx
import pytest
import respx

from jp_postal_code_mcp import (
    lookup_business_postal_code,
    lookup_postal_code,
    refresh_cache,
    search_postal_codes,
)
from jp_postal_code_mcp.client import BUSINESS_DATA_URL, DATA_URL


@pytest.mark.asyncio
@respx.mock
async def test_cached_lookup_and_failed_refresh(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("JP_POSTAL_CODE_CACHE_DIR", str(tmp_path))
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr(
            "utf_ken_all.csv",
            "01101,060,0600000,a,b,c,北海道,札幌市中央区,町域A,0,0,0,0,0,0\n"
            "01101,060,0600000,a,b,c,北海道,札幌市中央区,町域B,0,0,0,0,0,0\n",
        )
    route = respx.get(DATA_URL).mock(
        side_effect=[
            httpx.Response(200, content=buffer.getvalue(), headers={"ETag": '"test"'}),
            httpx.Response(304),
            httpx.Response(200, content=b"invalid archive"),
        ]
    )
    result = await lookup_postal_code("060-0000")
    assert [item["town_area"] for item in result["items"]] == ["町域A", "町域B"]
    first = await search_postal_codes("札幌市中央区 町域", prefecture="北海道", limit=1)
    assert first["total"] == 2
    assert first["items"][0]["postal_code"] == "0600000"
    assert first["next_offset"] == 1
    last = await search_postal_codes("町域", limit=1, offset=1)
    assert last["items"][0]["town_area"] == "町域B"
    assert last["next_offset"] is None
    assert (await search_postal_codes("町域Ａ", prefecture="北海道"))["total"] == 1
    assert (await search_postal_codes("町域", prefecture="東京都"))["items"] == []
    assert (await lookup_postal_code("0600000")) == result
    assert route.call_count == 1
    with closing(sqlite3.connect(tmp_path / "cache.sqlite3")) as db, db:
        db.execute("UPDATE snapshots SET checked = '2000-01-01T00:00:00+00:00'")
    checked = await lookup_postal_code("0600000")
    assert route.calls[1].request.headers["If-None-Match"] == '"test"'
    assert checked["cache"]["fetched_at"] == result["cache"]["fetched_at"]
    failed = await refresh_cache()
    assert failed["cache"]["refresh_failed"]
    assert failed["cache"]["checked_at"] == checked["cache"]["checked_at"]
    assert (await lookup_postal_code("0600000"))["items"] == result["items"]
    assert route.call_count == 3


@pytest.mark.asyncio
@respx.mock
async def test_business_postal_codes_use_separate_cp932_snapshot(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("JP_POSTAL_CODE_CACHE_DIR", str(tmp_path))
    buffer = BytesIO()
    csv = (
        "01101,ジギョウショ,試験事業所,北海道,札幌市中央区,町域,１－２,0608621,060,札幌中央,0,0,0\n"
        "01101,シショバコ,試験私書箱,北海道,札幌市中央区,町域,１－２,0608621,060,札幌中央,1,0,0\n"
    )
    with ZipFile(buffer, "w") as archive:
        archive.writestr("JIGYOSYO.CSV", csv.encode("cp932"))
    route = respx.get(BUSINESS_DATA_URL).mock(
        side_effect=[
            httpx.Response(200, content=buffer.getvalue(), headers={"ETag": '"office"'}),
            httpx.Response(304),
        ]
    )
    result = await lookup_business_postal_code("060-8621")
    assert result["postal_code"] == "0608621"
    assert result["source_urls"][-1] == BUSINESS_DATA_URL
    assert result["items"][0]["business_name"] == "試験事業所"
    assert result["items"][1]["type_code"] == "1"
    assert (await lookup_business_postal_code("1000001"))["items"] == []
    assert (await refresh_cache(dataset="business"))["postal_codes"] == 1
    assert route.calls[1].request.headers["If-None-Match"] == '"office"'

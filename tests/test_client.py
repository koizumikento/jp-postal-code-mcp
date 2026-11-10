import sqlite3
from contextlib import closing
from io import BytesIO
from zipfile import ZipFile

import httpx
import pytest
import respx

from jp_postal_code_mcp import lookup_postal_code, refresh_cache
from jp_postal_code_mcp.client import DATA_URL


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

# jp-postal-code-mcp

日本郵便の住所用UTF-8 CSVから、郵便番号に対応する町域を検索します。

Python 3.12以上と [uv](https://docs.astral.sh/uv/) を使用します。

```bash
uv sync --locked
uv run jp-postal-code-mcp lookup-postal-code --postal-code 100-0001
```

CLIの結果はUTF-8のJSONです。引数なしでstdio MCPサーバーが起動します。
MCPクライアントではコマンドを `uv`、引数を `--directory`、リポジトリの絶対パス、`run`、`jp-postal-code-mcp` の順に設定します。

```python
import asyncio

from jp_postal_code_mcp import lookup_postal_code

print(asyncio.run(lookup_postal_code(postal_code="100-0001")))
```

同じ郵便番号の町域はすべて返します。データ基準日は、配布元が返すアーカイブの更新日時（取得できなければ `null`）です。事業所の個別郵便番号は収録範囲外です。確認間隔は7日です。

MCP・CLI・Pythonライブラリは同じローカルキャッシュを使います。保存先はWindowsでは `%LOCALAPPDATA%/jp-postal-code-mcp`、その他では `$XDG_CACHE_HOME/jp-postal-code-mcp` または `~/.cache/jp-postal-code-mcp` です。`JP_POSTAL_CODE_CACHE_DIR` で上書きできます。

期限を過ぎた最初の照会で配布元を確認し、対応している場合はHTTPの条件付き取得を使います。更新できない場合は最後に検証できた版を返し、`cache.refresh_failed` と `cache.checked_at` を確認できます。初回取得に失敗した場合はエラーになります。

```bash
uv run jp-postal-code-mcp refresh
```

データ出典は [公式資料](https://www.post.japanpost.jp/service/search/zipcode/download/utf-zip.html) です。MIT Licenseはコードに適用します。

郵便番号データの形式と取扱いは[日本郵便のデータ説明](https://www.post.japanpost.jp/service/search/zipcode/download/utf-readme.html)を参照してください。

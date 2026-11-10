# jp-postal-code-mcp

日本郵便の公開データから、郵便番号に対応する町域や、住所に対応する郵便番号を調べられます。大口事業所や私書箱の個別郵便番号も照会できます。

[MCP登録](#mcpクライアントに登録する) · [CLI](#cliで使う) · [Pythonライブラリ](#pythonライブラリとして使う)

## 利用前に

[uv](https://docs.astral.sh/uv/) と Git が必要です。Python 3.12以上に対応しています。APIキーの設定は不要です。

## MCPクライアントに登録する

公開GitHubリポジトリから `uvx` で起動します。初回は依存関係の準備に時間がかかることがあります。

### Codex

```sh
codex mcp add jp-postal-code-mcp -- uvx --python 3.12 --from git+https://github.com/koizumikento/jp-postal-code-mcp.git@main jp-postal-code-mcp
codex mcp list
```

`codex mcp list` で登録を確認し、Codexの新しいセッションで `/mcp` を開くと、接続状態を確認できます。[Codexの公式設定ガイド](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)

Codexのデスクトップアプリでは、設定の「MCP servers」でSTDIOサーバーを追加し、下のJSON例と同じコマンド・引数を指定する方法もあります。

### Claude Desktop / Cursor

次のファイルに設定します。

- Claude Desktop（Windows） `%APPDATA%/Claude/claude_desktop_config.json`
- Claude Desktop（macOS） `~/Library/Application Support/Claude/claude_desktop_config.json`
- Cursor `.cursor/mcp.json`（プロジェクト内）

既に `mcpServers` がある場合は、その中にサーバーの項目を追加してください。保存後にクライアントを再起動し、ツールが表示されるか確認します。[設定ファイルの場所と接続手順](https://py.sdk.modelcontextprotocol.io/get-started/real-host/)

```json
{
  "mcpServers": {
    "jp-postal-code-mcp": {
      "command": "uvx",
      "args": [
        "--python",
        "3.12",
        "--from",
        "git+https://github.com/koizumikento/jp-postal-code-mcp.git@main",
        "jp-postal-code-mcp"
      ]
    }
  }
}
```

`uvx` が見つからない場合は、設定のコマンドに実行ファイルの絶対パスを指定してください。

登録後は、チャットで次のように聞けます。

> 郵便番号100-0001に対応する住所を教えて。

> 北海道札幌市中央区の「北一条西」に対応する郵便番号を探して。

## MCPツール

| ツール | 用途 |
| --- | --- |
| `lookup_postal_code` | 7桁の郵便番号に対応する町域をすべて返す。ハイフンは省略可 |
| `search_postal_codes` | 都道府県・市区町村・町域の住所文字列から郵便番号を探す。都道府県を指定して絞り込める |
| `lookup_business_postal_code` | 7桁の個別郵便番号で、事業所名や所在地、取扱郵便局を照会 |

住所検索は、都道府県名・市区町村名・町域名をつないだ文字列に部分一致します。空白と文字幅の違いを吸収します。`next_offset` が返ったら、次の検索の `offset` に指定してください。

## CLIで使う

結果は標準出力にUTF-8のJSONで返ります。

```sh
uvx --python 3.12 --from git+https://github.com/koizumikento/jp-postal-code-mcp.git@main jp-postal-code-mcp lookup-postal-code --postal-code 100-0001
uvx --python 3.12 --from git+https://github.com/koizumikento/jp-postal-code-mcp.git@main jp-postal-code-mcp search-postal-codes --address "札幌市中央区北一条西" --prefecture "北海道"
uvx --python 3.12 --from git+https://github.com/koizumikento/jp-postal-code-mcp.git@main jp-postal-code-mcp lookup-business-postal-code --postal-code 060-8621
```

## Pythonライブラリとして使う

自分のPythonプロジェクト（`pyproject.toml` があるディレクトリ）で依存関係に追加します。

```sh
uv add "git+https://github.com/koizumikento/jp-postal-code-mcp.git@main"
```

次のコードを `example.py` に保存し、同じディレクトリで `uv run python example.py` を実行します。

```python
import asyncio

from jp_postal_code_mcp import lookup_business_postal_code, search_postal_codes

print(asyncio.run(search_postal_codes(address="札幌市中央区北一条西")))
print(asyncio.run(lookup_business_postal_code(postal_code="060-8621")))
```

## データの更新

MCP・CLI・Pythonは同じローカルキャッシュを使います。町域用と事業所用は、それぞれ初回の利用時に公式CSVを取得します。確認間隔は7日で、期限を過ぎた最初の照会時に更新を確認します。更新に失敗した場合は直前の正常な版を返し、`cache.refresh_failed` と `cache.checked_at` で失敗の有無と最後に確認できた日時を判別できます。初回取得に失敗した場合はエラーになります。

すぐに更新したいときは次を実行します。

```sh
uvx --python 3.12 --from git+https://github.com/koizumikento/jp-postal-code-mcp.git@main jp-postal-code-mcp refresh
uvx --python 3.12 --from git+https://github.com/koizumikento/jp-postal-code-mcp.git@main jp-postal-code-mcp refresh --dataset business
```

キャッシュはWindowsでは `%LOCALAPPDATA%/jp-postal-code-mcp`、その他では `$XDG_CACHE_HOME/jp-postal-code-mcp` または `~/.cache/jp-postal-code-mcp` に保存されます。`JP_POSTAL_CODE_CACHE_DIR` で保存先を指定できます。

## データの出典と利用条件

町域の照会・検索は日本郵便の住所用CSVを使います。結果の `data_as_of` は配布元が返すアーカイブの更新日時です。更新日時が得られない場合は `null` になります。[住所用CSVの配布ページ](https://www.post.japanpost.jp/service/search/zipcode/download/utf-zip.html)・[データ説明](https://www.post.japanpost.jp/service/search/zipcode/download/utf-readme.html)

個別郵便番号の照会は事業所用CSVを使います。公表を希望しない事業所は収録されません。結果の `type_code` は `0` が大口事業所、`1` が私書箱です。[事業所用CSVの配布ページ](https://www.post.japanpost.jp/service/search/zipcode/download/office/index-zip.html)・[データ説明](https://www.post.japanpost.jp/service/search/zipcode/download/office/readme.html)

MIT Licenseはこのリポジトリのコードに適用します。

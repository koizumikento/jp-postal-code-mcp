# jp-postal-code-mcp

7桁の郵便番号から、日本郵便のデータに登録された都道府県・市区町村・町域を調べられます。1つの番号に複数の町域があればすべて返します。

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

## MCPツール

| ツール | 用途 |
| --- | --- |
| `lookup_postal_code` | 7桁の郵便番号で町域を照会。ハイフンは省略可 |

## CLIで使う

結果は標準出力にUTF-8のJSONで返ります。

```sh
uvx --python 3.12 --from git+https://github.com/koizumikento/jp-postal-code-mcp.git@main jp-postal-code-mcp lookup-postal-code --postal-code 100-0001
```

## Pythonから呼び出す

リポジトリをクローンし、依存関係を準備します。

```sh
git clone https://github.com/koizumikento/jp-postal-code-mcp.git
cd jp-postal-code-mcp
uv sync --locked
```

次の例を `example.py` に保存し、クローン先で `uv run --locked python example.py` を実行します。

```python
import asyncio

from jp_postal_code_mcp import lookup_postal_code

print(asyncio.run(lookup_postal_code(postal_code="100-0001")))
```

## データの更新

MCP・CLI・Pythonは同じローカルキャッシュを使います。初回は公式CSVを取得します。確認間隔は7日で、期限を過ぎた最初の照会時に更新を確認します。更新に失敗した場合は直前の正常な版を返し、`cache.refresh_failed` と `cache.checked_at` で失敗の有無と最後に確認できた日時を判別できます。初回取得に失敗した場合はエラーになります。

すぐに更新したいときは次を実行します。

```sh
uvx --python 3.12 --from git+https://github.com/koizumikento/jp-postal-code-mcp.git@main jp-postal-code-mcp refresh
```

キャッシュはWindowsでは `%LOCALAPPDATA%/jp-postal-code-mcp`、その他では `$XDG_CACHE_HOME/jp-postal-code-mcp` または `~/.cache/jp-postal-code-mcp` に保存されます。`JP_POSTAL_CODE_CACHE_DIR` で保存先を指定できます。

## データの出典と利用条件

住所用のCSVを使用します。事業所の個別郵便番号は収録範囲外です。`data_as_of` は配布元が返すアーカイブの更新日時です。更新日時が得られない場合は `null` になります。[日本郵便の配布ページ](https://www.post.japanpost.jp/service/search/zipcode/download/utf-zip.html)・[データ説明](https://www.post.japanpost.jp/service/search/zipcode/download/utf-readme.html)

MIT Licenseはこのリポジトリのコードに適用します。

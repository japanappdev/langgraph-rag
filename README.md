# LangGraph × ChromaDB × FastAPI RAG

日本語対応のシンプルな RAG（Retrieval Augmented Generation）システムです。LangGraph で「検索 → 生成」のワークフローを構築し、ChromaDB をベクトル検索、OpenAI API を生成・埋め込みに利用します。トップページ（`/`）に簡易な検索 UI を同梱しています。
<img width="859" height="810" alt="スクリーンショット 2025-08-25 22 52 54" src="https://github.com/user-attachments/assets/528d8ba2-3b8b-4d8e-bfb3-5e0bb86462fd" />

## 特長
- 分かりやすい検索 UI（日本語対応）
- Docker Compose で簡単起動（API/Chroma/Seed）
- サンプルデータの投入スクリプト付き（`data/*.md`）
- 最小限の LangGraph 構成（Retrieve → Generate）

## 要件
- Docker / Docker Compose（推奨）
- OpenAI API キー（課金が発生します）

## クイックスタート（Docker）
1) `.env` を作成して API キーを設定
```bash
cp .env.example .env
# .env を開き OPENAI_API_KEY を設定
```

2) コンテナ起動とインデックス作成（初回のみ Seed 実行）
```bash
docker compose up -d chroma
docker compose up -d api
docker compose run --rm seed   # 初回データ投入／更新時に再実行
```

3) ブラウザでアクセス
- http://localhost:8001/

> まとめて起動する場合（seed は別途実行）
> ```bash
> docker compose up -d
> docker compose run --rm seed
> ```

## API
- `GET /`：検索 UI を返します。
- `POST /search`：RAG を実行します。

リクエスト例:
```json
{
  "query": "LangGraphとは？",
  "top_k": 4
}
```

レスポンス例:
```json
{
  "query": "LangGraphとは？",
  "top_k": 4,
  "answer": "LangGraphは…（省略）",
  "contexts": [
    {"id": "…", "text": "…", "metadata": {"source": "seed"}, "distance": 0.12}
  ]
}
```

## ディレクトリ構成
```
.
├─ app/
│  ├─ main.py           # FastAPI エントリ。UI と /search
│  ├─ rag_graph.py      # LangGraph（retrieve → generate）
│  ├─ retriever.py      # Chroma 検索 + OpenAI 埋め込み
│  └─ static/index.html # 検索 UI
├─ scripts/
│  └─ seed.py           # `data/*.md` を分割し upsert
├─ data/
│  └─ sample_jp.md      # サンプルドキュメント
├─ docker-compose.yml    # chroma/api/seed サービス
├─ Dockerfile
├─ pyproject.toml
└─ .env.example
```

## 環境変数
- `OPENAI_API_KEY`：OpenAI の API キー（必須）
- `OPENAI_MODEL`：生成モデル（既定: `gpt-4o-mini`）
- `OPENAI_EMBEDDING_MODEL`：埋め込みモデル（既定: `text-embedding-3-small`）
- `CHROMA_HOST` / `CHROMA_PORT`：ChromaDB 接続（Compose では自動設定）
- `CHROMA_COLLECTION`：コレクション名（既定: `docs`）
- `SEED_GLOB`：投入ファイルのグロブ（既定: `data/*.md`）

## データ投入（Seed）
- 既定では `data/*.md` を 600 文字程度で分割し、OpenAI 埋め込みを作成して ChromaDB に upsert します。
- 独自データを `data/` 配下に `.md` で追加し、再度 Seed を実行してください。
```bash
docker compose run --rm seed
```

## 開発（ローカル実行）
Docker を使わない場合：
```bash
# 依存関係のインストール（uv を使用）
uv pip install -e .

# API 起動（別途 ChromaDB サーバが必要）
uvicorn app.main:app --reload
```

別端末で ChromaDB を起動するか、`docker compose up -d chroma` を併用してください。

## アーキテクチャ概要
- Retrieve：OpenAI 埋め込みでクエリをベクトル化 → ChromaDB で近傍検索
- Generate：検索結果をコンテキストとして OpenAI Chat で回答生成
- 制御：LangGraph で「retrieve → generate」の状態遷移を定義

## トラブルシュート
- 「OpenAI API キーが未設定」：`.env` の `OPENAI_API_KEY` を設定してください。
- 「検索しても結果が出ない」：Seed を実行し、対象データが投入されているか確認してください。
- 「ChromaDB 接続エラー」：`docker compose ps` で `chroma` が起動しているか、`CHROMA_HOST/PORT` の値を確認してください。

## 注意事項
- OpenAI API の利用には料金が発生します。コスト管理に注意してください。
- 本リポジトリは学習・検証用の最小構成です。運用投入時は認証、監視、ログ、レート制限等をご検討ください。

## 貢献
Issue / Pull Request 歓迎です。改善提案やバグ報告があればお知らせください。

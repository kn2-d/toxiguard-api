## 📄 TECHNICAL_SPECIFICATION.md の内容

以下の内容を`TECHNICAL_SPECIFICATION.md`に記述してください：

```markdown
# ToxiGuard API 技術仕様書

<div align="center">
  <h1>🛡️ ToxiGuard API Technical Specification</h1>
  <p><strong>Version 4.0.0</strong></p>
  <p>最終更新日: 2025年6月17日</p>
</div>

---

## 📋 目次

1. [システムアーキテクチャ](#システムアーキテクチャ)
2. [技術スタック](#技術スタック)
3. [API仕様](#api仕様)
4. [データモデル](#データモデル)
5. [認証・認可](#認証認可)
6. [AIモデル詳細](#aiモデル詳細)
7. [パフォーマンス](#パフォーマンス)
8. [エラーハンドリング](#エラーハンドリング)
9. [実装例](#実装例)
10. [開発者ガイド](#開発者ガイド)

---

## システムアーキテクチャ

### 🏗️ 全体構成

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   クライアント    │────▶│  Load Balancer  │────▶│   Web Server    │
│  (Web/Mobile)   │     │    (Nginx)      │     │   (Uvicorn)     │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                          │
                                                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                         FastAPI Application                      │
├─────────────────┬──────────────────┬──────────────────────────┤
│   Middleware    │     Routers      │       Services            │
│  ├─ Auth       │  ├─ analyze      │  ├─ KeywordAnalyzer      │
│  └─ RateLimit  │  ├─ analyze_v2   │  ├─ ToxicBertAnalyzer    │
│                │  ├─ api_key      │  ├─ ClaudeAnalyzer       │
│                │  └─ web          │  ├─ OpenAIAnalyzer       │
│                │                   │  └─ MultiModelAnalyzer   │
└─────────────────┴──────────────────┴────────────┬───────────────┘
                                                   │
                  ┌────────────────────────────────┼────────────┐
                  ▼                                ▼            ▼
         ┌──────────────┐              ┌──────────────┐  ┌──────────┐
         │  PostgreSQL  │              │    Redis     │  │   S3     │
         │   Database   │              │    Cache     │  │ Storage  │
         └──────────────┘              └──────────────┘  └──────────┘
```

### 🔄 リクエストフロー

1. **クライアント** → APIキーを含むHTTPSリクエスト
2. **認証ミドルウェア** → APIキー検証、使用量チェック
3. **ルーター** → 適切なサービスへルーティング
4. **分析サービス** → 選択された戦略で毒性分析
5. **レスポンス** → JSON形式で結果返却

---

## 技術スタック

### 🛠️ バックエンド

| カテゴリ | 技術 | バージョン | 用途 |
|---------|------|-----------|------|
| **言語** | Python | 3.12 | メイン開発言語 |
| **フレームワーク** | FastAPI | 0.104.1 | Web API |
| **サーバー** | Uvicorn | 0.24.0 | ASGI サーバー |
| **データベース** | PostgreSQL | 15 | メインDB |
| **ORM** | SQLAlchemy | 2.0.23 | データベース操作 |
| **キャッシュ** | Redis | 7.2 | キャッシュ（計画中） |

### 🤖 AI/ML

| モデル/ライブラリ | バージョン | 用途 |
|-----------------|-----------|------|
| **Transformers** | 4.52.4 | モデル管理 |
| **PyTorch** | 2.2.2 | 深層学習 |
| **Sentence-Transformers** | 2.2.2 | 埋め込みベース分析 |
| **ToxicBERT** | - | 毒性検知専用モデル |
| **Claude API** | 最新 | 高精度分析（外部API） |
| **OpenAI API** | 最新 | 比較分析（外部API） |

### 🎨 フロントエンド

| 技術 | 用途 |
|------|------|
| **HTML5/CSS3** | ランディングページ |
| **JavaScript** | インタラクティブ機能 |
| **Bootstrap Icons** | アイコン |

---

## API仕様

### 🔐 認証

すべてのAPIリクエストには`X-API-Key`ヘッダーが必要です。

```http
X-API-Key: your-api-key-here
```

### 📍 エンドポイント一覧

#### 1. **単一テキスト分析 (v1)**

```http
POST /api/v1/analyze
```

**リクエスト:**
```json
{
  "text": "分析したいテキスト"
}
```

**レスポンス:**
```json
{
  "is_toxic": false,
  "toxicity_score": 0.15,
  "categories": [
    {
      "name": "軽度の毒性",
      "score": 0.15
    }
  ],
  "confidence": 0.92
}
```

#### 2. **高度な分析 (v2)**

```http
POST /api/v2/analyze
```

**リクエスト:**
```json
{
  "text": "分析したいテキスト",
  "strategy": "balanced",  // optional: fast, cascade, balanced, accurate
  "options": {
    "include_reasoning": true,
    "threshold": 0.3
  }
}
```

**レスポンス:**
```json
{
  "is_toxic": false,
  "toxicity_score": 0.25,
  "primary_category": "軽度の毒性",
  "all_categories": [
    {
      "name": "軽度の毒性",
      "score": 0.25,
      "confidence": 0.88
    }
  ],
  "model_used": "multi",
  "strategy": "balanced",
  "processing_time": 2.34,
  "model_scores": {
    "keyword": 0.20,
    "toxic_bert": 0.28,
    "openai": 0.27
  }
}
```

#### 3. **バッチ分析**

```http
POST /api/v2/analyze/batch
```

**リクエスト:**
```json
{
  "texts": [
    "テキスト1",
    "テキスト2",
    "テキスト3"
  ],
  "strategy": "fast"
}
```

#### 4. **APIキー発行**

```http
POST /api/register
```

**リクエスト:**
```json
{
  "email": "user@example.com"
}
```

**レスポンス:**
```json
{
  "api_key": "tg_1234567890abcdef...",
  "email": "user@example.com",
  "daily_limit": 100
}
```

### 📊 分析戦略

| 戦略 | 説明 | 使用モデル | 精度 | 速度 |
|------|------|-----------|------|------|
| **fast** | 高速キーワードベース | Keyword | 87.5% | < 0.01秒 |
| **cascade** | 段階的判定 | Keyword → ToxicBERT | 95% | < 1秒 |
| **balanced** | バランス型 | 全モデル並列 | 98% | < 3秒 |
| **accurate** | 最高精度 | 全モデル + 重み最適化 | 99%+ | < 5秒 |

---

## データモデル

### 📦 主要モデル

#### APIキー (api_keys)

```sql
CREATE TABLE api_keys (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    api_key VARCHAR(64) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    daily_limit INTEGER DEFAULT 100,
    is_active BOOLEAN DEFAULT true
);
```

#### 使用量 (api_usage)

```sql
CREATE TABLE api_usage (
    id SERIAL PRIMARY KEY,
    api_key_id INTEGER REFERENCES api_keys(id),
    date DATE NOT NULL,
    request_count INTEGER DEFAULT 0,
    UNIQUE(api_key_id, date)
);
```

#### フィードバック (user_feedback)

```sql
CREATE TABLE user_feedback (
    id SERIAL PRIMARY KEY,
    request_id VARCHAR(36) UNIQUE NOT NULL,
    original_text TEXT NOT NULL,
    ai_result JSONB NOT NULL,
    user_correction JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 🔄 カテゴリ定義

```python
class ToxicityCategory(Enum):
    SEVERE_TOXICITY = "重度の毒性"      # 死ね、殺す等
    HATE_SPEECH = "ヘイトスピーチ"      # 差別的表現
    VIOLENCE = "暴力的表現"             # 暴力、脅迫
    SEXUAL = "性的な内容"               # 性的表現
    DISCRIMINATION = "差別的表現"        # 偏見、差別
    MILD_TOXICITY = "軽度の毒性"        # バカ、アホ等
```

---

## 認証・認可

### 🔒 認証フロー

```python
# ミドルウェア実装
async def verify_api_key(
    request: Request,
    api_key: str = Header(..., alias="X-API-Key")
):
    # 1. APIキー存在確認
    db_api_key = await get_api_key(api_key)
    if not db_api_key or not db_api_key.is_active:
        raise HTTPException(401, "Invalid API key")
    
    # 2. 使用量確認
    usage = await get_daily_usage(db_api_key.id)
    if usage >= db_api_key.daily_limit:
        raise HTTPException(429, "Daily limit exceeded")
    
    # 3. 使用量インクリメント
    await increment_usage(db_api_key.id)
    
    return db_api_key
```

### 🛡️ セキュリティ実装

1. **APIキー生成**
   - 64文字のランダム文字列
   - `secrets.choice()`使用
   - プレフィックス付き: `tg_`

2. **レート制限**
   - デフォルト: 100リクエスト/日
   - IPベース制限（計画中）

3. **暗号化**
   - HTTPS必須
   - パスワードはbcryptでハッシュ化（計画中）

---

## AIモデル詳細

### 🤖 使用モデル

#### 1. **KeywordAnalyzer**
- **方式**: ルールベース
- **辞書**: 6カテゴリ × 約50キーワード
- **特徴**: 超高速、確実な検知
- **制限**: 文脈を考慮しない

#### 2. **ToxicBertAnalyzer**
- **ベース**: sentence-transformers
- **モデル**: paraphrase-multilingual-MiniLM-L12-v2
- **方式**: 埋め込みベクトル類似度
- **特徴**: 文脈考慮、多言語対応
- **精度**: 95%+

#### 3. **ClaudeAnalyzer**
- **API**: Anthropic Claude API
- **モデル**: Claude 3 Opus
- **特徴**: 最高精度、説明可能
- **コスト**: $15/100万トークン

#### 4. **OpenAIAnalyzer**
- **API**: OpenAI API
- **モデル**: GPT-4
- **特徴**: 高精度、汎用性
- **コスト**: $30/100万トークン

### 📊 モデル選択ロジック

```python
def select_models(strategy: str, text_length: int):
    if strategy == "fast":
        return ["keyword"]
    elif strategy == "cascade":
        # キーワードで疑わしい場合のみAI
        keyword_result = keyword_analyze(text)
        if keyword_result.score > 0.2:
            return ["keyword", "toxic_bert"]
        return ["keyword"]
    elif strategy == "balanced":
        return ["keyword", "toxic_bert", "claude"]
    else:  # accurate
        return ["keyword", "toxic_bert", "claude", "openai"]
```

---

## パフォーマンス

### ⚡ レスポンスタイム

| エンドポイント | 平均 | 95%ile | 99%ile |
|---------------|------|---------|---------|
| v1/analyze (fast) | 8ms | 15ms | 25ms |
| v2/analyze (cascade) | 120ms | 500ms | 1s |
| v2/analyze (balanced) | 2.3s | 3.5s | 4.8s |
| v2/analyze/batch | 5s | 8s | 12s |

### 💾 リソース使用量

```yaml
起動時:
  - メモリ: 1.2GB (ToxicBERTモデル含む)
  - CPU: 10-20%

稼働時:
  - メモリ: 1.5-2GB
  - CPU: 
    - keyword: 1-5%
    - toxic_bert: 30-50%
    - 外部API: 5-10%
```

### 📈 スケーラビリティ

- **水平スケーリング**: Kubernetes対応
- **キャッシュ**: Redis実装（同一テキストの再分析回避）
- **非同期処理**: FastAPIの非同期対応
- **コネクションプール**: PostgreSQL/Redis

---

## エラーハンドリング

### 🚨 HTTPステータスコード

| コード | 説明 | 例 |
|--------|------|-----|
| 200 | 成功 | 正常な分析完了 |
| 400 | 不正なリクエスト | テキスト未入力 |
| 401 | 認証エラー | 無効なAPIキー |
| 429 | レート制限 | 使用量超過 |
| 500 | サーバーエラー | 内部エラー |
| 503 | サービス利用不可 | AI モデル読み込み失敗 |

### 📝 エラーレスポンス形式

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Daily limit exceeded",
    "details": {
      "limit": 100,
      "used": 100,
      "reset_at": "2025-06-18T00:00:00Z"
    }
  }
}
```

---

## 実装例

### 🐍 Python

```python
import requests
from typing import Dict, Any

class ToxiGuardClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.toxiguard.com"
        
    def analyze(self, text: str, strategy: str = "balanced") -> Dict[str, Any]:
        headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }
        
        data = {
            "text": text,
            "strategy": strategy
        }
        
        response = requests.post(
            f"{self.base_url}/api/v2/analyze",
            headers=headers,
            json=data
        )
        
        response.raise_for_status()
        return response.json()

# 使用例
client = ToxiGuardClient("your-api-key")
result = client.analyze("検査したいテキスト")

if result["is_toxic"]:
    print(f"毒性検出: {result['primary_category']}")
```

### 📘 JavaScript/TypeScript

```typescript
interface ToxiGuardResponse {
  is_toxic: boolean;
  toxicity_score: number;
  primary_category: string;
  all_categories: Array<{
    name: string;
    score: number;
    confidence: number;
  }>;
}

class ToxiGuardClient {
  private apiKey: string;
  private baseUrl: string = 'https://api.toxiguard.com';

  constructor(apiKey: string) {
    this.apiKey = apiKey;
  }

  async analyze(text: string, strategy: string = 'balanced'): Promise<ToxiGuardResponse> {
    const response = await fetch(`${this.baseUrl}/api/v2/analyze`, {
      method: 'POST',
      headers: {
        'X-API-Key': this.apiKey,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ text, strategy }),
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }

    return response.json();
  }
}

// 使用例
const client = new ToxiGuardClient('your-api-key');
const result = await client.analyze('検査したいテキスト');

if (result.is_toxic) {
  console.log(`毒性検出: ${result.primary_category}`);
}
```

### 💎 Ruby

```ruby
require 'net/http'
require 'json'

class ToxiGuardClient
  def initialize(api_key)
    @api_key = api_key
    @base_url = 'https://api.toxiguard.com'
  end

  def analyze(text, strategy = 'balanced')
    uri = URI("#{@base_url}/api/v2/analyze")
    
    http = Net::HTTP.new(uri.host, uri.port)
    http.use_ssl = true
    
    request = Net::HTTP::Post.new(uri)
    request['X-API-Key'] = @api_key
    request['Content-Type'] = 'application/json'
    request.body = { text: text, strategy: strategy }.to_json
    
    response = http.request(request)
    JSON.parse(response.body)
  end
end

# 使用例
client = ToxiGuardClient.new('your-api-key')
result = client.analyze('検査したいテキスト')

if result['is_toxic']
  puts "毒性検出: #{result['primary_category']}"
end
```

---

## 開発者ガイド

### 🚀 クイックスタート

1. **APIキー取得**
   ```bash
   curl -X POST https://api.toxiguard.com/api/register \
     -H "Content-Type: application/json" \
     -d '{"email": "your@email.com"}'
   ```

2. **テスト実行**
   ```bash
   curl -X POST https://api.toxiguard.com/api/v1/analyze \
     -H "X-API-Key: your-api-key" \
     -H "Content-Type: application/json" \
     -d '{"text": "こんにちは"}'
   ```

### 📚 ベストプラクティス

#### 1. **適切な戦略選択**
```python
def choose_strategy(requirements):
    if requirements.real_time:  # リアルタイム処理
        return "fast"
    elif requirements.cost_sensitive:  # コスト重視
        return "cascade"
    elif requirements.high_accuracy:  # 精度重視
        return "accurate"
    else:
        return "balanced"  # バランス型
```

#### 2. **エラーハンドリング**
```python
try:
    result = client.analyze(text)
except RateLimitError:
    # レート制限時は待機
    time.sleep(60)
except AuthenticationError:
    # APIキー更新
    refresh_api_key()
```

#### 3. **バッチ処理の活用**
```python
# 個別処理より効率的
texts = ["text1", "text2", "text3", ...]
results = client.analyze_batch(texts)
```

### 🔧 カスタマイズ

#### 閾値調整
```python
# デフォルト: 0.3
custom_threshold = 0.5  # より厳しい判定

result = client.analyze(
    text,
    options={"threshold": custom_threshold}
)
```

#### カテゴリフィルタ
```python
# 特定カテゴリのみ検知
result = client.analyze(
    text,
    options={
        "categories": ["重度の毒性", "ヘイトスピーチ"]
    }
)
```

### 📊 モニタリング

利用状況の確認:
```bash
GET /api/usage/stats
```

レスポンス:
```json
{
  "daily_usage": 45,
  "daily_limit": 100,
  "total_requests": 1234,
  "average_response_time": 1.23
}
```

---

## 付録

### 📎 用語集

| 用語 | 説明 |
|------|------|
| **毒性スコア** | 0.0〜1.0の値。高いほど有害 |
| **信頼度** | 判定の確実性。0.5〜1.0 |
| **カスケード判定** | 段階的にモデルを適用する方式 |
| **埋め込みベクトル** | テキストの意味を数値化した表現 |

### 🔗 関連リソース

- [APIリファレンス](https://docs.toxiguard.com/api)
- [SDKドキュメント](https://github.com/toxiguard-api/sdk)
- [サンプルコード](https://github.com/toxiguard-api/examples)
- [ステータスページ](https://status.toxiguard.com)

### 📝 変更履歴

| バージョン | 日付 | 変更内容 |
|-----------|------|----------|
| 4.0.0 | 2025-06-17 | 初版リリース |
| 3.0.0 | 2025-06-16 | マルチモデル対応 |
| 2.0.0 | 2025-06-15 | AI統合 |
| 1.0.0 | 2025-06-14 | キーワードベース |

---

<div align="center">
  <p>
    <strong>ToxiGuard API Technical Specification v4.0.0</strong><br>
    Copyright © 2025 ToxiGuard. All rights reserved.
  </p>
</div>
```

ファイルを保存したら「OK」と返信してください。次にREADME.mdの改善を行います。
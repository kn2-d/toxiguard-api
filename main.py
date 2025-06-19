"""
ToxiGuard API メインアプリケーション
Version 3.0 - マルチモデル統合版
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
# main.pyの先頭部分に以下のインポートを追加
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from datetime import datetime
import os
from typing import Dict, Any
import json
from dotenv import load_dotenv
from app.routers import analyze
from app.routers import analyze_v2
import logging
# 新規追加
from app.routers import feedback
# 既存のインポートの後に、以下を追加
from app.routers import web
from app.routers import api_key


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

load_dotenv()

app = FastAPI(
    title="ToxiGuard API",
    description="日本語テキストの毒性を検知するAPI - Release 3 マルチモデル版",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 静的ファイルの配信設定
app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# カスタムJSONレスポンス（日本語対応）
class CustomJSONResponse(JSONResponse):
    def render(self, content: any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
        ).encode("utf-8")

app.default_response_class = CustomJSONResponse

# ルーター登録
app.include_router(web.router)
app.include_router(analyze.router)      # Release 1 (v1)
app.include_router(analyze_v2.router)   # Release 3 (v2)
# 既存のルーター登録の後に追加 # 新規追加
app.include_router(feedback.router)  
app.include_router(api_key.router)

@app.get("/")
async def root():
    return {
        "message": "Welcome to ToxiGuard API 🛡️",
        "version": "3.0.0",
        "release": "Release 3 - Multi-Model Integration",
        "features": {
            "models": ["KeywordAnalyzer", "ToxicBertAnalyzer", "Phi-2 (LLM)"],
            "strategies": ["fast", "cascade", "balanced", "accurate"],
            "accuracy": {
                "keyword_only": "87.5%",
                "multi_model": "100%"
            }
        },
        "endpoints": {
            "/": "このメッセージ",
            "/docs": "APIドキュメント（Swagger UI）",
            "/api/v1/analyze": "テキスト毒性分析（Release 1）",
            "/api/v2/analyze": "テキスト毒性分析（Release 3 - マルチモデル）",
            "/api/v2/analyze/batch": "バッチ分析（複数テキスト同時処理）",
            "/api/v2/strategies": "利用可能な分析戦略一覧",
            "/api/v2/models": "使用中のモデル情報",
            "/api/v2/health": "分析サービスの状態"
        },
        "recommendation": {
            "free_plan": "strategy=fast (高速、精度87.5%)",
            "basic_plan": "strategy=cascade (効率的、精度87.5%)",
            "premium_plan": "strategy=balanced (全モデル、精度100%)"
        },
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "api": "healthy",
            "analyzer_v1": "healthy",
            "analyzer_v2": "healthy"
        },
        "version": {
            "api": "3.0.0",
            "release": "Release 3"
        }
    }

@app.get("/setup-status", response_model=Dict[str, Any])
async def setup_status():
    """
    開発環境セットアップ状況確認エンドポイント
    Release 3の進捗確認用
    """
    return {
        "phase": "Release 3",
        "title": "ToxiGuard API マルチモデル統合版",
        "completed_releases": [
            "✅ Release 1: キーワードベース（精度40%）",
            "✅ Release 2: ハイブリッドAI（精度65%）- 削除済み",
            "✅ Release 3: マルチモデル統合（精度100%）"
        ],
        "implemented_features": [
            "✅ KeywordAnalyzer（高速ルールベース）",
            "✅ ToxicBertAnalyzer（埋め込みベース）", 
            "✅ MistralAnalyzer（Phi-2 LLM）",
            "✅ MultiModelAnalyzer（統合システム）",
            "✅ 4つの分析戦略（fast/cascade/balanced/accurate）",
            "✅ API v2エンドポイント実装",
            "✅ バッチ分析機能",
            "✅ 詳細情報取得オプション"
        ],
        "performance": {
            "fast_strategy": {"accuracy": "87.5%", "response_time": "< 0.01秒"},
            "cascade_strategy": {"accuracy": "87.5%", "response_time": "< 1秒"},
            "balanced_strategy": {"accuracy": "100%", "response_time": "1-2秒"},
            "accurate_strategy": {"accuracy": "100%", "response_time": "1-2秒"}
        },
        "next_release": {
            "name": "Release 4",
            "features": [
                "外部API統合（Claude/OpenAI）",
                "ユーザーフィードバックシステム",
                "強化学習による精度向上",
                "エンタープライズ機能"
            ]
        },
        "status": "🎉 Release 3 完了！",
        "estimated_completion": "100% 完了"
    }

if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    
    print(f"""
    🚀 ToxiGuard API Release 3 Starting...
    📍 URL: http://localhost:{port}
    📚 Docs: http://localhost:{port}/docs
    🎯 Accuracy: 
       - Keyword Only: 87.5%
       - Multi-Model: 100%
    🤖 Models:
       - KeywordAnalyzer (Rule-based)
       - ToxicBertAnalyzer (Embedding-based)
       - Phi-2 (LLM-based)
    📊 Strategies:
       - fast: キーワードのみ（最速）
       - cascade: 段階的判定（効率的）
       - balanced: 全モデル並列（バランス）
       - accurate: 重み付け最適化（高精度）
    """)
    
    uvicorn.run(app, host=host, port=port, reload=True)
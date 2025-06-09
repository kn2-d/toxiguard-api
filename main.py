"""
ToxiGuard API メインアプリケーション
Version 1.0 - キーワードベース毒性検知
"""
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import os
from typing import Dict, Any
import json
from dotenv import load_dotenv
from app.routers import analyze
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

load_dotenv()

app = FastAPI(
    title="ToxiGuard API",
    description="日本語テキストの毒性を検知するAPI - Release 1",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze.router)

@app.get("/")
async def root():
    data = {
        "message": "Welcome to ToxiGuard API 🛡️",
        "version": "1.0.0",
        "release": "Release 1 - Keyword Based",
        "endpoints": {
            "/": "このメッセージ",
            "/docs": "APIドキュメント（Swagger UI）",
            "/api/v1/analyze": "テキスト毒性分析",
            "/api/v1/analyze/health": "分析サービスの状態"
        },
        "accuracy": "40%",
        "method": "Keyword matching",
        "timestamp": datetime.now().isoformat()
    }
    json_str = json.dumps(data, ensure_ascii=False)
    return Response(content=json_str, media_type="application/json; charset=utf-8")

@app.get("/health")
async def health_check():
    data = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "api": "healthy",
            "analyzer": "healthy"
        }
    }
    json_str = json.dumps(data, ensure_ascii=False)
    return Response(content=json_str, media_type="application/json; charset=utf-8")

@app.get("/setup-status", response_model=Dict[str, Any])
async def setup_status():
    """
    開発環境セットアップ状況確認エンドポイント
    Phase 4の進捗確認用
    """
    return {
        "phase": "Phase 4",
        "title": "ToxiGuard API開発環境最終準備",
        "completed_steps": [
            "✅ .gitignore ファイル作成",
            "✅ app/ ディレクトリ構造準備", 
            "✅ tests/ ディレクトリ準備",
            "✅ main.py 基本構造作成",
            "✅ FastAPI Hello World動作確認",
            "✅ API起動テスト（uvicorn）成功",
            "✅ VS Code開発環境完了"
        ],
        "remaining_steps": [
            "✅ デバッグ環境動作確認完了", 
            "✅ GitHub連携最終確認完了"
        ],
        "status": "🎉 Phase 4 完全完了！",
        "next_action": "Release 1 開発開始準備完了",
        "estimated_completion": "100% 完了"
    }

if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    
    print(f"""
    🚀 ToxiGuard API Release 1 Starting...
    📍 URL: http://localhost:{port}
    📚 Docs: http://localhost:{port}/docs
    🎯 Accuracy: 40% (Keyword-based)
    """)
    
    uvicorn.run(app, host=host, port=port, reload=True)

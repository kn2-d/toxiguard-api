#!/usr/bin/env python3
"""
ToxiGuard API - Render.com用最小限テスト版
Python互換性問題を回避するシンプル版
"""
import os
import sys
from fastapi import FastAPI
from fastapi.responses import JSONResponse

# バージョン情報
__version__ = "4.0.0-simple"

# FastAPIアプリケーション初期化
app = FastAPI(
    title="ToxiGuard API",
    description="日本語毒性検知API - Simple Test Version",
    version=__version__
)

@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {
        "name": "ToxiGuard API",
        "version": __version__,
        "status": "running",
        "python_version": sys.version,
        "endpoints": {
            "health": "/health",
            "test": "/api/test"
        }
    }

@app.get("/health")
async def health_check():
    """ヘルスチェック"""
    return {
        "status": "healthy",
        "version": __version__,
        "python": sys.version.split()[0]
    }

@app.post("/api/test")
async def test_analyze(text: str = "テスト"):
    """テスト分析（キーワードのみ）"""
    # 簡単なキーワードチェック
    toxic_keywords = ["死ね", "殺す", "クズ"]
    
    score = 0.0
    for keyword in toxic_keywords:
        if keyword in text:
            score = 0.8
            break
    
    return {
        "text": text,
        "toxicity_score": score,
        "is_toxic": score > 0.3,
        "message": "This is a test response"
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
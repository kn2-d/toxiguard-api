"""
ToxiGuard API メインアプリケーション
Version 1.0 - キーワードベース毒性検知
"""
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import os
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

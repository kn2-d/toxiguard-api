"""
Webインターフェース用ルーター
ランディングページとデモ機能を提供
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path


# テンプレートディレクトリの設定
templates_dir = Path(__file__).parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

# ルーター作成
router = APIRouter(
    tags=["web"],
    responses={404: {"description": "Not found"}},
)

@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """ランディングページを表示"""
    return templates.TemplateResponse(
        "index.html",
        {"request": request}
    )

@router.get("/demo", response_class=HTMLResponse)
async def demo_page(request: Request):
    """デモページを表示（将来的に別ページにする場合用）"""
    return templates.TemplateResponse(
        "index.html",  # 現在はホームページと同じ
        {"request": request}
    )

@router.get("/api-key", response_class=HTMLResponse)
async def api_key_page(request: Request):
    """APIキー発行ページ"""
    return templates.TemplateResponse("api_key.html", {"request": request})

@router.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    return {
        "status": "healthy",
        "service": "ToxiGuard API Web Interface",
        "version": "4.0.0"
    }
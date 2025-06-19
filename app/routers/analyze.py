"""
毒性分析APIエンドポイント
URLとその処理を定義
"""
from fastapi import APIRouter, HTTPException, status, Depends
from app.models.schemas import (
    AnalyzeRequest, 
    AnalyzeResponse,
    HealthResponse
)
from app.services.keyword_analyzer import KeywordAnalyzer
import logging

from app.middleware.auth import verify_api_key_optional
from app.models.api_key import APIKey
from typing import Optional

# ログの設定
logger = logging.getLogger(__name__)

# ルーターの作成（URLのグループ）
router = APIRouter(prefix="/api/v1", tags=["analyze"])

# グローバルでアナライザーを初期化（起動時に1回だけ）
analyzer = KeywordAnalyzer()

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_text(
    request: AnalyzeRequest,
    api_key: Optional[APIKey] = Depends(verify_api_key_optional)                   
):
    """
    テキストの毒性を分析
    
    このエンドポイントにPOSTリクエストを送ると、
    テキストの毒性を分析して結果を返します。
    
    - **text**: 分析対象のテキスト（最大5000文字）
    - **options**: オプション設定（現在は未使用）
    
    毒性スコアは0.0（安全）から1.0（非常に有害）の範囲で返されます。
    """
    try:
        # 分析サービスを呼び出す
        toxicity_score, categories, confidence = analyzer.analyze(request.text)
        
        # レスポンスを構築
        response = AnalyzeResponse(
            text=request.text,
            toxicity_score=toxicity_score,
            is_toxic=toxicity_score >= 0.5,  # 0.5以上で「有害」判定
            confidence=confidence,
            categories=categories,
            analysis_method="keyword_v1"
        )
        
        # ログに記録
        logger.info(f"Analysis completed: score={toxicity_score:.2f}")
        return response
        
    except Exception as e:
        # エラーが発生した場合
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"分析中にエラーが発生しました: {str(e)}"
        )

@router.get("/analyze/health", response_model=HealthResponse)
async def health_check():
    """
    分析サービスのヘルスチェック
    
    サービスが正常に動作しているか確認するためのエンドポイント
    """
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        analyzer_status={
            "keyword_analyzer": "active",
            "ai_analyzer": "not_implemented",  # Release 2で実装予定
            "model_count": "0"
        }
    )

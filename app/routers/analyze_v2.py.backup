"""
Release 3 API エンドポイント
マルチモデル統合版
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
import asyncio
from datetime import datetime

# マルチモデルアナライザーのインポート
from app.services.multi_model_analyzer import MultiModelAnalyzer

# ルーター作成
router = APIRouter(prefix="/api/v2", tags=["analyze_v2"])

# グローバルアナライザー（初期化は一度だけ）
analyzer = None
analyzer_lock = asyncio.Lock()


# リクエスト/レスポンスモデル
class AnalyzeRequestV2(BaseModel):
    """分析リクエスト（V2）"""
    text: str = Field(..., description="分析対象のテキスト", example="こんにちは")
    strategy: Optional[Literal["fast", "balanced", "accurate", "cascade"]] = Field(
        "balanced",
        description="分析戦略"
    )
    include_details: Optional[bool] = Field(
        False,
        description="詳細情報を含めるか"
    )


class CategoryInfo(BaseModel):
    """カテゴリ情報"""
    name: str
    score: Optional[float] = None


class ModelScore(BaseModel):
    """モデル別スコア"""
    model: str
    score: float
    response_time: float


class AnalyzeResponseV2(BaseModel):
    """分析レスポンス（V2）"""
    text: str
    toxicity_score: float = Field(..., ge=0.0, le=1.0, description="毒性スコア")
    is_toxic: bool = Field(..., description="有害判定")
    confidence: float = Field(..., ge=0.0, le=1.0, description="信頼度")
    primary_category: str = Field(..., description="主要カテゴリ")
    strategy: str = Field(..., description="使用した戦略")
    models_used: List[str] = Field(..., description="使用したモデル")
    total_time: float = Field(..., description="処理時間（秒）")
    timestamp: datetime = Field(default_factory=datetime.now, description="分析日時")
    
    # オプション：詳細情報
    individual_scores: Optional[dict] = Field(None, description="モデル別スコア")
    model_times: Optional[dict] = Field(None, description="モデル別処理時間")
    consensus: Optional[float] = Field(None, description="モデル間の一致度")
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "死ね",
                "toxicity_score": 0.85,
                "is_toxic": True,
                "confidence": 0.92,
                "primary_category": "生命への脅威",
                "strategy": "balanced",
                "models_used": ["keyword", "toxic_bert", "mistral"],
                "total_time": 1.234,
                "timestamp": "2024-03-14T10:30:00"
            }
        }


class BatchAnalyzeRequestV2(BaseModel):
    """バッチ分析リクエスト"""
    texts: List[str] = Field(..., description="分析対象のテキストリスト", max_items=100)
    strategy: Optional[Literal["fast", "balanced", "accurate", "cascade"]] = Field(
        "fast",
        description="分析戦略（バッチはデフォルトfast）"
    )


class BatchAnalyzeResponseV2(BaseModel):
    """バッチ分析レスポンス"""
    results: List[AnalyzeResponseV2]
    total_texts: int
    total_time: float
    average_time: float


# エンドポイント
@router.post("/analyze", response_model=AnalyzeResponseV2)
async def analyze_text_v2(request: AnalyzeRequestV2):
    """
    テキストの毒性を分析（マルチモデル版）
    
    戦略:
    - fast: キーワードのみ（最速）
    - cascade: 段階的判定（効率的）
    - balanced: 全モデル並列（バランス）
    - accurate: 重み付け最適化（高精度）
    """
    global analyzer
    
    # アナライザーの初期化（初回のみ）
    if analyzer is None:
        async with analyzer_lock:
            if analyzer is None:
                analyzer = MultiModelAnalyzer()
                # await analyzer.initialize()
    
    try:
        # 分析実行
        result = await analyzer.analyze_with_strategy(
    		text=request.text, 
    		strategy=request.strategy
        )
        
        # レスポンス作成
        response = AnalyzeResponseV2(
            text=request.text,
            toxicity_score=result["toxicity_score"],
            is_toxic=result["is_toxic"],
            confidence=result["confidence"],
            primary_category=result.get("primary_category", "不明"),
            strategy=result.get("strategy", request.strategy),
            models_used=result.get("models_used", []),
            total_time=result.get("total_time", 0.0)
        )
        
        # 詳細情報を含める場合
        if request.include_details:
            response.individual_scores = result.get("individual_scores")
            response.model_times = result.get("model_times")
            response.consensus = result.get("consensus")
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/batch", response_model=BatchAnalyzeResponseV2)
async def analyze_batch_v2(request: BatchAnalyzeRequestV2):
    """
    複数テキストの一括分析
    
    最大100件まで同時処理可能
    """
    global analyzer
    
    # アナライザーの初期化
    if analyzer is None:
        async with analyzer_lock:
            if analyzer is None:
                analyzer = MultiModelAnalyzer()
                # await analyzer.initialize()
    
    try:
        import time
        start_time = time.time()
        
        # 並列分析
        tasks = []
        for text in request.texts:
            task = analyzer.analyze_with_strategy(text=text, strategy=request.strategy)
            tasks.append(task)
        
        results_data = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 結果整形
        results = []
        for i, (text, result) in enumerate(zip(request.texts, results_data)):
            if isinstance(result, Exception):
                # エラーの場合はデフォルト値
                results.append(AnalyzeResponseV2(
                    text=text,
                    toxicity_score=0.0,
                    is_toxic=False,
                    confidence=0.0,
                    primary_category="エラー",
                    strategy=request.strategy,
                    models_used=[],
                    total_time=0.0
                ))
            else:
                results.append(AnalyzeResponseV2(
                    text=text,
                    toxicity_score=result["toxicity_score"],
                    is_toxic=result["is_toxic"],
                    confidence=result["confidence"],
                    primary_category=result.get("primary_category", "不明"),
                    strategy=result.get("strategy", request.strategy),
                    models_used=result.get("models_used", []),
                    total_time=result.get("total_time", 0.0)
                ))
        
        total_time = time.time() - start_time
        
        return BatchAnalyzeResponseV2(
            results=results,
            total_texts=len(request.texts),
            total_time=total_time,
            average_time=total_time / len(request.texts) if request.texts else 0
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/strategies")
async def get_strategies():
    """
    利用可能な分析戦略の一覧
    """
    return {
        "strategies": [
            {
                "name": "fast",
                "description": "キーワードのみ使用。最速だが精度は低め",
                "expected_accuracy": "85-90%",
                "response_time": "< 0.01秒"
            },
            {
                "name": "cascade",
                "description": "段階的判定。高信頼度なら早期終了",
                "expected_accuracy": "85-90%",
                "response_time": "0.01-1秒"
            },
            {
                "name": "balanced",
                "description": "全モデル並列実行。バランス型",
                "expected_accuracy": "95-100%",
                "response_time": "1-2秒"
            },
            {
                "name": "accurate",
                "description": "重み付け最適化。最高精度",
                "expected_accuracy": "95-100%",
                "response_time": "1-2秒"
            }
        ]
    }


@router.get("/models")
async def get_models():
    """
    使用中のモデル情報
    """
    global analyzer
    
    if analyzer is None:
        return {"models": [], "status": "not_initialized"}
    
    models_info = []
    for name in analyzer.models.keys():
        model_info = {
            "name": name,
            "weight": analyzer.weights.get(name, 0.0),
            "status": "active"
        }
        
        if name == "keyword":
            model_info["type"] = "rule_based"
            model_info["description"] = "キーワードベース高速判定"
        elif name == "toxic_bert":
            model_info["type"] = "embedding_based"
            model_info["description"] = "文埋め込みベース高精度判定"
        elif name == "mistral":
            model_info["type"] = "llm_based"
            model_info["description"] = "大規模言語モデル（Phi-2）"
            
        models_info.append(model_info)
    
    return {
        "models": models_info,
        "total_models": len(models_info),
        "status": "initialized"
    }


@router.get("/stats")
async def get_stats():
    """
    分析統計情報
    """
    global analyzer
    
    if analyzer is None:
        return {"status": "not_initialized"}
    
    return {
        "total_requests": analyzer.stats.get("total_requests", 0),
        "model_performance": analyzer.stats.get("model_performance", {}),
        "status": "active"
    }


# ヘルスチェック
@router.get("/health")
async def health_check():
    """
    APIヘルスチェック
    """
    global analyzer
    
    return {
        "status": "healthy",
        "version": "2.0",
        "analyzer_initialized": analyzer is not None,
        "models_available": list(analyzer.models.keys()) if analyzer else []
    }
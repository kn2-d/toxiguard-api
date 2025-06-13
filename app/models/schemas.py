"""
リクエスト/レスポンスのデータモデル定義
このファイルでAPIの入出力の形を決めます
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime

class AnalyzeRequest(BaseModel):
    """
    テキスト分析リクエスト
    ユーザーから送られてくるデータの形
    """
    # テキストは必須、1文字以上5000文字以下
    text: str = Field(..., min_length=1, max_length=5000, description="分析対象テキスト")
    # オプションは任意（今は使わない）
    options: Optional[Dict] = Field(default={}, description="オプション設定")
    
    class Config:
        # Swagger UIに表示される例
        json_schema_extra = {
            "example": {
                "text": "これは分析したいテキストです",
                "options": {"detailed": True}
            }
        }

class ToxicityCategory(BaseModel):
    """
    毒性カテゴリ
    「暴言」「ヘイトスピーチ」などの分類結果
    """
    # カテゴリ名（例：「暴言」）
    name: str = Field(..., description="カテゴリ名")
    # スコア（0.0〜1.0）
    score: float = Field(..., ge=0, le=1, description="カテゴリスコア")
    # 見つかったキーワードのリスト
    keywords_found: List[str] = Field(default=[], description="検出されたキーワード")

class AnalyzeResponse(BaseModel):
    """
    テキスト分析レスポンス
    APIが返す結果の形
    """
    # 分析したテキスト（確認用）
    text: str = Field(..., description="分析対象テキスト")
    # 総合毒性スコア（0.0=安全、1.0=危険）
    toxicity_score: float = Field(..., ge=0, le=1, description="総合毒性スコア（0-1）")
    # 毒性判定（0.5以上でTrue）
    is_toxic: bool = Field(..., description="毒性判定（0.5以上でTrue）")
    # 判定の信頼度
    confidence: float = Field(..., ge=0, le=1, description="判定の信頼度")
    # カテゴリ別の結果
    categories: List[ToxicityCategory] = Field(..., description="カテゴリ別スコア")
    # 使用した分析手法
    analysis_method: str = Field(default="keyword_v1", description="使用した分析手法")
    # 分析日時
    timestamp: datetime = Field(default_factory=datetime.now, description="分析日時")
    
    class Config:
        # Swagger UIに表示される例
        json_schema_extra = {
            "example": {
                "text": "分析されたテキスト",
                "toxicity_score": 0.75,
                "is_toxic": True,
                "confidence": 0.8,
                "categories": [
                    {
                        "name": "暴言",
                        "score": 0.9,
                        "keywords_found": ["死ね"]
                    }
                ],
                "analysis_method": "keyword_v1",
                "timestamp": "2024-06-06T12:00:00"
            }
        }

class HealthResponse(BaseModel):
    """
    ヘルスチェックレスポンス
    APIが正常に動いているか確認用
    """
    status: str = "healthy"
    version: str = "1.0.0"
    analyzer_status: Dict[str, str] = Field(default_factory=dict)

# ===== Feedback Schemas（最後に追加） =====

class FeedbackCreate(BaseModel):
    """フィードバック作成用スキーマ"""
    text: str
    model_name: str
    strategy: Optional[str] = None
    original_score: float
    original_is_toxic: bool
    original_categories: Optional[List[str]] = None
    original_confidence: Optional[float] = None
    user_is_toxic: bool
    user_category: Optional[str] = None
    user_severity: Optional[float] = None
    feedback_reason: Optional[str] = None
    session_id: Optional[str] = None


class FeedbackResponse(BaseModel):
    """フィードバックレスポンス用スキーマ"""
    id: int
    text: str
    model_name: str
    original_score: float
    original_is_toxic: bool
    user_is_toxic: bool
    created_at: datetime
    message: str = "フィードバックを受け付けました"
    
    class Config:
        from_attributes = True


class FeedbackStats(BaseModel):
    """フィードバック統計用スキーマ"""
    total_feedbacks: int
    accuracy: float
    false_positives: int
    false_negatives: int
    model_performance: Dict[str, float]
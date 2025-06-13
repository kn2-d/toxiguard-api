# app/routers/feedback.py

from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.feedback import Feedback, ModelPerformance
from app.models.schemas import FeedbackCreate, FeedbackResponse, FeedbackStats

router = APIRouter(prefix="/api/v2/feedback", tags=["feedback"])


@router.post("/", response_model=FeedbackResponse)
async def create_feedback(
    feedback: FeedbackCreate,
    db: Session = Depends(get_db)
) -> FeedbackResponse:
    """ユーザーフィードバックを保存"""
    try:
        # フィードバックデータをデータベースに保存
        db_feedback = Feedback(
            text=feedback.text,
            model_name=feedback.model_name,
            strategy=feedback.strategy,
            original_score=feedback.original_score,
            original_is_toxic=feedback.original_is_toxic,
            original_categories=feedback.original_categories,
            original_confidence=feedback.original_confidence,
            user_is_toxic=feedback.user_is_toxic,
            user_category=feedback.user_category,
            user_severity=feedback.user_severity,
            feedback_reason=feedback.feedback_reason,
            session_id=feedback.session_id
        )
        
        db.add(db_feedback)
        db.commit()
        db.refresh(db_feedback)
        
        # 精度が変わったかチェック（同意しない場合）
        if feedback.original_is_toxic != feedback.user_is_toxic:
            accuracy_impact = "判定精度の改善に活用されます"
        else:
            accuracy_impact = "判定が正しかったことを確認しました"
        
        return FeedbackResponse(
            id=db_feedback.id,
            text=db_feedback.text,
            model_name=db_feedback.model_name,
            original_score=db_feedback.original_score,
            original_is_toxic=db_feedback.original_is_toxic,
            user_is_toxic=db_feedback.user_is_toxic,
            created_at=db_feedback.created_at,
            message=f"フィードバックを受け付けました。{accuracy_impact}"
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"フィードバック保存エラー: {str(e)}")


@router.get("/stats", response_model=FeedbackStats)
async def get_feedback_stats(
    model_name: Optional[str] = Query(None, description="モデル名でフィルタ"),
    days: int = Query(7, description="過去何日間の統計を取得するか"),
    db: Session = Depends(get_db)
) -> FeedbackStats:
    """フィードバック統計を取得"""
    try:
        # 期間の計算
        since = datetime.now() - timedelta(days=days)
        
        # クエリの基本条件
        query = db.query(Feedback).filter(Feedback.created_at >= since)
        
        # モデル名でフィルタ
        if model_name:
            query = query.filter(Feedback.model_name == model_name)
        
        feedbacks = query.all()
        total = len(feedbacks)
        
        if total == 0:
            return FeedbackStats(
                total_feedbacks=0,
                accuracy=0.0,
                false_positives=0,
                false_negatives=0,
                model_performance={}
            )
        
        # 統計計算
        correct = sum(1 for f in feedbacks if f.original_is_toxic == f.user_is_toxic)
        false_positives = sum(1 for f in feedbacks if f.original_is_toxic and not f.user_is_toxic)
        false_negatives = sum(1 for f in feedbacks if not f.original_is_toxic and f.user_is_toxic)
        
        # モデル別の精度計算
        model_performance = {}
        models = set(f.model_name for f in feedbacks)
        
        for model in models:
            model_feedbacks = [f for f in feedbacks if f.model_name == model]
            model_correct = sum(1 for f in model_feedbacks if f.original_is_toxic == f.user_is_toxic)
            model_performance[model] = model_correct / len(model_feedbacks) if model_feedbacks else 0.0
        
        return FeedbackStats(
            total_feedbacks=total,
            accuracy=correct / total,
            false_positives=false_positives,
            false_negatives=false_negatives,
            model_performance=model_performance
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"統計取得エラー: {str(e)}")


@router.get("/recent", response_model=List[FeedbackResponse])
async def get_recent_feedbacks(
    limit: int = Query(10, ge=1, le=100),
    model_name: Optional[str] = None,
    db: Session = Depends(get_db)
) -> List[FeedbackResponse]:
    """最近のフィードバックを取得"""
    query = db.query(Feedback)
    
    if model_name:
        query = query.filter(Feedback.model_name == model_name)
    
    feedbacks = query.order_by(Feedback.created_at.desc()).limit(limit).all()
    
    return [
        FeedbackResponse(
            id=f.id,
            text=f.text,
            model_name=f.model_name,
            original_score=f.original_score,
            original_is_toxic=f.original_is_toxic,
            user_is_toxic=f.user_is_toxic,
            created_at=f.created_at
        )
        for f in feedbacks
    ]
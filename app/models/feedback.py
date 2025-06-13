# app/models/feedback.py

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, JSON
from sqlalchemy.sql import func
from app.database import Base


class Feedback(Base):
    """ユーザーフィードバックを保存するテーブル"""
    __tablename__ = "feedbacks"
    
    # 主キー
    id = Column(Integer, primary_key=True, index=True)
    
    # フィードバック内容
    text = Column(Text, nullable=False)  # 判定されたテキスト
    model_name = Column(String(50), nullable=False)  # 使用したモデル名
    strategy = Column(String(50))  # 使用した戦略
    
    # 元の判定結果
    original_score = Column(Float, nullable=False)  # 元のスコア
    original_is_toxic = Column(Boolean, nullable=False)  # 元の判定
    original_categories = Column(JSON)  # 検出されたカテゴリ
    original_confidence = Column(Float)  # 信頼度
    
    # ユーザーフィードバック
    user_is_toxic = Column(Boolean, nullable=False)  # ユーザーの判定
    user_category = Column(String(50))  # ユーザーが指定したカテゴリ
    user_severity = Column(Float)  # ユーザーが指定した深刻度
    feedback_reason = Column(Text)  # フィードバックの理由
    
    # メタデータ
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    user_id = Column(String(100))  # 将来の認証システム用
    session_id = Column(String(100))  # セッション追跡用
    
    def __repr__(self):
        return f"<Feedback(id={self.id}, text='{self.text[:30]}...', model={self.model_name})>"


class ModelPerformance(Base):
    """モデルの性能を追跡するテーブル"""
    __tablename__ = "model_performances"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # モデル情報
    model_name = Column(String(50), nullable=False)
    date = Column(DateTime(timezone=True), default=func.now())
    
    # 性能指標
    accuracy = Column(Float)  # 精度
    precision = Column(Float)  # 適合率
    recall = Column(Float)  # 再現率
    f1_score = Column(Float)  # F1スコア
    
    # 詳細統計
    total_feedbacks = Column(Integer, default=0)  # フィードバック総数
    correct_predictions = Column(Integer, default=0)  # 正解数
    false_positives = Column(Integer, default=0)  # 偽陽性
    false_negatives = Column(Integer, default=0)  # 偽陰性
    
    # カテゴリ別性能（JSON形式）
    category_performance = Column(JSON)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
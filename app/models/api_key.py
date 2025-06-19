"""
APIキー管理モデル
本番環境でもそのまま使用可能な設計
"""
from datetime import datetime
from typing import Optional
import secrets
import string
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Date, UniqueConstraint, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class APIKey(Base):
    """APIキー管理テーブル"""
    __tablename__ = "api_keys"
    
    # 主キー
    id = Column(Integer, primary_key=True, index=True)
    
    # メールアドレス（ユニークではない：同じメールで複数キー発行可能）
    email = Column(String(255), nullable=False, index=True)
    
    # APIキー（ユニーク、64文字）
    api_key = Column(String(64), unique=True, nullable=False, index=True)
    
    # 作成日時
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 1日あたりの使用制限（デフォルト100回）
    daily_limit = Column(Integer, default=100)
    
    # 有効/無効フラグ
    is_active = Column(Boolean, default=True)
    
    # 使用履歴とのリレーション
    usage_records = relationship("APIUsage", back_populates="api_key_record", cascade="all, delete-orphan")
    
    @staticmethod
    def generate_api_key() -> str:
        """セキュアなAPIキーを生成"""
        # 英数字で64文字のランダム文字列
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(64))


class APIUsage(Base):
    """API使用量追跡テーブル"""
    __tablename__ = "api_usage"
    
    # 主キー
    id = Column(Integer, primary_key=True, index=True)
    
    # APIキーへの外部キー
    api_key_id = Column(Integer, ForeignKey("api_keys.id"), nullable=False)
    
    # 使用日（日別集計用）
    date = Column(Date, nullable=False)
    
    # その日のリクエスト数
    request_count = Column(Integer, default=0)
    
    # APIキーとのリレーション
    api_key_record = relationship("APIKey", back_populates="usage_records")
    
    # 複合ユニーク制約（同じAPIキー・日付の組み合わせは1レコードのみ）
    __table_args__ = (
        UniqueConstraint('api_key_id', 'date', name='_api_key_date_uc'),
    )
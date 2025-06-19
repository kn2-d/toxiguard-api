# app/database.py

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# .envファイルから環境変数を読み込み
load_dotenv()

# データベースURL（.envから読み込むか、デフォルト値を使用）
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/toxiguard_db")

# SQLAlchemyエンジンの作成
engine = create_engine(DATABASE_URL, echo=False)  # echo=Trueでデバッグ用SQL表示

# セッションメーカーの作成
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ベースクラスの作成
Base = declarative_base()

# データベース接続を取得する関数
def get_db():
    """データベースセッションを提供するジェネレータ"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
# 既存のコードの最後に以下を追加

def init_db():
    """データベース初期化（テーブル作成）"""
    # APIキーモデルをインポート（循環参照を避けるため関数内で）
    from app.models.api_key import APIKey, APIUsage
    
    # 全テーブルを作成
    Base.metadata.create_all(bind=engine)
    print("データベーステーブルを作成しました")
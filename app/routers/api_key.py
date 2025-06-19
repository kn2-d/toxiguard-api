"""
APIキー発行エンドポイント
簡易的な実装（メール確認なし）
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Dict, Any

from app.database import get_db
from app.models.api_key import APIKey

# ルーターの作成
router = APIRouter(
    prefix="/api",
    tags=["API Key Management"]
)

# リクエスト/レスポンスモデル
class RegisterRequest(BaseModel):
    """APIキー登録リクエスト"""
    email: EmailStr  # メールアドレス検証付き

class RegisterResponse(BaseModel):
    """APIキー登録レスポンス"""
    api_key: str
    email: str
    daily_limit: int
    created_at: datetime
    message: str

@router.post("/register", response_model=RegisterResponse)
async def register_api_key(
    request: RegisterRequest,
    db: Session = Depends(get_db)
) -> RegisterResponse:
    """
    メールアドレスを受け取ってAPIキーを発行
    
    - 同じメールアドレスで複数のAPIキー発行可能
    - 1日100回の制限付き
    - メール確認なし（簡易版）
    """
    try:
        # APIキーを生成
        new_api_key = APIKey.generate_api_key()
        
        # データベースに保存
        api_key_record = APIKey(
            email=request.email,
            api_key=new_api_key,
            daily_limit=100  # 無料プラン
        )
        
        db.add(api_key_record)
        db.commit()
        db.refresh(api_key_record)
        
        # レスポンスを返す
        return RegisterResponse(
            api_key=api_key_record.api_key,
            email=api_key_record.email,
            daily_limit=api_key_record.daily_limit,
            created_at=api_key_record.created_at,
            message="APIキーが正常に発行されました。このキーを安全に保管してください。"
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"APIキーの発行中にエラーが発生しました: {str(e)}"
        )

@router.get("/check/{api_key}")
async def check_api_key(
    api_key: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    APIキーの有効性を確認（デバッグ用）
    """
    # APIキーを検索
    api_key_record = db.query(APIKey).filter(
        APIKey.api_key == api_key,
        APIKey.is_active == True
    ).first()
    
    if not api_key_record:
        raise HTTPException(
            status_code=404,
            detail="APIキーが見つかりません"
        )
    
    return {
        "valid": True,
        "email": api_key_record.email,
        "daily_limit": api_key_record.daily_limit,
        "created_at": api_key_record.created_at,
        "is_active": api_key_record.is_active
    }
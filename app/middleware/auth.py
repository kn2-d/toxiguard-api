"""
APIキー認証ミドルウェア
発行されたAPIキーでAPIアクセスを制御
"""
from fastapi import HTTPException, Security, Depends
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
from datetime import date
from typing import Optional

from app.database import get_db
from app.models.api_key import APIKey, APIUsage

# APIキーヘッダーの定義
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(
    api_key: Optional[str] = Security(api_key_header),
    db: Session = Depends(get_db)
) -> APIKey:
    """
    APIキーを検証し、使用量をチェック
    
    Returns:
        APIKey: 有効なAPIキーレコード
    
    Raises:
        HTTPException: 無効なキーまたは制限超過
    """
    # APIキーが提供されていない場合
    if not api_key:
        raise HTTPException(
            status_code=403,
            detail="APIキーが必要です。X-API-Keyヘッダーに設定してください。"
        )
    
    # APIキーをデータベースで検索
    api_key_record = db.query(APIKey).filter(
        APIKey.api_key == api_key,
        APIKey.is_active == True
    ).first()
    
    if not api_key_record:
        raise HTTPException(
            status_code=403,
            detail="無効なAPIキーです"
        )
    
    # 今日の使用量を確認
    today = date.today()
    usage = db.query(APIUsage).filter(
        APIUsage.api_key_id == api_key_record.id,
        APIUsage.date == today
    ).first()
    
    # 使用量レコードがない場合は作成
    if not usage:
        usage = APIUsage(
            api_key_id=api_key_record.id,
            date=today,
            request_count=0
        )
        db.add(usage)
        db.commit()
    
    # 使用制限をチェック
    if usage.request_count >= api_key_record.daily_limit:
        raise HTTPException(
            status_code=429,
            detail=f"1日の使用制限（{api_key_record.daily_limit}回）に達しました。明日またお試しください。"
        )
    
    # 使用回数を増やす
    usage.request_count += 1
    db.commit()
    
    return api_key_record

# オプション：開発環境では認証をスキップ
async def verify_api_key_optional(
    api_key: Optional[str] = Security(api_key_header),
    db: Session = Depends(get_db)
) -> Optional[APIKey]:
    """
    APIキーがある場合のみ検証（開発用）
    """
    if not api_key:
        return None
    
    return await verify_api_key(api_key, db)
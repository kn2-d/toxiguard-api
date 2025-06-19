"""APIキー関連のテーブルを作成するスクリプト"""
import sys
import os

# プロジェクトのルートディレクトリをPythonパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import init_db

if __name__ == "__main__":
    print("APIキーテーブルを作成中...")
    init_db()
    print("完了！")
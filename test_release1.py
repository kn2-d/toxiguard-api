"""
Release 1のテストスクリプト（簡易版）
"""
import requests
import json

# APIのベースURL
BASE_URL = "http://localhost:8000"

# テストケース
test_cases = [
    "今日はいい天気ですね",
    "死ね",
    "バカじゃないの",
    "素晴らしい作品をありがとうございます",
    "マジでムカつく、消えろ",
    "ちょっと違うんじゃないかな",
]

def test_api():
    """APIテスト実行"""
    print("🚀 ToxiGuard API Release 1 テスト開始")
    print("=" * 50)
    
    # ヘルスチェック
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✅ APIは正常に動作しています")
        else:
            print("❌ APIが応答しません")
            return
    except:
        print("❌ APIに接続できません。サーバーを起動してください。")
        print("別のターミナルで: uvicorn main:app --reload")
        return
    
    print("\n📊 毒性分析テスト")
    print("=" * 50)
    
    # 各テストケースを実行
    for text in test_cases:
        response = requests.post(
            f"{BASE_URL}/api/v1/analyze",
            json={"text": text}
        )
        result = response.json()
        
        print(f"\n📝 テキスト: {text}")
        print(f"📊 毒性スコア: {result['toxicity_score']:.2f}")
        print(f"🚦 判定: {'🔴 有害' if result['is_toxic'] else '🟢 安全'}")
        print(f"💯 信頼度: {result['confidence']:.2f}")
        
        if result['categories']:
            print("📋 検出カテゴリ:")
            for cat in result['categories']:
                print(f"  - {cat['name']}: {cat['score']:.2f}")
        print("-" * 50)
    
    print("\n✅ テスト完了！")

if __name__ == "__main__":
    test_api()

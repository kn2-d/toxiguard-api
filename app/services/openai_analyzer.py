"""
OpenAI API を使用した毒性検知サービス
GPT-4o-miniまたはGPT-3.5-turboを使用して高精度な日本語毒性判定を実行
"""

import os
import json
import time
import asyncio
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import openai
from openai import OpenAI
from dotenv import load_dotenv
import concurrent.futures
import logging

# ロガーの設定
logger = logging.getLogger(__name__)

# スキーマのインポート
from app.models.schemas import ToxicityCategory

# 環境変数の読み込み
load_dotenv()


class OpenAIAnalyzer:
    """OpenAI APIを使用した毒性分析クラス"""
    
    def __init__(self):
        """初期化処理"""
        # APIキーの設定
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        
        # OpenAIクライアントの初期化
        self.client = OpenAI(api_key=api_key)
        
        # モデル設定（コスト効率を考慮してgpt-4o-miniを使用）
        self.model = "gpt-4o-mini"  # または "gpt-3.5-turbo"
        
        # キャッシュの初期化
        self.cache = {}
        self.max_cache_size = 100
        
        # カテゴリ定義
        self.categories = {
            "severe_toxicity": "重度の毒性（死ね、殺す等）",
            "hate_speech": "ヘイトスピーチ（差別的発言）",
            "violence": "暴力的表現",
            "sexual": "性的な内容",
            "discrimination": "差別的表現",
            "mild_toxicity": "軽度の毒性（バカ、アホ等）"
        }
        
        # プロンプトテンプレート
        self.system_prompt = """あなたは日本語の毒性検知の専門家です。
与えられたテキストを分析し、以下の形式でJSONを返してください。

{
    "toxicity_score": 0.0-1.0の数値（全体的な毒性スコア）,
    "is_toxic": true/false（0.3以上で有害と判定）,
    "confidence": 0.0-1.0の数値（判定の確信度）,
    "categories": [
        {
            "name": "カテゴリ名",
            "score": 0.0-1.0の数値,
            "detected": true/false,
            "keywords": ["検出されたキーワード"]
        }
    ],
    "reasoning": "判定理由の簡潔な説明"
}

カテゴリ:
- severe_toxicity: 重度の毒性（死ね、殺す等）
- hate_speech: ヘイトスピーチ（きもい、クズ等）
- violence: 暴力的表現
- sexual: 性的な内容
- discrimination: 差別的表現
- mild_toxicity: 軽度の毒性（バカ、アホ等）

重要な注意事項:
- 文脈を考慮して判定すること
- 教育的・説明的な文脈では毒性を低く評価
- 日本語の微妙なニュアンスを理解すること
"""
    
    async def analyze_text(self, text: str) -> Dict:
        """
        テキストの毒性を分析
        
        Args:
            text: 分析対象のテキスト
            
        Returns:
            分析結果の辞書
        """
        start_time = time.time()
        
        # キャッシュチェック
        if text in self.cache:
            cached_result = self.cache[text].copy()
            cached_result['cache_hit'] = True
            cached_result['processing_time'] = 0.001
            return cached_result
        
        try:
            # OpenAI APIを呼び出し
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": f"以下のテキストの毒性を分析してください:\n\n{text}"}
                ],
                temperature=0.1,  # 一貫性のため低めに設定
                max_tokens=500,
                response_format={"type": "json_object"}
            )
            
            # レスポンスの解析
            result_text = response.choices[0].message.content
            result_data = json.loads(result_text)
            
            # 結果の構造化
            categories = []
            for cat_data in result_data.get('categories', []):
                if cat_data.get('detected', False):
                    category = ToxicityCategory(
                        name=cat_data['name'],
                        score=cat_data.get('score', 0.0),
                        keywords_found=cat_data.get('keywords', [])
                    )
                    categories.append({
                        'name': category.name,
                        'score': category.score,
                        'keywords_found': category.keywords_found
                    })
            
            # 最終結果の構築
            result = {
                'score': result_data.get('toxicity_score', 0.0),
                'is_toxic': result_data.get('is_toxic', False),
                'confidence': result_data.get('confidence', 0.5),
                'categories': categories,
                'model': self.model,
                'reasoning': result_data.get('reasoning', ''),
                'processing_time': time.time() - start_time,
                'cache_hit': False,
                'timestamp': datetime.now().isoformat()
            }
            
            # キャッシュに保存
            if len(self.cache) >= self.max_cache_size:
                # 最も古いエントリを削除
                oldest_key = min(self.cache.keys(), 
                               key=lambda k: self.cache[k].get('timestamp', ''))
                del self.cache[oldest_key]
            
            self.cache[text] = result.copy()
            
            return result
            
        except Exception as e:
            print(f"OpenAI API error: {str(e)}")
            # エラー時のフォールバック
            return {
                'score': 0.0,
                'is_toxic': False,
                'confidence': 0.0,
                'categories': [],
                'model': self.model,
                'error': str(e),
                'processing_time': time.time() - start_time,
                'cache_hit': False,
                'timestamp': datetime.now().isoformat()
            }
    
    def analyze(self, text: str) -> Tuple[float, List[ToxicityCategory], float]:
        """同期版の分析メソッド（MultiModelAnalyzer互換）"""
        try:
            # 既存のイベントループをチェック
            try:
                loop = asyncio.get_running_loop()
                # イベントループが実行中の場合、別スレッドで実行
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.analyze_text(text))
                    result = future.result()
            except RuntimeError:
                # イベントループが実行中でない場合
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(self.analyze_text(text))
                finally:
                    loop.close()
            
            # 結果の変換
            score = result.get('score', 0.0)
            confidence = result.get('confidence', 0.5)
            
            # カテゴリを変換
            categories = []
            for cat_detail in result.get('categories_detail', []):
                category = ToxicityCategory(
                    name=cat_detail['name'],
                    score=cat_detail['score'],
                    keywords_found=cat_detail.get('keywords', [])
                )
                categories.append(category)
            
            return score, categories, confidence
            
        except Exception as e:
            logger.error(f"OpenAI分析エラー: {str(e)}")
            return 0.0, [], 0.0
    
    def get_model_info(self) -> Dict:
        """モデル情報を取得"""
        return {
            'name': 'OpenAI',
            'model': self.model,
            'version': '1.0.0',
            'capabilities': [
                '高精度な文脈理解',
                '微妙なニュアンスの検出',
                '多言語対応（日本語最適化）',
                'カテゴリ別詳細分析'
            ],
            'cost_per_1k_tokens': {
                'gpt-4o-mini': {'input': 0.00015, 'output': 0.0006},
                'gpt-3.5-turbo': {'input': 0.0005, 'output': 0.0015}
            }
        }


# テスト用コード
if __name__ == "__main__":
    import asyncio
    
    async def test_openai_analyzer():
        """OpenAIAnalyzerのテスト"""
        print("=== OpenAI Analyzer Test ===")
        
        # アナライザーの初期化
        try:
            analyzer = OpenAIAnalyzer()
            print(f"✅ Initialized with model: {analyzer.model}")
        except ValueError as e:
            print(f"❌ Initialization error: {e}")
            print("Please set OPENAI_API_KEY in .env file")
            return
        
        # テストケース
        test_cases = [
            "こんにちは、良い天気ですね",
            "バカじゃないの",
            "死ね",
            "あなたはクズだ",
            "素晴らしい一日をお過ごしください"
        ]
        
        print("\n--- Testing analyze_text method ---")
        for text in test_cases:
            print(f"\nテキスト: '{text}'")
            result = await analyzer.analyze_text(text)
            
            print(f"スコア: {result['score']:.3f}")
            print(f"有害判定: {'🚨 有害' if result['is_toxic'] else '✅ 安全'}")
            print(f"信頼度: {result['confidence']:.3f}")
            print(f"処理時間: {result['processing_time']:.3f}秒")
            
            if result.get('categories'):
                print("カテゴリ:")
                for cat in result['categories']:
                    print(f"  - {cat['name']}: {cat['score']:.3f}")
            
            if result.get('reasoning'):
                print(f"理由: {result['reasoning']}")
        
        print("\n--- Testing analyze method (sync) ---")
        # 同期メソッドのテストは別途実行する必要があるため、ここではスキップ
        print("注: analyzeメソッドのテストは、非同期コンテキスト外で実行してください")
        
        # モデル情報
        print("\n--- Model Info ---")
        info = analyzer.get_model_info()
        print(json.dumps(info, indent=2, ensure_ascii=False))
    
    # テスト実行
    asyncio.run(test_openai_analyzer())
"""
Google Perspective API を使用した毒性検知サービス
毒性検知に特化したGoogleのAPIを使用して高精度な判定を実行
"""

import os
import time
import asyncio
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from googleapiclient import discovery
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
import json

# スキーマのインポート
from app.models.schemas import ToxicityCategory

# 環境変数の読み込み
load_dotenv()


class GoogleAnalyzer:
    """Google Perspective APIを使用した毒性分析クラス"""
    
    def __init__(self):
        """初期化処理"""
        # APIキーの設定
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is not set")
        
        # Perspective APIクライアントの初期化
        self.client = discovery.build(
            "commentanalyzer",
            "v1alpha1",
            developerKey=api_key,
            discoveryServiceUrl="https://commentanalyzer.googleapis.com/$discovery/rest?version=v1alpha1",
            static_discovery=False,
        )
        
        # キャッシュの初期化
        self.cache = {}
        self.max_cache_size = 100
        
        # 分析する属性の定義
        self.attributes = {
            'TOXICITY': 'severe_toxicity',  # 全体的な毒性
            'SEVERE_TOXICITY': 'severe_toxicity',  # 重度の毒性
            'IDENTITY_ATTACK': 'hate_speech',  # アイデンティティ攻撃
            'INSULT': 'hate_speech',  # 侮辱
            'PROFANITY': 'mild_toxicity',  # 不適切な言葉
            'THREAT': 'violence',  # 脅迫
        }
        
        # カテゴリマッピング
        self.category_mapping = {
            'severe_toxicity': '重度の毒性',
            'hate_speech': 'ヘイトスピーチ',
            'violence': '暴力的表現',
            'sexual': '性的な内容',
            'discrimination': '差別的表現',
            'mild_toxicity': '軽度の毒性'
        }
    
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
            # リクエストの構築
            analyze_request = {
                'comment': {'text': text},
                'requestedAttributes': {
                    attr: {} for attr in self.attributes.keys()
                },
                'languages': ['ja'],  # 日本語を指定
                'doNotStore': True    # プライバシー保護
            }
            
            # Google Perspective APIを呼び出し（非同期）
            response = await asyncio.to_thread(
                self.client.comments().analyze(body=analyze_request).execute
            )
            
            # スコアの抽出と処理
            scores = response.get('attributeScores', {})
            
            # カテゴリ別スコアの集計
            category_scores = {}
            max_score = 0.0
            
            for attr, category in self.attributes.items():
                if attr in scores:
                    score = scores[attr]['summaryScore']['value']
                    if category not in category_scores:
                        category_scores[category] = []
                    category_scores[category].append(score)
                    max_score = max(max_score, score)
            
            # カテゴリの構築
            categories = []
            detected_keywords = []  # Perspective APIはキーワードを返さない
            
            for category, score_list in category_scores.items():
                avg_score = sum(score_list) / len(score_list)
                if avg_score > 0.2:  # 閾値以上のカテゴリのみ
                    category_obj = ToxicityCategory(
                        name=category,
                        score=avg_score,
                        keywords_found=[]  # Perspective APIはキーワードを提供しない
                    )
                    categories.append({
                        'name': category_obj.name,
                        'score': category_obj.score,
                        'keywords_found': category_obj.keywords_found
                    })
            
            # 全体スコアの計算（TOXICITYスコアを優先）
            overall_score = scores.get('TOXICITY', {}).get('summaryScore', {}).get('value', max_score)
            
            # 信頼度の計算（スコアの分散を基に）
            if category_scores:
                all_scores = [s for scores in category_scores.values() for s in scores]
                score_variance = sum((s - overall_score) ** 2 for s in all_scores) / len(all_scores)
                confidence = max(0.5, min(1.0, 1.0 - score_variance))
            else:
                confidence = 0.5
            
            # 最終結果の構築
            result = {
                'score': overall_score,
                'is_toxic': overall_score >= 0.3,
                'confidence': confidence,
                'categories': categories,
                'model': 'perspective',
                'raw_scores': {attr: scores[attr]['summaryScore']['value'] 
                             for attr in scores if 'summaryScore' in scores[attr]},
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
            
        except HttpError as e:
            error_content = json.loads(e.content.decode('utf-8')) if e.content else {}
            print(f"Perspective API error: {e.resp.status} - {error_content}")
            
            # レート制限エラーの場合は少し待つ
            if e.resp.status == 429:
                await asyncio.sleep(1)
            
            # エラー時のフォールバック
            return {
                'score': 0.0,
                'is_toxic': False,
                'confidence': 0.0,
                'categories': [],
                'model': 'perspective',
                'error': str(e),
                'processing_time': time.time() - start_time,
                'cache_hit': False,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            return {
                'score': 0.0,
                'is_toxic': False,
                'confidence': 0.0,
                'categories': [],
                'model': 'perspective',
                'error': str(e),
                'processing_time': time.time() - start_time,
                'cache_hit': False,
                'timestamp': datetime.now().isoformat()
            }
    
    def analyze(self, text: str) -> Tuple[float, List[ToxicityCategory], float]:
        """
        MultiModelAnalyzer互換のanalyzeメソッド
        
        Args:
            text: 分析対象のテキスト
            
        Returns:
            (毒性スコア, カテゴリリスト, 信頼度)のタプル
        """
        # 非同期メソッドを同期的に実行
        import asyncio
        
        # イベントループの取得または作成
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # analyze_textを実行
        result = loop.run_until_complete(self.analyze_text(text))
        
        # 結果の変換
        score = result.get('score', 0.0)
        confidence = result.get('confidence', 0.5)
        
        # カテゴリオブジェクトの作成
        category_objects = []
        for cat_data in result.get('categories', []):
            category = ToxicityCategory(
                name=cat_data.get('name', ''),
                score=cat_data.get('score', 0.0),
                keywords_found=cat_data.get('keywords_found', [])
            )
            category_objects.append(category)
        
        return score, category_objects, confidence
    
    def get_model_info(self) -> Dict:
        """モデル情報を取得"""
        return {
            'name': 'Google Perspective',
            'model': 'v1alpha1',
            'version': '1.0.0',
            'capabilities': [
                '毒性検知に特化',
                '多言語対応（日本語含む）',
                '複数の毒性属性を同時分析',
                '高速レスポンス',
                '無料枠が大きい（1QPS）'
            ],
            'attributes': list(self.attributes.keys()),
            'rate_limits': {
                'free': '1 query per second',
                'quota': '1,000 queries per day (default)'
            }
        }


# テスト用コード
if __name__ == "__main__":
    import asyncio
    
    async def test_google_analyzer():
        """GoogleAnalyzerのテスト"""
        print("=== Google Perspective API Analyzer Test ===")
        
        # アナライザーの初期化
        try:
            analyzer = GoogleAnalyzer()
            print("✅ Initialized successfully")
        except ValueError as e:
            print(f"❌ Initialization error: {e}")
            print("Please set GOOGLE_API_KEY in .env file")
            return
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
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
            
            if 'error' in result:
                print(f"❌ エラー: {result['error']}")
                continue
            
            print(f"スコア: {result['score']:.3f}")
            print(f"有害判定: {'🚨 有害' if result['is_toxic'] else '✅ 安全'}")
            print(f"信頼度: {result['confidence']:.3f}")
            print(f"処理時間: {result['processing_time']:.3f}秒")
            
            if result.get('raw_scores'):
                print("属性別スコア:")
                for attr, score in result['raw_scores'].items():
                    print(f"  - {attr}: {score:.3f}")
            
            if result.get('categories'):
                print("検出カテゴリ:")
                for cat in result['categories']:
                    print(f"  - {cat['name']}: {cat['score']:.3f}")
            
            # レート制限を守るため1秒待機
            await asyncio.sleep(1)
        
        print("\n--- Testing analyze method (sync) ---")
        # 同期メソッドのテストは非同期コンテキスト外で実行
        print("注: analyzeメソッドのテストは、非同期コンテキスト外で実行してください")
        
        # モデル情報
        print("\n--- Model Info ---")
        info = analyzer.get_model_info()
        print(json.dumps(info, indent=2, ensure_ascii=False))
    
    # テスト実行
    asyncio.run(test_google_analyzer())
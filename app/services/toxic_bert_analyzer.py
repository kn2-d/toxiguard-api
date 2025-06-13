"""
Sentence-Transformers を使用した毒性検知サービス
埋め込みベースの類似度計算による日本語テキストの毒性判定
"""

import json
import time
import numpy as np
import concurrent.futures
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import asyncio
from sentence_transformers import SentenceTransformer
import logging

# スキーマのインポート
from app.models.schemas import ToxicityCategory

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ToxicBertAnalyzer:
    """Sentence-Transformersを使用した毒性分析クラス"""
    
    def __init__(self):
        """初期化処理"""
        # モデルの初期化
        self.model_name = "paraphrase-multilingual-MiniLM-L12-v2"
        
        try:
            self.model = SentenceTransformer(self.model_name)
            logger.info(f"モデル {self.model_name} を正常に初期化しました")
        except Exception as e:
            logger.error(f"モデル初期化エラー: {str(e)}")
            self.model = None
        
        # 毒性パターンの定義（埋め込み用）
        self.toxic_patterns = {
            "severe_toxicity": {
                "patterns": [
                    "死ね", "殺す", "死んでしまえ", "殺してやる",
                    "死ぬべき", "消えろ", "この世から消えろ"
                ],
                "weight": 0.9
            },
            "hate_speech": {
                "patterns": [
                    "クズ", "ゴミ", "きもい", "気持ち悪い",
                    "ブス", "デブ", "無能", "役立たず", "カス"
                ],
                "weight": 0.7
            },
            "violence": {
                "patterns": [
                    "殴る", "蹴る", "ぶっ殺す", "ボコボコにする",
                    "潰す", "痛めつける", "暴力を振るう"
                ],
                "weight": 0.8
            },
            "mild_toxicity": {
                "patterns": [
                    "バカ", "アホ", "間抜け", "ダメ", "うざい",
                    "むかつく", "イライラする", "嫌い"
                ],
                "weight": 0.4
            }
        }
        
        # パターンの埋め込みを事前計算
        self._precompute_embeddings()
        
        # キャッシュ
        self._cache = {}
        self._max_cache_size = 100
        
        # 閾値設定
        self.similarity_threshold = 0.5  # 類似度の閾値
    
    def _precompute_embeddings(self):
        """毒性パターンの埋め込みを事前計算"""
        if self.model is None:
            self.pattern_embeddings = {}
            return
            
        self.pattern_embeddings = {}
        
        for category, info in self.toxic_patterns.items():
            patterns = info["patterns"]
            if patterns:
                # パターンの埋め込みを計算
                embeddings = self.model.encode(patterns)
                self.pattern_embeddings[category] = {
                    "embeddings": embeddings,
                    "patterns": patterns,
                    "weight": info["weight"]
                }
    
    def _calculate_similarity(self, text_embedding: np.ndarray, 
                            pattern_embeddings: np.ndarray) -> float:
        """コサイン類似度を計算"""
        # 正規化
        text_norm = text_embedding / np.linalg.norm(text_embedding)
        pattern_norms = pattern_embeddings / np.linalg.norm(
            pattern_embeddings, axis=1, keepdims=True
        )
        
        # コサイン類似度
        similarities = np.dot(pattern_norms, text_norm)
        
        # 最大類似度を返す
        return float(np.max(similarities))
    
    def _keyword_fallback(self, text: str) -> Tuple[float, List[str], str]:
        """キーワードベースのフォールバック判定"""
        max_score = 0.0
        detected_keywords = []
        detected_category = "none"
        
        for category, info in self.toxic_patterns.items():
            for pattern in info["patterns"]:
                if pattern in text:
                    score = info["weight"]
                    if score > max_score:
                        max_score = score
                        detected_category = category
                    detected_keywords.append(pattern)
        
        return max_score, detected_keywords, detected_category
    
    async def analyze_text(self, text: str) -> Dict:
        """テキストの毒性分析（メイン関数）"""
        # キャッシュチェック
        if text in self._cache:
            cached_result = self._cache[text].copy()
            cached_result['cache_hit'] = True
            return cached_result
        
        start_time = time.time()
        
        try:
            if self.model is None:
                # モデルが利用できない場合はフォールバック
                score, keywords, category = self._keyword_fallback(text)
                categories = []
                if score > 0:
                    categories.append({
                        "name": category,
                        "score": score,
                        "keywords_found": keywords
                    })
            else:
                # テキストの埋め込みを計算
                text_embedding = self.model.encode([text])[0]
                
                # 各カテゴリとの類似度を計算
                max_score = 0.0
                categories = []
                
                for category, data in self.pattern_embeddings.items():
                    similarity = self._calculate_similarity(
                        text_embedding, 
                        data["embeddings"]
                    )
                    
                    if similarity >= self.similarity_threshold:
                        # 類似度が閾値を超えた場合
                        category_score = similarity * data["weight"]
                        
                        # 最も類似したパターンを特定
                        pattern_similarities = [
                            self._calculate_similarity(
                                text_embedding,
                                data["embeddings"][i:i+1]
                            )
                            for i in range(len(data["patterns"]))
                        ]
                        
                        max_pattern_idx = np.argmax(pattern_similarities)
                        similar_pattern = data["patterns"][max_pattern_idx]
                        
                        categories.append({
                            "name": category,
                            "score": category_score,
                            "keywords_found": [similar_pattern],
                            "similarity": similarity
                        })
                        
                        if category_score > max_score:
                            max_score = category_score
                
                # キーワードフォールバックも確認
                keyword_score, keywords, _ = self._keyword_fallback(text)
                if keyword_score > max_score:
                    max_score = keyword_score
                    # キーワードベースのカテゴリも追加
                    for category, info in self.toxic_patterns.items():
                        for keyword in keywords:
                            if keyword in info["patterns"]:
                                categories.append({
                                    "name": category,
                                    "score": info["weight"],
                                    "keywords_found": [keyword]
                                })
                                break
                
                score = max_score
            
            # 結果の構築
            result = {
                "score": score,
                "is_toxic": score >= 0.3,
                "confidence": self._calculate_confidence(score, bool(categories)),
                "categories": categories,
                "model": self.model_name if self.model else "keyword_fallback",
                "processing_time": time.time() - start_time,
                "cache_hit": False,
                "timestamp": datetime.now().isoformat()
            }
            
            # キャッシュに保存
            if len(self._cache) >= self._max_cache_size:
                # 最も古いエントリを削除
                oldest = min(self._cache.items(), 
                           key=lambda x: x[1].get("timestamp", ""))
                del self._cache[oldest[0]]
            
            self._cache[text] = result.copy()
            
            return result
            
        except Exception as e:
            logger.error(f"ToxicBert分析エラー: {str(e)}")
            # エラー時のフォールバック
            return {
                "score": 0.0,
                "is_toxic": False,
                "confidence": 0.0,
                "categories": [],
                "model": "error",
                "error": str(e),
                "processing_time": time.time() - start_time,
                "cache_hit": False,
                "timestamp": datetime.now().isoformat()
            }
    
    def _calculate_confidence(self, score: float, has_matches: bool) -> float:
        """信頼度を計算"""
        if score >= 0.7 and has_matches:
            return 0.9
        elif score >= 0.3 and has_matches:
            return 0.7
        elif has_matches:
            return 0.5
        else:
            return 0.3
    
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
            categories = result.get('categories', [])
            confidence = result.get('confidence', 0.5)
            
            # ToxicityCategoryオブジェクトのリストに変換
            category_objects = []
            for cat_data in categories:
                if isinstance(cat_data, dict):
                    category = ToxicityCategory(
                        name=cat_data['name'],
                        score=cat_data['score'],
                        keywords_found=cat_data.get('keywords', [])
                    )
                    category_objects.append(category)
            
            return score, category_objects, confidence
            
        except Exception as e:
            logger.error(f"ToxicBert分析エラー: {str(e)}")
            return 0.0, [], 0.0
    
    def get_model_info(self) -> Dict:
        """モデル情報を取得"""
        return {
            "name": "ToxicBert",
            "model": self.model_name,
            "method": "埋め込みベース類似度計算",
            "categories": list(self.toxic_patterns.keys()),
            "cache_size": len(self._cache),
            "max_cache_size": self._max_cache_size,
            "similarity_threshold": self.similarity_threshold
        }


# テスト用コード
async def test_toxic_bert():
    """ToxicBertAnalyzerのテスト"""
    print("=== ToxicBert Analyzer Test ===")
    
    analyzer = ToxicBertAnalyzer()
    
    # モデル情報
    info = analyzer.get_model_info()
    print(f"\nModel Info: {json.dumps(info, indent=2, ensure_ascii=False)}")
    
    test_texts = [
        "こんにちは、良い天気ですね",
        "死ね",
        "バカじゃないの",
        "素晴らしい提案ですね",
        "クズみたいな考え方だ",
        "ありがとうございます",
        "殴ってやる"
    ]
    
    print("\n--- Async analyze_text test ---")
    for text in test_texts:
        result = await analyzer.analyze_text(text)
        print(f"\nText: '{text}'")
        print(f"Score: {result['score']:.3f}")
        print(f"Is toxic: {result['is_toxic']}")
        print(f"Confidence: {result['confidence']:.3f}")
        
        if result['categories']:
            print("Categories:")
            for cat in result['categories']:
                print(f"  - {cat['name']}: {cat['score']:.3f}")
                if cat.get('keywords_found'):
                    print(f"    Keywords: {cat['keywords_found']}")
        
        print(f"Time: {result['processing_time']:.3f}s")
    
    # キャッシュテスト
    print("\n--- Cache test ---")
    text = "死ね"
    result1 = await analyzer.analyze_text(text)
    result2 = await analyzer.analyze_text(text)
    print(f"Cache hit: {result2.get('cache_hit', False)}")
    
    print("\n--- Sync analyze test ---")
    text = "アホか"
    score, categories, confidence = analyzer.analyze(text)
    print(f"\nText: '{text}'")
    print(f"Score: {score:.3f}")
    print(f"Categories: {len(categories)}")
    for cat in categories:
        print(f"  - {cat.name}: {cat.score:.3f}")
    print(f"Confidence: {confidence:.3f}")


if __name__ == "__main__":
    asyncio.run(test_toxic_bert())
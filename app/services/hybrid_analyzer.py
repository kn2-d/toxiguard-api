"""
ハイブリッド分析サービス
キーワード分析 + AI分析の統合判定
"""

from typing import Dict, Tuple
import asyncio
from app.services.keyword_analyzer import KeywordAnalyzer
from app.services.ai_analyzer import RinnaAnalyzer
import logging

logger = logging.getLogger(__name__)

class HybridAnalyzer:
    """キーワード + AI のハイブリッド毒性分析"""
    
    def __init__(self):
        """2つの分析エンジンを初期化"""
        self.keyword_analyzer = KeywordAnalyzer()
        self.ai_analyzer = RinnaAnalyzer()
        
        # 統合設定
        self.keyword_weight = 0.6  # キーワード重み
        self.ai_weight = 0.4       # AI重み
        
        logger.info("🔄 ハイブリッド分析システム初期化完了")
    
    async def analyze_text(self, text: str) -> Dict:
        """メイン分析機能：2つの手法を統合"""
        try:
            logger.info(f"🔍 ハイブリッド分析開始: {text[:20]}...")
            
            # 並列実行で高速化
            keyword_task = asyncio.create_task(self._get_keyword_result(text))
            ai_task = asyncio.create_task(self.ai_analyzer.analyze_text(text))
            
            # 両方の結果を取得
            keyword_result, ai_result = await asyncio.gather(keyword_task, ai_task)
            
            # スコア統合
            final_score, confidence = self._integrate_scores(keyword_result, ai_result, text)
            
            # 統合結果
            result = {
                "text": text,
                "final_score": final_score,
                "confidence": confidence,
                "is_toxic": final_score > 0.3,
                "details": {
                    "keyword": keyword_result,
                    "ai": {                                    # ← 正規化された形式
                        "score": ai_result.get("ai_score", 0.0),
                        "confidence": ai_result.get("confidence", 0.8),
                        "model_used": ai_result.get("model_used", "unknown")
                        },
                        "weights": {
                            "keyword": self.keyword_weight,
                            "ai": self.ai_weight
                        }
                    }
                }
            
            logger.info(f"✅ ハイブリッド分析完了: スコア={final_score:.3f}")
            return result
            
        except Exception as e:
            logger.error(f"❌ ハイブリッド分析エラー: {str(e)}")
            return {"error": str(e), "final_score": 0.0}
    
    # 【修正後】
    async def _get_keyword_result(self, text: str) -> Dict:
        """キーワード分析結果を取得"""
        # 既存のキーワード分析を呼び出し（正しいメソッド名）
        score, categories, confidence = self.keyword_analyzer.analyze(text)
        
        # 辞書形式に変換
        return {
            "score": score,
            "confidence": confidence,
            "categories": [str(cat) for cat in categories]  # カテゴリ名リスト
        }
    
    def _integrate_scores(self, keyword_result: Dict, ai_result: Dict, text: str) -> Tuple[float, float]:
        """2つのスコアを統合計算"""
        try:
            # 基本スコア取得
            keyword_score = keyword_result.get("score", 0.0)
            ai_score = ai_result.get("ai_score", 0.0)
            
            # 重み付け統合
            weighted_score = (keyword_score * self.keyword_weight) + (ai_score * self.ai_weight)
            
            # 信頼度計算
            keyword_conf = keyword_result.get("confidence", 0.8)
            ai_conf = ai_result.get("confidence", 0.8)
            integrated_confidence = (keyword_conf + ai_conf) / 2
            
            # ブースト効果（両方が高スコアの場合）
            if keyword_score > 0.2 and ai_score > 0.02:
                boost_factor = 1.2
                weighted_score = min(1.0, weighted_score * boost_factor)
                logger.info(f"🚀 ダブル検知ブースト適用: {boost_factor}x")
            
            logger.info(f"🧮 統合計算 - keyword:{keyword_score:.3f}, ai:{ai_score:.3f}, final:{weighted_score:.3f}")
            
            return weighted_score, integrated_confidence
            
        except Exception as e:
            logger.error(f"❌ スコア統合エラー: {str(e)}")
            return 0.0, 0.5
     # テスト用関数
async def test_hybrid_analyzer():
    """ハイブリッド分析の動作確認"""
    analyzer = HybridAnalyzer()
    
    # テストケース
    test_cases = [
        "こんにちは、良い天気ですね",  # 安全
        "バカ",                      # 軽度毒性（キーワードのみ）
        "死ね",                      # 重度毒性（両方検知）
        "あなたはクズだ",            # 中程度毒性
        "素晴らしい一日ですね"       # 完全安全
    ]
    
    print("🔬 ハイブリッド分析テスト開始\n")
    
    for i, text in enumerate(test_cases, 1):
        print(f"【テスト{i}】入力: '{text}'")
        result = await analyzer.analyze_text(text)
        
        if "error" in result:
            print(f"❌ エラー: {result['error']}\n")
            continue
            
        # 結果表示
        final_score = result['final_score']
        is_toxic = result['is_toxic']
        confidence = result['confidence']
        
        # 詳細スコア
        keyword_score = result['details']['keyword']['score']
        ai_score = result['details']['ai']['score']
        
        print(f"📊 最終判定: {'🚨 有害' if is_toxic else '✅ 安全'} (スコア: {final_score:.3f})")
        print(f"   キーワード: {keyword_score:.3f} | AI: {ai_score:.3f}")
        print(f"   信頼度: {confidence:.3f}")
        print("")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_hybrid_analyzer())   
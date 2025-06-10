"""
AI分析サービス（rinna日本語AI使用）
毒性検知のAI判定機能を提供
"""

from typing import Dict, Optional
import torch
from transformers import AutoTokenizer, AutoModel
import logging
from pathlib import Path

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RinnaAnalyzer:
    """rinna日本語AIを使用した毒性分析クラス"""
    
    def __init__(self):
        """初期化：モデルとトークナイザーを準備"""
        self.model_name = "rinna/japanese-roberta-base"
        self.device = "cpu"  # GPU使用時は"cuda"
        self.model = None
        self.tokenizer = None
        self.is_loaded = False
        
        # キャッシュ機能追加
        self.cache = {}  # 分析結果キャッシュ
        self.cache_max_size = 100  # キャッシュ最大件数
        
        logger.info(f"🤖 RinnaAnalyzer初期化開始")
        
    def load_model(self) -> bool:
        """モデル読み込み（遅延読み込み方式）"""
        try:
            logger.info(f"📥 モデル読み込み開始: {self.model_name}")
            
            # トークナイザー読み込み
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            
            # モデル読み込み
            self.model = AutoModel.from_pretrained(self.model_name)
            self.model.to(self.device)
            self.model.eval()  # 推論モード
            
            self.is_loaded = True
            logger.info(f"✅ モデル読み込み完了")
            return True
            
        except Exception as e:
            logger.error(f"❌ モデル読み込み失敗: {str(e)}")
            return False
    
    def get_model_info(self) -> Dict[str, str]:
        """モデル情報取得"""
        if not self.is_loaded:
            return {"status": "未読み込み"}
            
        return {
            "model_name": self.model_name,
            "device": self.device,
            "parameters": f"{self.model.num_parameters():,}",
            "status": "読み込み済み"
        }
    
    async def analyze_text(self, text: str) -> Dict[str, float]:
        """テキスト分析（キャッシュ対応版）"""
        # キャッシュ確認
        cache_key = text.strip().lower()
        if cache_key in self.cache:
            logger.info(f"💾 キャッシュヒット: {text[:20]}...")
            return self.cache[cache_key]
        
        # モデル未読み込みの場合は読み込み
        if not self.is_loaded:
            if not self.load_model():
                return {"error": "モデル読み込み失敗", "score": 0.0}
        
        try:
            # テキスト前処理とトークン化
            logger.info(f"🔍 分析開始: {text[:20]}...")
            
            # トークン化
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=512,
                padding=True
            )
            
            # AI推論実行
            with torch.no_grad():
                outputs = self.model(**inputs)
                
            # 毒性スコア計算
            toxicity_score = self._calculate_toxicity_score(outputs, text)
            
            # 結果作成
            result = {
                "ai_score": toxicity_score,
                "confidence": 0.8,
                "model_used": self.model_name
            }
            
            # キャッシュに保存（サイズ制限付き）
            if len(self.cache) >= self.cache_max_size:
                # 古いエントリを削除（FIFO方式）
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                logger.info(f"🧹 キャッシュクリア: {oldest_key[:20]}...")
            
            self.cache[cache_key] = result
            logger.info(f"✅ 分析完了・キャッシュ保存")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 分析エラー: {str(e)}")
            return {"error": str(e), "score": 0.0}
    
    def _calculate_toxicity_score(self, model_outputs, text: str) -> float:
        """AI出力から毒性スコアを計算"""
        try:
            # 隠れ状態の取得
            last_hidden_state = model_outputs.last_hidden_state
            
            # CLSトークン（文全体の表現）を使用
            cls_embedding = last_hidden_state[0, 0, :]  # [batch=0, token=0, features]
            
            # 毒性判定の特徴量計算
            # 1. ネガティブ要素の強度
            negative_intensity = torch.mean(torch.abs(cls_embedding)).item()
            
            # 2. 文の長さ補正
            text_length = len(text)
            length_factor = min(1.0, text_length / 10.0)  # 短文は係数小
            
            # 3. 基本毒性スコア計算
            base_score = min(1.0, negative_intensity * 0.1)  # 0-1正規化
            
            # 4. 毒性キーワードボーナス（簡易版）
            toxic_keywords = ["死ね", "殺す", "クズ", "バカ", "アホ"]
            keyword_bonus = 0.0
            for keyword in toxic_keywords:
                if keyword in text:
                    keyword_bonus += 0.3
            
            # 5. 最終スコア計算
            final_score = min(1.0, (base_score + keyword_bonus) * length_factor)
            
            logger.info(f"🧮 スコア詳細 - base:{base_score:.3f}, bonus:{keyword_bonus:.3f}, final:{final_score:.3f}")
            
            return final_score
            
        except Exception as e:
            logger.error(f"❌ スコア計算エラー: {str(e)}")
            return 0.0
    
    async def analyze_batch(self, texts: list) -> Dict[str, Dict]:
        """複数テキストの一括分析（高速化）"""
        results = {}
        
        logger.info(f"📦 バッチ分析開始: {len(texts)}件")
        
        for i, text in enumerate(texts):
            result = await self.analyze_text(text)
            results[f"text_{i}"] = {
                "input": text,
                "result": result
            }
        
        logger.info(f"✅ バッチ分析完了")
        return results

    def get_cache_stats(self) -> Dict[str, int]:
        """キャッシュ統計情報"""
        return {
            "cache_size": len(self.cache),
            "max_size": self.cache_max_size,
            "hit_rate": "実装予定"  # 将来の機能
        }


# テスト用関数
async def test_analyzer():
    """動作確認用テスト"""
    analyzer = RinnaAnalyzer()
    
    # モデル情報表示
    info = analyzer.get_model_info()
    print(f"📊 モデル情報: {info}")
    
    # テスト分析
    test_texts = ["こんにちは", "死ね", "良い天気ですね"]
    
    for text in test_texts:
        result = await analyzer.analyze_text(text)
        print(f"入力: {text} → 結果: {result}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_analyzer())
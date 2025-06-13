"""
Mistral/Phi-2 モデルを使用した毒性検知サービス
ローカルLLMを使用した日本語テキストの毒性判定
"""

import os
import json
import torch
import time
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from transformers import AutoModelForCausalLM, AutoTokenizer
import asyncio
import concurrent.futures

# スキーマのインポート
from app.models.schemas import ToxicityCategory

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MistralAnalyzer:
    """Mistral/Phi-2モデルを使用した毒性分析クラス"""
    
    def __init__(self):
        """初期化処理"""
        # モデルとトークナイザーの初期化
        self.model_name = "microsoft/phi-2"  # Mistralの代わりにPhi-2を使用
        self.device = self._get_device()
        
        logger.info(f"モデル {self.model_name} を {self.device} で初期化中...")
        
        try:
            # モデルとトークナイザーのロード
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=True,
                padding_side='left'
            )
            
            # パディングトークンの設定
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if self.device != "cpu" else torch.float32,
                device_map="auto" if self.device != "cpu" else None,
                trust_remote_code=True
            )
            
            if self.device == "cpu":
                self.model = self.model.to(self.device)
            
            self.model.eval()
            
            logger.info(f"モデル初期化完了: {self.device}")
            
        except Exception as e:
            logger.error(f"モデル初期化エラー: {str(e)}")
            # フォールバック: モデルなしで動作
            self.model = None
            self.tokenizer = None
        
        # キャッシュ
        self._cache = {}
        self._max_cache_size = 100
        
        # カテゴリ定義
        self.categories = {
            "severe_toxicity": {
                "name": "重度の毒性",
                "keywords": ["死ね", "殺す", "死んで", "殺してやる", "死ぬ"],
                "weight": 0.9
            },
            "hate_speech": {
                "name": "ヘイトスピーチ",
                "keywords": ["クズ", "ゴミ", "きもい", "ブス", "デブ"],
                "weight": 0.7
            },
            "violence": {
                "name": "暴力的表現",
                "keywords": ["殴る", "蹴る", "ぶっ殺す", "ボコボコ", "潰す"],
                "weight": 0.8
            },
            "mild_toxicity": {
                "name": "軽度の毒性",
                "keywords": ["バカ", "アホ", "間抜け", "ダメ", "うざい"],
                "weight": 0.4
            }
        }
    
    def _get_device(self) -> str:
        """使用可能なデバイスを取得"""
        if torch.cuda.is_available():
            return "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            # M1/M2 Macの場合、MPSは不安定なのでCPUを使用
            logger.info("MPS検出されましたが、安定性のためCPUを使用します")
            return "cpu"
        else:
            return "cpu"
    
    def _load_normal_model(self):
        """通常のモデルロード（将来の拡張用）"""
        pass
    
    def _create_prompt(self, text: str) -> str:
        """毒性判定用のプロンプトを作成"""
        prompt = f"""以下のテキストの毒性を分析してください。

テキスト: "{text}"

このテキストが有害または攻撃的かどうかを判定し、以下の形式で回答してください：
- 毒性スコア（0.0-1.0）: 
- 理由: 
- カテゴリ: severe_toxicity/hate_speech/violence/mild_toxicity/none

回答:"""
        return prompt
    
    def _parse_model_output(self, output: str) -> Dict:
        """モデル出力を解析"""
        try:
            # シンプルなパース（実際のモデル出力に応じて調整）
            lines = output.strip().split('\n')
            score = 0.5  # デフォルト
            reason = "モデル分析による判定"
            category = "none"
            
            for line in lines:
                if "毒性スコア" in line and ":" in line:
                    try:
                        score_str = line.split(':')[1].strip()
                        score = float(score_str)
                    except:
                        pass
                elif "理由" in line and ":" in line:
                    reason = line.split(':', 1)[1].strip()
                elif "カテゴリ" in line and ":" in line:
                    category = line.split(':')[1].strip()
            
            return {
                "score": score,
                "reason": reason,
                "category": category
            }
        except Exception as e:
            logger.error(f"出力パースエラー: {str(e)}")
            return {
                "score": 0.5,
                "reason": "解析エラー",
                "category": "none"
            }
    
    def _keyword_fallback(self, text: str) -> float:
        """キーワードベースのフォールバック判定"""
        max_score = 0.0
        detected_categories = []
        
        for cat_key, cat_info in self.categories.items():
            for keyword in cat_info["keywords"]:
                if keyword in text:
                    score = cat_info["weight"]
                    if score > max_score:
                        max_score = score
                    detected_categories.append(cat_key)
                    break
        
        return max_score
    
    async def _generate_with_model(self, prompt: str) -> str:
        """モデルを使用してテキスト生成"""
        if self.model is None or self.tokenizer is None:
            return ""
        
        try:
            inputs = self.tokenizer(
                prompt, 
                return_tensors="pt", 
                truncation=True, 
                max_length=512,
                padding=True
            ).to(self.device)
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=150,
                    temperature=0.1,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            # プロンプト部分を除去
            response = response[len(prompt):].strip()
            
            return response
            
        except Exception as e:
            logger.error(f"生成エラー: {str(e)}")
            return ""
    
    def _cached_analysis(self, text: str) -> Dict:
        """キャッシュされた分析結果を返す"""
        return self._cache.get(text)
    
    async def analyze_text(self, text: str) -> Dict:
        """テキストの毒性分析（メイン関数）"""
        # キャッシュチェック
        if text in self._cache:
            return self._cache[text]
            
        start_time = time.time()
        
        try:
            # モデルが利用可能な場合
            if self.model is not None:
                # タイムアウト付きで実行
                try:
                    prompt = self._create_prompt(text)
                    output = await asyncio.wait_for(
                        self._generate_with_model(prompt),
                        timeout=5.0  # 5秒でタイムアウト
                    )
                    
                    if output:
                        result = self._parse_model_output(output)
                        score = result["score"]
                        reason = result["reason"]
                    else:
                        # モデル出力が空の場合はフォールバック
                        score = self._keyword_fallback(text)
                        reason = "キーワードベース判定"
                        
                except asyncio.TimeoutError:
                    logger.warning("モデル推論がタイムアウトしました")
                    score = self._keyword_fallback(text)
                    reason = "タイムアウトによりキーワード判定"
            else:
                # モデルが利用できない場合はキーワードフォールバック
                score = self._keyword_fallback(text)
                reason = "モデル未初期化のためキーワード判定"
            
            # カテゴリ判定
            categories = []
            if score >= 0.7:
                categories.append({
                    "name": "severe_toxicity",
                    "score": score,
                    "keywords_found": []
                })
            elif score >= 0.3:
                categories.append({
                    "name": "mild_toxicity", 
                    "score": score,
                    "keywords_found": []
                })
            
            # 結果の構築
            result = {
                "score": score,
                "is_toxic": score >= 0.3,
                "confidence": self._calculate_confidence(score, reason),
                "categories": categories,
                "reason": reason,
                "model": self.model_name if self.model else "keyword_fallback",
                "processing_time": time.time() - start_time,
                "timestamp": datetime.now().isoformat()
            }
            
            # キャッシュに保存
            if len(self._cache) >= self._max_cache_size:
                # 最も古いエントリを削除
                oldest = min(self._cache.items(), key=lambda x: x[1].get("timestamp", ""))
                del self._cache[oldest[0]]
            
            self._cache[text] = result
            
            return result
            
        except Exception as e:
            logger.error(f"Mistral分析エラー: {str(e)}")
            # エラー時のフォールバック結果
            return {
                "score": 0.0,
                "is_toxic": False,
                "confidence": 0.0,
                "categories": [],
                "reason": f"エラー: {str(e)}",
                "model": "error",
                "processing_time": time.time() - start_time,
                "timestamp": datetime.now().isoformat()
            }
    
    def _calculate_confidence(self, score: float, reason: str) -> float:
        """信頼度を計算"""
        if "モデル分析" in reason:
            return 0.8
        elif "キーワード" in reason:
            return 0.6
        elif "タイムアウト" in reason:
            return 0.4
        else:
            return 0.5
    
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
            score = result.get('toxicity_score', 0.0)
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
            logger.error(f"Mistral分析エラー: {str(e)}")
            return 0.0, [], 0.0


# テスト用コード
async def test_mistral():
    """MistralAnalyzerのテスト"""
    print("=== Mistral/Phi-2 Analyzer Test ===")
    
    analyzer = MistralAnalyzer()
    
    test_texts = [
        "こんにちは、良い天気ですね",
        "死ね",
        "バカじゃないの",
        "素晴らしい提案ですね",
        "クズみたいな考え方だ"
    ]
    
    print("\n--- Async analyze_text test ---")
    for text in test_texts:
        result = await analyzer.analyze_text(text)
        print(f"\nText: '{text}'")
        print(f"Score: {result['score']:.3f}")
        print(f"Is toxic: {result['is_toxic']}")
        print(f"Confidence: {result['confidence']:.3f}")
        print(f"Reason: {result['reason']}")
        print(f"Time: {result['processing_time']:.3f}s")
    
    print("\n--- Sync analyze test ---")
    text = "アホか"
    score, categories, confidence = analyzer.analyze(text)
    print(f"\nText: '{text}'")
    print(f"Score: {score:.3f}")
    print(f"Categories: {len(categories)}")
    print(f"Confidence: {confidence:.3f}")


if __name__ == "__main__":
    asyncio.run(test_mistral())
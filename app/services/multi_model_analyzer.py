# app/services/multi_model_analyzer.py
"""
Release 4 マルチモデル統合アナライザー
KeywordAnalyzer + ToxicBertAnalyzer + MistralAnalyzer (Phi-2) + ClaudeAnalyzer
"""
import asyncio
from asyncio import TimeoutError
from typing import Dict, List, Optional, Literal, Tuple
from dataclasses import dataclass
import logging
import time
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed

# 各アナライザーをインポート
import sys
import os

# プロジェクトルートをパスに追加
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_root)

try:
    from app.services.keyword_analyzer import KeywordAnalyzer
    from app.services.toxic_bert_analyzer import ToxicBertAnalyzer
    from app.services.mistral_analyzer import MistralAnalyzer
    from app.services.claude_analyzer import ClaudeAnalyzer  # Release 4で追加
    from app.config import settings, MODEL_CONFIGS
    from app.models.schemas import ToxicityCategory
except ImportError:
    # 別のインポート方法を試す
    try:
        from keyword_analyzer import KeywordAnalyzer
        from toxic_bert_analyzer import ToxicBertAnalyzer
        from mistral_analyzer import MistralAnalyzer
        from claude_analyzer import ClaudeAnalyzer  # Release 4で追加
        from config import settings, MODEL_CONFIGS
        from models.schemas import ToxicityCategory
    except ImportError as e:
        print(f"インポートエラー: {e}")
        print(f"現在のディレクトリ: {os.getcwd()}")
        print(f"Pythonパス: {sys.path}")
        raise

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ModelResult:
    """各モデルの分析結果"""
    model_name: str
    toxicity_score: float
    is_toxic: bool
    categories: List[ToxicityCategory]
    confidence: float
    response_time: float
    error: Optional[str] = None


# app/services/multi_model_analyzer.py（修正版の該当部分）
class MultiModelAnalyzer:
    """複数のモデルを統合した分析システム"""
    
    def __init__(self):
        """利用可能なモデルを初期化"""
        self.models = {}
        
        # キーワードアナライザー（必須）
        try:
            self.models['keyword'] = KeywordAnalyzer()
            logger.info("KeywordAnalyzer初期化成功")
        except Exception as e:
            logger.error(f"KeywordAnalyzer初期化エラー: {e}")
        
        # ToxicBERTアナライザー
        if 'toxic_bert' in MODEL_CONFIGS and MODEL_CONFIGS['toxic_bert'].enabled:
            try:
                self.models['toxic_bert'] = ToxicBertAnalyzer()
                logger.info("ToxicBertAnalyzer初期化成功")
            except Exception as e:
                logger.error(f"ToxicBertAnalyzer初期化エラー: {e}")
        
        # Mistralアナライザー（Phi-2）
        if 'mistral' in MODEL_CONFIGS and MODEL_CONFIGS['mistral'].enabled:
            try:
                self.models['mistral'] = MistralAnalyzer()
                logger.info("MistralAnalyzer初期化成功")
            except Exception as e:
                logger.error(f"MistralAnalyzer初期化エラー: {e}")
        
        # Claude アナライザー（Release 4で追加）
        if 'claude' in MODEL_CONFIGS and MODEL_CONFIGS['claude'].enabled:
            try:
                self.models['claude'] = ClaudeAnalyzer()
                logger.info("ClaudeAnalyzer初期化成功")
            except Exception as e:
                logger.error(f"ClaudeAnalyzer初期化エラー: {e}")
        
        # OpenAI アナライザー（プレースホルダー）
        if 'openai' in MODEL_CONFIGS and MODEL_CONFIGS['openai'].enabled:
            logger.info("OpenAIAnalyzer: 未実装")
        
        # Google アナライザー（プレースホルダー）
        if 'google' in MODEL_CONFIGS and MODEL_CONFIGS['google'].enabled:
            logger.info("GoogleAnalyzer: 未実装")
        
        logger.info(f"初期化完了: {list(self.models.keys())}")
        
        # モデル重み（config.pyから取得）
        self.model_weights = {
            'keyword': MODEL_CONFIGS['keyword'].weight if 'keyword' in MODEL_CONFIGS else 0.2,
            'toxic_bert': MODEL_CONFIGS['toxic_bert'].weight if 'toxic_bert' in MODEL_CONFIGS else 0.3,
            'mistral': MODEL_CONFIGS['mistral'].weight if 'mistral' in MODEL_CONFIGS else 0.15,
            'claude': MODEL_CONFIGS['claude'].weight if 'claude' in MODEL_CONFIGS else 0.2,
            'openai': MODEL_CONFIGS['openai'].weight if 'openai' in MODEL_CONFIGS else 0.15,
            'google': MODEL_CONFIGS['google'].weight if 'google' in MODEL_CONFIGS else 0.0,
        }
        
        # タイムアウト設定（秒）
        self.timeouts = {
            'keyword': MODEL_CONFIGS['keyword'].timeout if 'keyword' in MODEL_CONFIGS else 1,
            'toxic_bert': MODEL_CONFIGS['toxic_bert'].timeout if 'toxic_bert' in MODEL_CONFIGS else 3,
            'mistral': MODEL_CONFIGS['mistral'].timeout if 'mistral' in MODEL_CONFIGS else 5,
            'claude': MODEL_CONFIGS['claude'].timeout if 'claude' in MODEL_CONFIGS else 10,
            'openai': MODEL_CONFIGS['openai'].timeout if 'openai' in MODEL_CONFIGS else 10,
            'google': MODEL_CONFIGS['google'].timeout if 'google' in MODEL_CONFIGS else 5,
        }
    
    async def analyze_with_model(self, model_name: str, text: str) -> ModelResult:
        """単一モデルで分析を実行"""
        if model_name not in self.models:
            return ModelResult(
                model_name=model_name,
                toxicity_score=0.0,
                is_toxic=False,
                categories=[],
                confidence=0.0,
                response_time=0.0,
                error=f"Model {model_name} not available"
            )
        
        start_time = time.time()
        try:
            # タイムアウト付きで実行
            timeout = self.timeouts.get(model_name, 5)
            
            # 非同期実行のラッパー
            async def run_analysis():
                model = self.models[model_name]
                # analyzeメソッドを非同期で実行
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, model.analyze, text)
            
            # タイムアウト付きで実行
            score, categories, confidence = await asyncio.wait_for(
                run_analysis(),
                timeout=timeout
            )
            
            response_time = time.time() - start_time
            
            return ModelResult(
                model_name=model_name,
                toxicity_score=score,
                is_toxic=score >= 0.3,
                categories=categories,
                confidence=confidence,
                response_time=response_time
            )
            
        except asyncio.TimeoutError:
            logger.warning(f"{model_name}がタイムアウト（{self.timeouts[model_name]}秒）")
            return ModelResult(
                model_name=model_name,
                toxicity_score=0.0,
                is_toxic=False,
                categories=[],
                confidence=0.0,
                response_time=time.time() - start_time,
                error="Timeout"
            )
        except Exception as e:
            logger.error(f"{model_name}エラー: {e}")
            return ModelResult(
                model_name=model_name,
                toxicity_score=0.0,
                is_toxic=False,
                categories=[],
                confidence=0.0,
                response_time=time.time() - start_time,
                error=str(e)
            )
    
    async def analyze_with_strategy(
        self, 
        text: str, 
        strategy: Literal["fast", "cascade", "balanced", "accurate"] = "balanced"
    ) -> Dict:
        """戦略に基づいて分析を実行"""
        
        start_time = time.time()
        results = []
        
        if strategy == "fast":
            # 最速：キーワードのみ
            result = await self.analyze_with_model("keyword", text)
            results.append(result)
            
        elif strategy == "cascade":
            # 段階的：キーワード → 必要に応じて他のモデル
            keyword_result = await self.analyze_with_model("keyword", text)
            results.append(keyword_result)
            
            # キーワードで中間的なスコアの場合、追加分析
            if 0.2 <= keyword_result.toxicity_score <= 0.7:
                if "toxic_bert" in self.models:
                    bert_result = await self.analyze_with_model("toxic_bert", text)
                    results.append(bert_result)
                    
                # さらに高精度が必要な場合、Claude追加
                if 0.3 <= keyword_result.toxicity_score <= 0.6 and "claude" in self.models:
                    claude_result = await self.analyze_with_model("claude", text)
                    results.append(claude_result)
        
        elif strategy == "balanced":
            # バランス型：利用可能な全モデルを並列実行
            tasks = []
            for model_name in self.models.keys():
                task = asyncio.create_task(self.analyze_with_model(model_name, text))
                tasks.append((model_name, task))
            
            # 全タスクの完了を待つ
            for model_name, task in tasks:
                try:
                    result = await task
                    results.append(result)
                except Exception as e:
                    logger.error(f"{model_name}の実行エラー: {e}")
        
        elif strategy == "accurate":
            # 高精度：重要なモデルに重点
            priority_models = ["keyword", "toxic_bert", "claude"]
            tasks = []
            
            for model_name in priority_models:
                if model_name in self.models:
                    task = asyncio.create_task(self.analyze_with_model(model_name, text))
                    tasks.append((model_name, task))
            
            # 全タスクの完了を待つ
            for model_name, task in tasks:
                try:
                    result = await task
                    results.append(result)
                except Exception as e:
                    logger.error(f"{model_name}の実行エラー: {e}")
        
        # 結果の統合
        final_result = self._aggregate_results(results, strategy)
        final_result["analysis_time"] = time.time() - start_time
        final_result["strategy"] = strategy
        final_result["models_used"] = [r.model_name for r in results if r.error is None]
        
        return final_result
    
    def _aggregate_results(self, results: List[ModelResult], strategy: str) -> Dict:
        """複数モデルの結果を統合"""
        if not results:
            return {
                "text": "",
                "toxicity_score": 0.0,
                "is_toxic": False,
                "categories": [],
                "confidence": 0.0,
                "details": {"error": "No results"}
            }
        
        # エラーでない結果のみフィルタ
        valid_results = [r for r in results if r.error is None]
        
        if not valid_results:
            return {
                "text": "",
                "toxicity_score": 0.0,
                "is_toxic": False,
                "categories": [],
                "confidence": 0.0,
                "details": {"error": "All models failed"}
            }
        
        # 重み付き平均の計算
        total_weight = 0
        weighted_score = 0
        all_categories = []
        confidence_scores = []
        
        for result in valid_results:
            weight = self.model_weights.get(result.model_name, 0.1)
            weighted_score += result.toxicity_score * weight
            total_weight += weight
            all_categories.extend(result.categories)
            confidence_scores.append(result.confidence)
        
        # 最終スコア
        final_score = weighted_score / total_weight if total_weight > 0 else 0.0
        
        # カテゴリの統合（重複を除く）
        unique_categories = []
        seen_names = set()
        for cat in all_categories:
            if cat.name not in seen_names:
                unique_categories.append(cat)
                seen_names.add(cat.name)
        
        # 信頼度の計算
        avg_confidence = np.mean(confidence_scores) if confidence_scores else 0.0
        
        # 各モデルの詳細結果
        model_details = {}
        for result in results:
            model_details[result.model_name] = {
                "score": result.toxicity_score,
                "is_toxic": result.is_toxic,
                "confidence": result.confidence,
                "response_time": result.response_time,
                "error": result.error
            }
        
        return {
            "text": "",  # テキストは後で設定
            "toxicity_score": final_score,
            "is_toxic": final_score >= 0.3,
            "categories": unique_categories,
            "confidence": avg_confidence,
            "details": {
                "model_results": model_details,
                "aggregation_method": "weighted_average",
                "total_models": len(results),
                "valid_models": len(valid_results)
            }
        }
    
    def get_available_models(self) -> List[str]:
        """利用可能なモデルのリストを返す"""
        return list(self.models.keys())
    
    def get_model_info(self) -> Dict:
        """各モデルの情報を返す"""
        info = {}
        for name, model in self.models.items():
            info[name] = {
                "enabled": True,
                "weight": self.model_weights.get(name, 0.1),
                "timeout": self.timeouts.get(name, 5),
                "type": type(model).__name__
            }
        return info


# テストコード
if __name__ == "__main__":
    async def test():
        print("=== マルチモデル統合テスト（Release 4） ===")
        analyzer = MultiModelAnalyzer()
        
        print(f"利用可能なモデル: {analyzer.get_available_models()}")
        print("\nモデル情報:")
        for name, info in analyzer.get_model_info().items():
            print(f"  {name}: {info}")
        
        test_cases = [
            "こんにちは、良い天気ですね",
            "死ね",
            "バカ",
            "うざい、消えろ",
        ]
        
        strategies = ["fast", "cascade", "balanced", "accurate"]
        
        for text in test_cases:
            print(f"\n{'='*60}")
            print(f"テキスト: {text}")
            print('='*60)
            
            for strategy in strategies:
                print(f"\n戦略: {strategy}")
                result = await analyzer.analyze_with_strategy(text, strategy)
                result["text"] = text  # テキストを設定
                
                print(f"総合スコア: {result['toxicity_score']:.3f}")
                print(f"有害判定: {'🚨 有害' if result['is_toxic'] else '✅ 安全'}")
                print(f"使用モデル: {result['models_used']}")
                print(f"分析時間: {result['analysis_time']:.2f}秒")
                
                if result['categories']:
                    print("検出カテゴリ:")
                    for cat in result['categories']:
                        print(f"  - {cat.name}")
    
    asyncio.run(test())
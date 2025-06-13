# app/services/claude_analyzer.py（既存構造完全互換版）
"""
Claude APIを使用した毒性分析サービス
Release 4: 外部API統合
"""
import asyncio
import json
import concurrent.futures
from typing import Dict, Optional, Tuple, List
import logging
from datetime import datetime
from anthropic import Anthropic, APIError, APITimeoutError

from app.config import settings, API_SPECIFIC_CONFIG
from app.models.schemas import ToxicityCategory

logger = logging.getLogger(__name__)


class ClaudeAnalyzer:
    """Claude APIを使用した毒性分析"""
    
    def __init__(self):
        """Claude APIクライアントの初期化"""
        self.api_key = settings.ANTHROPIC_API_KEY
        self.client = None
        self.config = API_SPECIFIC_CONFIG.get("claude", {})
        self.model_name = self.config.get("model", "claude-3-haiku-20240307")
        
        # キャッシュ（コスト削減のため）
        self._cache = {}
        self._cache_size = 100
        
        # APIキーが設定されている場合のみクライアントを初期化
        if self.api_key:
            try:
                self.client = Anthropic(api_key=self.api_key)
                logger.info(f"Claude APIクライアント初期化成功: {self.model_name}")
            except Exception as e:
                logger.error(f"Claude APIクライアント初期化エラー: {e}")
                self.client = None
        else:
            logger.warning("Claude APIキーが設定されていません")
    
    def analyze(self, text: str) -> Tuple[float, List[ToxicityCategory], float]:
        """
        テキストを分析して毒性スコアを返す（既存インターフェース互換）
        
        Args:
            text: 分析対象のテキスト
            
        Returns:
            (総合スコア, カテゴリリスト, 信頼度)
        """
        # 非同期メソッドを同期的に実行
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
            
            # 結果を既存インターフェースに変換
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
            logger.error(f"分析エラー: {str(e)}")
            return 0.0, [], 0.0
    
    async def analyze_text(self, text: str) -> Dict:
        """
        テキストの毒性を分析（内部API用）
        
        Args:
            text: 分析対象のテキスト
            
        Returns:
            分析結果の辞書
        """
        try:
            # キャッシュチェック
            if text in self._cache:
                logger.debug(f"キャッシュヒット: {text[:30]}...")
                cached_result = self._cache[text].copy()
                cached_result["details"]["cached"] = True
                return cached_result
            
            # APIが利用できない場合はデフォルト値を返す
            if not self.client or not settings.USE_EXTERNAL_APIS:
                return self._get_default_result(text)
            
            # Claude APIへのプロンプト作成
            prompt = self._create_prompt(text)
            
            # 非同期でAPI呼び出し
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                self._call_claude_api,
                prompt
            )
            
            # レスポンスの解析
            result = self._parse_response(response, text)
            
            # キャッシュに保存
            self._update_cache(text, result)
            
            return result
            
        except APITimeoutError:
            logger.error(f"Claude APIタイムアウト: {text[:50]}...")
            return self._get_default_result(text)
            
        except APIError as e:
            logger.error(f"Claude APIエラー: {e}")
            return self._get_default_result(text)
            
        except Exception as e:
            logger.error(f"予期しないエラー: {e}")
            return self._get_default_result(text)
    
    def _create_prompt(self, text: str) -> str:
        """Claude API用のプロンプトを作成"""
        system_prompt = self.config.get("system_prompt", "")
        
        return f"""{system_prompt}

以下の日本語テキストの毒性を分析してください。
0.0（完全に安全）から1.0（非常に有害）のスコアと、該当するカテゴリを判定してください。

カテゴリ:
- 重度の毒性: 死ね、殺す等の生命を脅かす表現
- ヘイトスピーチ: きもい、クズ等の侮辱的表現
- 暴力的表現: 暴力を示唆する表現
- 性的な内容: 性的な表現
- 差別的表現: 差別を含む表現
- 軽度の毒性: バカ、アホ等の軽い悪口

テキスト: "{text}"

以下の形式で回答してください：
総合スコア: [0.0-1.0の数値]
カテゴリ: [該当するカテゴリ名（日本語、複数可）]
理由: [判定理由を簡潔に]
検出語句: [毒性のある具体的な語句（カンマ区切り）]"""
    
    def _call_claude_api(self, prompt: str) -> str:
        """Claude APIを同期的に呼び出し"""
        start_time = datetime.now()
        
        try:
            message = self.client.messages.create(
                model=self.model_name,
                max_tokens=self.config.get("max_tokens", 200),
                temperature=self.config.get("temperature", 0),
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            # API呼び出し時間を記録
            elapsed_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"Claude API応答時間: {elapsed_time:.2f}秒")
            
            return message.content[0].text
            
        except Exception as e:
            logger.error(f"Claude API呼び出しエラー: {e}")
            raise
    
    def _parse_response(self, response: str, original_text: str) -> Dict:
        """Claude APIのレスポンスを解析"""
        try:
            # レスポンスから情報を抽出
            lines = response.strip().split('\n')
            total_score = 0.0
            categories = []
            reason = ""
            detected_words = []
            
            for line in lines:
                line = line.strip()
                if line.startswith("総合スコア:"):
                    score_str = line.replace("総合スコア:", "").strip()
                    try:
                        total_score = float(score_str)
                        total_score = max(0.0, min(1.0, total_score))
                    except ValueError:
                        logger.warning(f"スコア解析エラー: {score_str}")
                        
                elif line.startswith("カテゴリ:"):
                    category_str = line.replace("カテゴリ:", "").strip()
                    
                    # なし、none、該当なしの場合はスキップ
                    if category_str.lower() in ["なし", "none", "該当なし", "無し"]:
                        continue
                    
                    # 複数カテゴリ対応
                    import re
                    cats = re.split(r'[,、]', category_str)
                    for cat in cats:
                        cat = cat.strip()
                        if cat:
                            categories.append(cat)
                            
                elif line.startswith("理由:"):
                    reason = line.replace("理由:", "").strip()
                    
                elif line.startswith("検出語句:"):
                    words_str = line.replace("検出語句:", "").strip()
                    if words_str and words_str.lower() not in ["なし", "none", "該当なし"]:
                        detected_words = [w.strip() for w in re.split(r'[,、]', words_str) if w.strip()]
            
            # カテゴリ詳細の作成
            categories_detail = []
            if categories:
                for cat_name in categories:
                    # カテゴリごとのスコアを総合スコアから推定
                    cat_score = total_score * 0.8 if cat_name in ["重度の毒性", "ヘイトスピーチ"] else total_score * 0.6
                    categories_detail.append({
                        "name": cat_name,
                        "score": cat_score,
                        "keywords": detected_words  # 全体の検出語句を使用
                    })
            elif total_score >= 0.3:
                # カテゴリが指定されていない場合、スコアから推定
                if total_score >= 0.8:
                    cat_name = "重度の毒性"
                elif total_score >= 0.5:
                    cat_name = "ヘイトスピーチ"
                else:
                    cat_name = "軽度の毒性"
                
                categories_detail.append({
                    "name": cat_name,
                    "score": total_score,
                    "keywords": detected_words
                })
            
            return {
                "text": original_text,
                "toxicity_score": total_score,
                "is_toxic": total_score >= 0.3,
                "categories_detail": categories_detail,
                "confidence": 0.9 if total_score > 0 else 0.95,
                "details": {
                    "model": self.model_name,
                    "reason": reason,
                    "api_used": True,
                    "cached": False,
                    "response_time": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"レスポンス解析エラー: {e}")
            return self._get_default_result(original_text)
    
    def _update_cache(self, text: str, result: Dict) -> None:
        """キャッシュを更新"""
        # キャッシュサイズ制限
        if len(self._cache) >= self._cache_size:
            # 最も古いエントリを削除
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        
        self._cache[text] = result.copy()
    
    def _get_default_result(self, text: str = "") -> Dict:
        """APIが利用できない場合のデフォルト結果"""
        return {
            "text": text,
            "toxicity_score": 0.0,
            "is_toxic": False,
            "categories_detail": [],
            "confidence": 0.0,
            "details": {
                "model": self.model_name,
                "api_used": False,
                "error": "API unavailable or disabled",
                "cached": False
            }
        }


# テストコード
if __name__ == "__main__":
    import asyncio
    
    # シンプルなテスト
    print("=== Claude API テスト ===")
    print(f"API使用: {settings.USE_EXTERNAL_APIS}")
    print(f"APIキー: {'設定済み' if settings.ANTHROPIC_API_KEY else '未設定'}")
    print("-" * 50)
    
    analyzer = ClaudeAnalyzer()
    
    test_cases = [
        "こんにちは、良い天気ですね",
        "死ね",
        "バカ",
        "あなたは素晴らしい人です",
        "うざい、消えろ",
    ]
    
    for text in test_cases:
        print(f"\nテキスト: {text}")
        try:
            score, categories, confidence = analyzer.analyze(text)
            
            print(f"総合スコア: {score:.3f}")
            print(f"有害判定: {'🚨 有害' if score >= 0.3 else '✅ 安全'}")
            print(f"信頼度: {confidence:.2f}")
            
            if categories:
                print("カテゴリ詳細:")
                for cat in categories:
                    print(f"  - {cat.name}: スコア {cat.score:.2f}")
                    if cat.keywords_found:
                        print(f"    検出語句: {', '.join(cat.keywords_found)}")
        except Exception as e:
            print(f"エラー: {e}")
            import traceback
            traceback.print_exc()
        print("-" * 30)
"""
キーワードベースの毒性分析サービス
リリース1のコア機能
完全修正版
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple
from app.models.schemas import ToxicityCategory
import logging
import os

logger = logging.getLogger(__name__)

class KeywordAnalyzer:
    """キーワードベースの毒性分析器"""
    
    def __init__(self):
        """初期化：キーワードデータを読み込む"""
        self.data = self._load_keywords()
        self.categories = self.data["categories"]
        self.modifiers = self.data["modifiers"]
        logger.info("KeywordAnalyzer initialized")
        
    def _load_keywords(self) -> Dict:
        """キーワードデータを読み込む"""
        # Docker環境とローカル環境の両方に対応
        possible_paths = [
            "/app/app/data/toxic_keywords.json",  # Docker環境
            "/app/data/toxic_keywords.json",       # 別のDocker構成
            Path(__file__).parent.parent / "data" / "toxic_keywords.json",  # ローカル環境
        ]
        
        data_path = None
        for path in possible_paths:
            if os.path.exists(str(path)):
                data_path = path
                logger.info(f"Found toxic_keywords.json at: {path}")
                break
        
        if data_path is None:
            raise FileNotFoundError(
                f"toxic_keywords.json not found. Searched paths: {possible_paths}"
            )
        
        with open(data_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def analyze(self, text: str) -> Tuple[float, List[ToxicityCategory], float]:
        """テキストを分析して毒性スコアを返す"""
        # 1. テキストの前処理
        normalized_text = self._normalize_text(text)
        
        # 2. カテゴリ別の分析
        categories_result = []
        total_score = 0.0
        max_score = 0.0
        
        for category_id, category_data in self.categories.items():
            score, found_keywords = self._analyze_category(
                normalized_text, 
                category_data
            )
            
            if score > 0:
                categories_result.append(ToxicityCategory(
                    name=category_data["name"],
                    score=score,
                    keywords_found=found_keywords
                ))
                
                weighted_score = score * category_data["weight"]
                total_score += weighted_score
                max_score = max(max_score, weighted_score)
        
        # 3. 最終スコアの計算
        if len(categories_result) > 0:
            avg_score = total_score / len(categories_result)
            final_score = (max_score * 0.8) + (avg_score * 0.2)
            final_score = min(1.0, final_score)
        else:
            final_score = 0.0
        
        # 4. 信頼度の計算
        confidence = self._calculate_confidence(categories_result, len(text))
        
        return final_score, categories_result, confidence
    
    def _normalize_text(self, text: str) -> str:
        """テキストの正規化"""
        text = text.lower()
        text = re.sub(r'\s+', ' ', text)
        text = text.translate(str.maketrans(
            'ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ０１２３４５６７８９',
            'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
        ))
        return text
    
    def _analyze_category(self, text: str, category_data: Dict) -> Tuple[float, List[str]]:
        """カテゴリ別の分析"""
        keywords = category_data["keywords"]
        found_keywords = []
        
        for keyword in keywords:
            if keyword in text:
                found_keywords.append(keyword)
                
                for intensifier in self.modifiers["intensifiers"]:
                    if f"{intensifier}{keyword}" in text:
                        found_keywords.append(f"{intensifier}{keyword}")
        
        if found_keywords:
            unique_keywords = list(set(found_keywords))
            weight = category_data.get("weight", 0.5)
            
            # カテゴリの重要度に応じてスコアを調整
            if weight >= 1.0:  # 重度の毒性
                if len(unique_keywords) == 1:
                    score = 0.8
                else:
                    score = 1.0
            elif weight >= 0.8:  # 中程度の毒性
                if len(unique_keywords) == 1:
                    score = 0.6
                elif len(unique_keywords) == 2:
                    score = 0.8
                else:
                    score = 1.0
            else:  # 軽度の毒性
                if len(unique_keywords) == 1:
                    score = 0.4
                elif len(unique_keywords) == 2:
                    score = 0.6
                else:
                    score = 0.8
        else:
            score = 0.0
            
        return score, found_keywords
    
    def _calculate_confidence(self, categories: List[ToxicityCategory], text_length: int) -> float:
        """信頼度の計算"""
        if not categories:
            return 0.9
        
        total_keywords = sum(len(cat.keywords_found) for cat in categories)
        
        if text_length < 10 and total_keywords > 0:
            return 1.0
        
        keyword_density = total_keywords / max(text_length / 10, 1)
        confidence = min(0.7 + (keyword_density * 0.3), 1.0)
        
        return confidence
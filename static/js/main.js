// デモ機能の実装
document.addEventListener('DOMContentLoaded', function() {
    const analyzeBtn = document.getElementById('analyze-btn');
    const demoText = document.getElementById('demo-text');
    const demoResult = document.getElementById('demo-result');
    const resultLabel = document.getElementById('result-label');
    const resultScore = document.getElementById('result-score');
    const categoryList = document.getElementById('category-list');
    const confidenceScore = document.getElementById('confidence-score');

    // 分析処理中フラグ（新規追加）
    let isAnalyzing = false;

    // 分析ボタンのクリックイベント
    analyzeBtn.addEventListener('click', async function() {
        // 連続クリック防止（新規追加）
        if (isAnalyzing) return;
        
        const text = demoText.value.trim();
        
        // 入力チェック
        if (!text) {
            alert('テキストを入力してください');
            return;
        }

        // 分析開始（ここから修正部分）
        isAnalyzing = true;
        analyzeBtn.disabled = true;
        analyzeBtn.textContent = '分析中...';
        
        // 結果エリアを事前に表示（ローディング状態）- 新規追加
        demoResult.style.display = 'block';
        resultLabel.textContent = '分析中...';
        resultLabel.className = 'result-label';
        resultScore.textContent = '';
        categoryList.innerHTML = '<span style="color: #94a3b8;">分析しています...</span>';
        confidenceScore.textContent = '...';

        try {
            // APIにリクエスト送信（URLを/api/v1/analyzeに変更）
            const response = await fetch('/api/v1/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    text: text
                    // strategyを削除（v1は不要）
                })
            });

            if (!response.ok) {
                throw new Error('分析に失敗しました');
            }

            const data = await response.json();
            
            // 結果を表示
            displayResult(data);
            
        } catch (error) {
            console.error('Error:', error);
            alert('エラーが発生しました。もう一度お試しください。');
            demoResult.style.display = 'none';  // エラー時は非表示に
        } finally {
            // ボタンを有効化（isAnalyzingフラグも追加）
            isAnalyzing = false;
            analyzeBtn.disabled = false;
            analyzeBtn.textContent = '分析する';
        }
    });

    // 結果表示関数（アニメーション追加）
    function displayResult(data) {
        // アニメーション用に一度非表示（新規追加）
        demoResult.style.opacity = '0';
        
        setTimeout(() => {
            const scorePercent = Math.round(data.toxicity_score * 100);
        
        // 3段階判定
        if (data.toxicity_score < 0.1) {  // 10%未満
            resultLabel.textContent = '✅ 安全なコンテンツ';
            resultLabel.className = 'result-label safe';
            resultScore.style.color = '#10b981';
        } else if (data.toxicity_score < 0.5) {  // 10-49%
            resultLabel.textContent = '⚡ 軽度の毒性';
            resultLabel.className = 'result-label mild';
            resultScore.style.color = '#f59e0b';  // オレンジ色
        } else {  // 50%以上
            resultLabel.textContent = '⚠️ 有害なコンテンツ';
            resultLabel.className = 'result-label toxic';
            resultScore.style.color = '#ef4444';
        }
        
        // スコアの表示
        resultScore.textContent = `${scorePercent}%`;
            
            // カテゴリの表示（修正版）
			categoryList.innerHTML = '';
			if (data.categories && data.categories.length > 0) {
    		data.categories.forEach(category => {
        		const tag = document.createElement('span');
        		tag.className = 'category-tag';
        		// オブジェクトの場合はnameプロパティを使用
        		const categoryName = typeof category === 'object' ? category.name : category;
        		tag.textContent = getCategoryName(categoryName);
        		categoryList.appendChild(tag);
    		});
		} else {
    		categoryList.innerHTML = '<span style="color: #94a3b8;">検出されたカテゴリはありません</span>';
		}
            
            // 信頼度の表示
            const confidencePercent = Math.round(data.confidence * 100);
            confidenceScore.textContent = `${confidencePercent}%`;
            
            // フェードイン（新規追加）
            demoResult.style.opacity = '1';
        }, 100);
    }

    // カテゴリ名の日本語化
    function getCategoryName(category) {
        const categoryMap = {
            'severe_toxicity': '重度の毒性',
            'hate': 'ヘイトスピーチ',
            'violence': '暴力的表現',
            'sexual': '性的な内容',
            'discrimination': '差別的表現',
            'mild_toxicity': '軽度の毒性'
        };
        return categoryMap[category] || category;
    }

    // テキストエリアでEnter+Shiftで分析実行（isAnalyzingチェック追加）
    demoText.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && e.shiftKey && !isAnalyzing) {
            e.preventDefault();
            analyzeBtn.click();
        }
    });

    // テキストが変更されたら結果をクリア（新規追加）
    let typingTimer;
    demoText.addEventListener('input', function() {
        clearTimeout(typingTimer);
        typingTimer = setTimeout(() => {
            if (demoResult.style.display === 'block' && demoText.value.trim() === '') {
                demoResult.style.opacity = '0';
                setTimeout(() => {
                    demoResult.style.display = 'none';
                }, 300);
            }
        }, 1000);
    });

    // スムーズスクロール
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // ナビゲーションの背景色変更
    const navbar = document.querySelector('.navbar');
    window.addEventListener('scroll', function() {
        if (window.scrollY > 50) {
            navbar.style.background = 'rgba(15, 23, 42, 0.95)';
        } else {
            navbar.style.background = 'rgba(15, 23, 42, 0.8)';
        }
    });
});

// APIキー取得ページへのリダイレクト（仮実装）
document.querySelectorAll('a[href="#api"]').forEach(link => {
    link.addEventListener('click', function(e) {
        e.preventDefault();
        // 後でAPIキー取得ページを実装
        alert('APIキー取得機能は準備中です。\nお問い合わせ: support@toxiguard-api.com');
    });
});
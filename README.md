# ToxiGuard API

日本語テキストの毒性を検知するAPIサービス

## 🚀 プロジェクト概要

- **目的**: 日本語コンテンツの毒性を自動検出
- **目標**: 4日間で精度95%のSaaS構築
- **現在**: Release 1完成（精度40%）

## 📅 開発スケジュール

- [x] **Release 1** (3時間) - キーワードベース検知 ✅ 2025-06-06
- [ ] **Release 2** (6時間) - rinna AI統合
- [ ] **Release 3** (9時間) - マルチモデル
- [ ] **Release 4** (12時間) - 完全版

## 🎉 Release 1 完成内容

### 機能
- ✅ キーワードベース毒性検知（精度40%）
- ✅ 6カテゴリ分類
  - 重度の毒性（死ね、殺す等）
  - ヘイトスピーチ（きもい、クズ等）
  - 暴力的表現
  - 性的な内容
  - 差別的表現
  - 軽度の毒性（バカ、アホ等）
- ✅ REST API（FastAPI）
- ✅ Swagger UI
- ✅ 日本語完全対応

### 技術スタック
- Python 3.12
- FastAPI
- Pydantic
- uvicorn

## 🔧 セットアップ

```bash
# リポジトリをクローン
git clone https://github.com/toxiguard-api/toxiguard-api.git
cd toxiguard-api

# 仮想環境を作成
python3 -m venv venv
source venv/bin/activate

# 依存関係をインストール
pip install -r requirements.txt

# サーバーを起動
uvicorn main:app --reload

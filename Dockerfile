FROM python:3.11-slim

# 作業ディレクトリの設定
WORKDIR /app

# システムパッケージの更新とPostgreSQL開発ツールのインストール
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Pythonパッケージのアップグレード
RUN pip install --upgrade pip

# 依存関係のインストール（キャッシュ効率化のため先に実行）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションのコピー
COPY . .

# ポート設定（Renderは$PORTを使用）
EXPOSE 10000

# 起動コマンド（本番用のmain.pyを使用）
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
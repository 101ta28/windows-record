# Windows Record

## 概要

このプロジェクトは、Windows環境で画面・Webカメラ・音声を同時に録画できるPythonスクリプト群です。  
単体での録画（`record.py`）、複数PCの一斉録画制御（`client.py` + `master.py`）に対応しています。

---

## 環境構築

### uv を用いる場合

1. `uv sync` を実行してください。
2. `uv run <filename>.py`を実行してください。

3. **Python 3.12 以上をインストール**  
   `.python-version`ファイルに記載されています。

4. **ffmpeg をインストール**  
   Windowsの場合、以下のコマンドでインストールできます。  

   ```powershell
   winget install --id=Gyan.FFmpeg -e
   ```

5. **録音・録画デバイス名の確認**  
   コマンドプロンプトで以下を実行し、AUDIO_DEVICE・WEBCAM_DEVICEの値を調べてください。  

   ```powershell
   ffmpeg -list_devices true -f dshow -i dummy
   ```

6. **依存パッケージ**  
   標準ライブラリのみ使用しています。追加インストールは不要です。

7. **開発用依存パッケージ**
   フォーマッタとしてRuffを導入しています。

---

## 各プログラムの使い方

### 1. 単体録画: [`record.py`](record.py)

- 画面・Webカメラ・音声を同時に録画します。
- 録画ファイルは `screen_YYYYMMDD_HHMMSS.mp4`、`webcam_YYYYMMDD_HHMMSS.mp4` 形式で保存されます。

#### 実行方法

```powershell
uv run record.py
```

- Enterキーを押すと録画が停止し、ファイルが保存されます。

---

### 2. サーバークライアント録画: [`client.py`](client.py) + [`master.py`](master.py)

#### 概要

- `client.py` を各録画PCで起動しておき、`master.py` から一斉に録画開始・停止命令を送信できます。

#### 使い方

##### 1. クライアント側（録画PC）で [`client.py`](client.py) を起動

```powershell
uv run client.py
```

- デフォルトでポート5001で待機します。
- 録画ファイルは `screen_YYYYMMDD_HHMMSS.mp4`、`webcam_YYYYMMDD_HHMMSS.mp4` 形式で保存されます。
- プログラムの停止は `Ctrl + C` を行ってください。

###### バッチファイルによる起動

- [`client_launcher.bat`](client_launcher.bat) をダブルクリックすることで、コマンドプロンプトを表示せずにクライアント録画プログラム（`client_recorder.py`）をバックグラウンドで起動できます。
- Windowsのスタートアップに登録することで、PC起動時に自動で録画クライアントを立ち上げる運用も可能です。

##### 2. マスター側（制御PC）で [`master.py`](master.py) を起動

```powershell
uv run master.py
```

- `CLIENTS`リストに制御したいPCのIPアドレスを記載してください。
- 起動後、以下のコマンドを入力できます:
  - `start` : 全クライアントで録画開始
  - `stop`  : 全クライアントで録画停止
  - `exit`  : プログラム終了

---

## 注意事項

- 録画デバイス名（AUDIO_DEVICE, WEBCAM_DEVICE）は各PCの環境に合わせて設定してください。
- ffmpegのパスが通っていない場合は、環境変数PATHに追加してください。
- 録画ファイルはスクリプトを実行したディレクトリに保存されます。

---

## 参考

- ffmpeg公式: <https://ffmpeg.org/>
- uv公式: <https://docs.astral.sh/uv/>
- Python公式: <https://www.python.org/>

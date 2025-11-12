@echo off
REM --- uv をインストール ---
powershell -NoProfile -ExecutionPolicy Bypass -Command "irm 'https://astral.sh/uv/install.ps1' | iex"
IF %ERRORLEVEL% NEQ 0 (
  echo uv のインストールでエラーが発生しました。処理を中断します.
  pause
  exit /b %ERRORLEVEL%
)

REM --- ffmpeg を winget でインストール ---
powershell -NoProfile -ExecutionPolicy Bypass -Command "winget install --id=Gyan.FFmpeg -e"
IF %ERRORLEVEL% NEQ 0 (
  echo winget による ffmpeg のインストールでエラーが発生しました。
  pause
  exit /b %ERRORLEVEL%
)

echo インストールが完了しました。
pause

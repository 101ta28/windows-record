@echo off
setlocal

:: -------------------------
:: 設定
:: -------------------------
set "LOG=%TEMP%\install_uv_ffmpeg_%RANDOM%.log"
echo ログ: %LOG%

:: -------------------------
:: 管理者チェック（昇格）
:: -------------------------
powershell -NoProfile -Command ^
  "if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] 'Administrator')) { Start-Process -FilePath '%~f0' -Verb RunAs; exit 1 }"
if %ERRORLEVEL% NEQ 0 (
  echo 管理者権限が必要です。昇格した新しいウィンドウで再実行してください。
  pause
  exit /b %ERRORLEVEL%
)

:: -------------------------
:: winget の存在確認
:: -------------------------
where winget >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
  echo winget (App Installer) が見つかりません。Microsoft Store の "App Installer" をインストールしてください。
  echo （参照）https://aka.ms/getwinget
  pause
  exit /b 1
)

:: -------------------------
:: uv をインストール
:: -------------------------
echo --- uv をインストール中 ---
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
"try {
  $uri = 'https://astral.sh/uv/install.ps1';
  Write-Output 'Downloading ' + $uri;
  $script = Invoke-RestMethod -Uri $uri -ErrorAction Stop;
  Invoke-Expression $script;
  Write-Output 'uv インストール スクリプトを実行しました。';
} catch {
  Write-Error $_.Exception.Message;
  exit 1
}" > "%LOG%" 2>&1
if %ERRORLEVEL% NEQ 0 (
  echo uv のインストールでエラーが発生しました。ログを表示します。
  type "%LOG%"
  pause
  exit /b %ERRORLEVEL%
)

:: -------------------------
:: ffmpeg を winget でインストール
:: -------------------------
echo --- ffmpeg を winget でインストール中 ---
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
"try {
  $args = 'install --id=Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements --silent';
  Write-Output 'winget ' + $args;
  & winget install --id=Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements --silent
  if ($LASTEXITCODE -ne 0) { throw 'winget が非ゼロ終了コードを返しました: ' + $LASTEXITCODE }
} catch {
  Write-Error $_.Exception.Message;
  exit 1
}" >> "%LOG%" 2>&1
if %ERRORLEVEL% NEQ 0 (
  echo ffmpeg のインストールでエラーが発生しました。ログを表示します。
  type "%LOG%"
  pause
  exit /b %ERRORLEVEL%
)

:: -------------------------
:: インストール確認
:: -------------------------
echo --- インストール確認 ---
where uv >nul 2>&1
if %ERRORLEVEL% EQU 0 (
  echo uv が PATH に見つかりました。バージョン:
  uv --version 2>nul || echo uv コマンドの実行に失敗しました。
) else (
  echo uv が見つかりません。インストール先が PATH にない可能性があります。
)

where ffmpeg >nul 2>&1
if %ERRORLEVEL% EQU 0 (
  echo ffmpeg が PATH に見つかりました。バージョン:
  ffmpeg -version 2>nul || echo ffmpeg コマンドの実行に失敗しました。
) else (
  echo ffmpeg が見つかりません。winget のインストールが失敗した可能性があります。
)

echo インストール処理は完了しました。詳細ログ: %LOG%
pause
endlocal
exit /b 0
@echo off
setlocal

:: -------------------------
:: Configuration
:: -------------------------
set "LOG=%TEMP%\install_uv_ffmpeg_%RANDOM%.log"
echo Log file: %LOG%

:: -------------------------
:: Admin check (elevate if needed)
:: -------------------------
powershell -NoProfile -Command ^
  "if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] 'Administrator')) { Start-Process -FilePath '%~f0' -Verb RunAs; exit 1 }"
if %ERRORLEVEL% NEQ 0 (
  echo Administrative privileges are required. Please allow elevation in the newly opened window.
  pause
  exit /b %ERRORLEVEL%
)

:: -------------------------
:: Check for winget
:: -------------------------
where winget >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
  echo winget (App Installer) was not found. Please install "App Installer" from Microsoft Store.
  echo (See) https://aka.ms/getwinget
  pause
  exit /b 1
)

:: -------------------------
:: Install uv
:: -------------------------
echo --- Installing uv ---
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
"try {
  $uri = 'https://astral.sh/uv/install.ps1';
  Write-Output 'Downloading ' + $uri;
  $script = Invoke-RestMethod -Uri $uri -ErrorAction Stop;
  Invoke-Expression $script;
  Write-Output 'Executed uv install script.';
} catch {
  Write-Error $_.Exception.Message;
  exit 1
}" > "%LOG%" 2>&1
if %ERRORLEVEL% NEQ 0 (
  echo Error occurred during uv installation. Showing log:
  type "%LOG%"
  pause
  exit /b %ERRORLEVEL%
)

:: -------------------------
:: Install ffmpeg with winget
:: -------------------------
echo --- Installing ffmpeg (winget) ---
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
"try {
  $args = 'install --id=Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements --silent';
  Write-Output 'Running: winget ' + $args;
  & winget install --id=Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements --silent
  if ($LASTEXITCODE -ne 0) { throw 'winget returned non-zero exit code: ' + $LASTEXITCODE }
} catch {
  Write-Error $_.Exception.Message;
  exit 1
}" >> "%LOG%" 2>&1
if %ERRORLEVEL% NEQ 0 (
  echo Error occurred during ffmpeg installation. Showing log:
  type "%LOG%"
  pause
  exit /b %ERRORLEVEL%
)

:: -------------------------
:: Verify installations
:: -------------------------
echo --- Verifying installations ---
where uv >nul 2>&1
if %ERRORLEVEL% EQU 0 (
  echo uv found in PATH. Version:
  uv --version 2>nul || echo Failed to run 'uv --version'.
) else (
  echo uv not found in PATH. The installation location might not be added to PATH.
)

where ffmpeg >nul 2>&1
if %ERRORLEVEL% EQU 0 (
  echo ffmpeg found in PATH. Version:
  ffmpeg -version 2>nul || echo Failed to run 'ffmpeg -version'.
) else (
  echo ffmpeg not found in PATH. winget installation may have failed or PATH was not updated.
)

echo Installation process finished. Log file: %LOG%
pause
endlocal
exit /b 0

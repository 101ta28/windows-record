<#
.SYNOPSIS
  Install uv and ffmpeg (Gyan.FFmpeg) with robust error handling and logging.

.INSTRUCTIONS
  1. Save this file as install_uv_ffmpeg.ps1 (prefer UTF-8 without BOM).
  2. Right-click -> Run with PowerShell, or execute in an elevated PowerShell console.
     The script will attempt to auto-elevate via UAC if not already elevated.
#>

# Ensure script stops on errors
$ErrorActionPreference = 'Stop'

# Prepare log
$LogFile = Join-Path $env:TEMP ("install_uv_ffmpeg_{0}.log" -f ([guid]::NewGuid().ToString()))
function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $time = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    $line = "[$time] [$Level] $Message"
    $line | Tee-Object -FilePath $LogFile -Append
}

# Elevate if not running as Administrator
function Ensure-RunningAsAdmin {
    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $isAdmin) {
        Write-Log "Not running as administrator. Attempting to relaunch elevated..." "INFO"
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = (Get-Command powershell).Source
        $args = @(
            "-NoProfile"
            "-ExecutionPolicy Bypass"
            "-File"
            "`"$PSCommandPath`""
        ) -join ' '
        $psi.Arguments = $args
        $psi.Verb = "runas"
        try {
            [System.Diagnostics.Process]::Start($psi) | Out-Null
            Write-Log "Relaunch requested. Exiting current process." "INFO"
            Exit 0
        } catch {
            Write-Log "Elevation request failed: $($_.Exception.Message)" "ERROR"
            throw "Administrator privileges are required."
        }
    } else {
        Write-Log "Already running as Administrator." "INFO"
    }
}

# Check for winget
function Ensure-WingetPresent {
    try {
        $wg = Get-Command winget -ErrorAction Stop
        Write-Log "winget found: $($wg.Source)" "INFO"
    } catch {
        Write-Log "winget (App Installer) not found. Please install 'App Installer' from Microsoft Store: https://aka.ms/getwinget" "ERROR"
        throw "winget not found"
    }
}

# Install uv from official script
function Install-UV {
    param([string]$InstallerUri = "https://astral.sh/uv/install.ps1")
    Write-Log "Installing uv from $InstallerUri" "INFO"

    try {
        # Ensure TLS 1.2
        try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 } catch { }

        Write-Log "Downloading uv installer script..." "INFO"
        $scriptContent = Invoke-RestMethod -Uri $InstallerUri -ErrorAction Stop
        Write-Log "Downloaded installer script (length $($scriptContent.Length)). Executing..." "INFO"

        # Execute in its own scope
        Invoke-Expression $scriptContent

        Write-Log "uv install script executed. Please check output above for details." "INFO"
    } catch {
        Write-Log "uv installation failed: $($_.Exception.Message)" "ERROR"
        throw
    }
}

# Install ffmpeg via winget
function Install-FFmpeg {
    Write-Log "Installing ffmpeg via winget (Gyan.FFmpeg)..." "INFO"

    $args = @(
        'install'
        '--id=Gyan.FFmpeg'
        '-e'
        '--accept-source-agreements'
        '--accept-package-agreements'
        '--silent'
    )
    try {
        $proc = Start-Process -FilePath "winget" -ArgumentList $args -NoNewWindow -Wait -PassThru -ErrorAction Stop
        if ($proc.ExitCode -ne 0) {
            Write-Log "winget returned non-zero exit code: $($proc.ExitCode)" "ERROR"
            throw "winget install failed with exit code $($proc.ExitCode)"
        } else {
            Write-Log "winget install completed successfully (exit code 0)." "INFO"
        }
    } catch {
        Write-Log "ffmpeg installation via winget failed: $($_.Exception.Message)" "ERROR"
        throw
    }
}

# Verify installation
function Verify-Installations {
    Write-Log "Verifying installations..." "INFO"

    try {
        $uvCmd = Get-Command uv -ErrorAction SilentlyContinue
        if ($null -ne $uvCmd) {
            Write-Log "uv command found at: $($uvCmd.Source)" "INFO"
            try {
                $uvVersion = & uv --version 2>&1
                Write-Log "uv --version output:`n$uvVersion" "INFO"
            } catch {
                Write-Log "Failed to run 'uv --version': $($_.Exception.Message)" "WARN"
            }
        } else {
            Write-Log "uv not found in PATH." "WARN"
        }

        $ffmpegCmd = Get-Command ffmpeg -ErrorAction SilentlyContinue
        if ($null -ne $ffmpegCmd) {
            Write-Log "ffmpeg command found at: $($ffmpegCmd.Source)" "INFO"
            try {
                $ffmpegVersion = & ffmpeg -version 2>&1 | Select-Object -First 1
                Write-Log "ffmpeg -version output: $ffmpegVersion" "INFO"
            } catch {
                Write-Log "Failed to run 'ffmpeg -version': $($_.Exception.Message)" "WARN"
            }
        } else {
            Write-Log "ffmpeg not found in PATH." "WARN"
        }
    } catch {
        Write-Log "Verification step failed: $($_.Exception.Message)" "ERROR"
    }
}

# MAIN
try {
    Write-Log "===== Start install_uv_ffmpeg.ps1 =====" "INFO"
    Ensure-RunningAsAdmin
    Ensure-WingetPresent

    Install-UV
    Install-FFmpeg

    Verify-Installations

    Write-Log "Installation sequence finished." "INFO"
    Write-Host ""
    Write-Host "Installation finished. Log file: $LogFile" -ForegroundColor Green
    Write-Host "If something failed, please paste the last lines of the log file here."
    Write-Host ""
    Write-Host "To open the log now: notepad `"$LogFile`""
} catch {
    Write-Host ""
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "A detailed log is available at: $LogFile"
    Write-Host "Open the log with: notepad `"$LogFile`""
    Write-Log "Script terminated with error: $($_.Exception.Message)" "ERROR"
    Exit 1
}

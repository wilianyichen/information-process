param(
    [string]$PythonExe = ".\.venv\Scripts\python.exe",
    [string]$ConfigPath = ".\config.toml",
    [string]$Profile = "quality",
    [string]$CacheDir = ".\.infoproc\models",
    [string]$HfHome = ".\.infoproc\hf_home",
    [string]$Device = "cuda",
    [switch]$DownloadDiarization
)

if (-not (Test-Path $PythonExe)) {
    throw "Python executable not found: $PythonExe"
}

New-Item -ItemType Directory -Force -Path $CacheDir | Out-Null
New-Item -ItemType Directory -Force -Path $HfHome | Out-Null
$scriptRoot = Join-Path $CacheDir "_script_cache"
New-Item -ItemType Directory -Force -Path $scriptRoot | Out-Null

Write-Host "Downloading faster-whisper model via infoproc CLI"
& $PythonExe -m infoproc --config $ConfigPath download-model --profile $Profile --cache-dir $CacheDir
if ($LASTEXITCODE -ne 0) {
    throw "Failed to download transcription model"
}

if ($DownloadDiarization) {
    if (-not $env:HF_TOKEN) {
        throw "HF_TOKEN is required when -DownloadDiarization is used"
    }

    $diarizationScript = Join-Path $scriptRoot "download_diarization_model.py"
    @"
import os
from whisperx.diarize import DiarizationPipeline
os.environ["HF_HOME"] = r"$((Resolve-Path $HfHome).Path)"
DiarizationPipeline(model_name="pyannote/speaker-diarization-3.1", use_auth_token=os.environ["HF_TOKEN"], device="$Device")
print("diarization model ready")
"@ | Set-Content -Path $diarizationScript -Encoding UTF8

    & $PythonExe $diarizationScript
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to download diarization model"
    }
}

Write-Host "Model download completed"

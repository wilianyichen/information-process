param(
    [string]$ApiKey,
    [string]$BaseUrl,
    [string]$Model,
    [string]$HfToken,
    [string]$EnvFilePath = ".\deploy\linux\infoproc.env.example"
)

function Read-EnvValue {
    param(
        [string]$Path,
        [string[]]$Names
    )

    if (-not (Test-Path $Path)) {
        return $null
    }

    foreach ($name in $Names) {
        $line = Get-Content $Path | Where-Object { $_ -match "^$name=" } | Select-Object -First 1
        if ($line) {
            return ($line -replace "^$name=", "").Trim('"')
        }
    }
    return $null
}

if (-not $BaseUrl) {
    $BaseUrl = Read-EnvValue -Path $EnvFilePath -Names @("INFOPROC_BASE_URL", "BASE_URL")
}
if (-not $Model) {
    $Model = Read-EnvValue -Path $EnvFilePath -Names @("INFOPROC_MODEL", "MODEL")
}
if (-not $ApiKey) {
    $ApiKey = Read-EnvValue -Path $EnvFilePath -Names @("INFOPROC_API_KEY", "API_KEY")
}
if (-not $HfToken) {
    $HfToken = Read-EnvValue -Path $EnvFilePath -Names @("HF_TOKEN")
}

if ($ApiKey) {
    $env:INFOPROC_API_KEY = $ApiKey
}
if ($BaseUrl) {
    $env:INFOPROC_BASE_URL = $BaseUrl
}
if ($Model) {
    $env:INFOPROC_MODEL = $Model
}
if ($HfToken) {
    $env:HF_TOKEN = $HfToken
}

Write-Host "INFOPROC_API_KEY set for current session:" ([bool]$env:INFOPROC_API_KEY)
Write-Host "INFOPROC_BASE_URL:" $env:INFOPROC_BASE_URL
Write-Host "INFOPROC_MODEL:" $env:INFOPROC_MODEL
Write-Host "HF_TOKEN set for current session:" ([bool]$env:HF_TOKEN)

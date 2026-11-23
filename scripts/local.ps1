param(
    [ValidateSet('serve', 'migrate', 'seed', 'train', 'index', 'check', 'images', 'purge')]
    [string]$Action = 'serve'
)
$ErrorActionPreference = 'Stop'
$projectDirectory = Split-Path -Parent $PSScriptRoot
$pythonExecutable = Join-Path $projectDirectory '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonExecutable)) {
    throw 'Create .venv and install requirements-lock.txt first. See README.md.'
}
Push-Location $projectDirectory
try {
    # One stable random local key keeps sessions valid between restarts. It stays
    # in ignored instance/, never in source control or console output.
    $instanceDirectory = Join-Path $projectDirectory 'instance'
    New-Item -ItemType Directory -Path $instanceDirectory -Force | Out-Null
    $secretPath = Join-Path $instanceDirectory 'local-secret.txt'
    if (-not (Test-Path -LiteralPath $secretPath)) {
        $secretBytes = New-Object byte[] 48
        $generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
        try { $generator.GetBytes($secretBytes) } finally { $generator.Dispose() }
        [System.IO.File]::WriteAllText($secretPath, [Convert]::ToBase64String($secretBytes))
    }
    $env:SECRET_KEY = [System.IO.File]::ReadAllText($secretPath).Trim()
    $env:APP_ENV = 'development'
    # This helper deliberately selects only this project's local data.
    $env:DATABASE_URL = 'sqlite:///' + (Join-Path $instanceDirectory 'market-mirror.sqlite').Replace('\', '/')
    $env:UPLOAD_FOLDER = Join-Path $instanceDirectory 'uploads'
    $env:AI_FOLDER = Join-Path $instanceDirectory 'ai'
    switch ($Action) {
        'serve' { & $pythonExecutable -m waitress --listen=127.0.0.1:5000 wsgi:application }
        'migrate' { & $pythonExecutable -m flask --app app:create_app db upgrade }
        'seed' { & $pythonExecutable -m flask --app app:create_app seed }
        'train' { & $pythonExecutable -m flask --app app:create_app ai train }
        'index' { & $pythonExecutable -m flask --app app:create_app ai index }
        'check' { & $pythonExecutable -m flask --app app:create_app db check }
        'images' { & $pythonExecutable -m flask --app app:create_app maintenance images }
        'purge' { & $pythonExecutable -m flask --app app:create_app maintenance purge }
    }
    if ($LASTEXITCODE -ne 0) { throw "Market Mirror command failed with exit code $LASTEXITCODE" }
} finally {
    Remove-Item Env:SECRET_KEY -ErrorAction SilentlyContinue
    Pop-Location
}

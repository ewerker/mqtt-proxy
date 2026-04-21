$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $scriptDir

$envFile = Join-Path $scriptDir ".env"
if (Test-Path -LiteralPath $envFile) {
    Get-Content -LiteralPath $envFile | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) {
            return
        }

        $parts = $line.Split("=", 2)
        if ($parts.Count -eq 2) {
            $name = $parts[0].Trim()
            $value = $parts[1].Trim().Trim("'`"")
            [System.Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
}

$pythonExe = Join-Path $scriptDir ".venv\\Scripts\\python.exe"
if (-not (Test-Path -LiteralPath $pythonExe)) {
    throw "Python in .venv wurde nicht gefunden. Erwartet: $pythonExe"
}

& $pythonExe ".\\mqtt-proxy.py" @args

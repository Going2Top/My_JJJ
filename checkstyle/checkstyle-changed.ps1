[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Write-Status {
    param([string]$Message)
    Write-Host "[checkstyle-changed] $Message"
}

function Test-CommandAvailable {
    param([string]$CommandName)
    return [bool](Get-Command $CommandName -ErrorAction SilentlyContinue)
}

function Get-ChangedJavaFiles {
    $allFiles = [System.Collections.Generic.List[string]]::new()
    $gitCommands = @(
        @("diff", "--name-only", "--diff-filter=ACMRT", "--", "*.java"),
        @("diff", "--name-only", "--cached", "--diff-filter=ACMRT", "--", "*.java"),
        @("ls-files", "--others", "--exclude-standard", "--", "*.java")
    )

    foreach ($commandArgs in $gitCommands) {
        $output = & git @commandArgs
        if ($LASTEXITCODE -ne 0) {
            throw "Unable to determine changed Java files from git."
        }

        foreach ($line in ($output -split "`r?`n")) {
            $trimmed = $line.Trim()
            if ($trimmed) {
                [void]$allFiles.Add($trimmed)
            }
        }
    }

    return $allFiles | Sort-Object -Unique
}

$projectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))

try {
    Push-Location $projectRoot
    try {
        if (-not (Test-CommandAvailable -CommandName "git")) {
            throw "git was not found in PATH."
        }
        if (-not (Test-CommandAvailable -CommandName "mvn")) {
            throw "mvn was not found in PATH."
        }

        & cmd.exe /c "git rev-parse --is-inside-work-tree >nul 2>nul"
        if ($LASTEXITCODE -ne 0) {
            throw "Current project is not a git repository. Changed-file Checkstyle runs require git metadata."
        }

        $changedFiles = @(Get-ChangedJavaFiles)
        if ($changedFiles.Count -eq 0) {
            Write-Status "No changed .java files detected. Skipping Checkstyle."
            return
        }

        Write-Status ("Changed Java files:`n - " + ($changedFiles -join "`n - "))

        $failedFiles = [System.Collections.Generic.List[string]]::new()

        foreach ($relativePath in $changedFiles) {
            Write-Status "Running Checkstyle for $relativePath"
            & mvn `
                "-q" `
                "-Dcheckstyle.includes=$relativePath" `
                "-Dcheckstyle.includeResources=false" `
                "-Dcheckstyle.includeTestResources=false" `
                "-Dcheckstyle.includeTestSourceDirectory=true" `
                "-Dcheckstyle.consoleOutput=true" `
                "-Dcheckstyle.output.format=plain" `
                "checkstyle:check"

            if ($LASTEXITCODE -ne 0) {
                [void]$failedFiles.Add($relativePath)
            }
        }

        if ($failedFiles.Count -gt 0) {
            throw ("Checkstyle reported violations in:`n - " + ($failedFiles -join "`n - "))
        }

        Write-Status "Checkstyle passed for all changed Java files."
    }
    finally {
        Pop-Location
    }
}
catch {
    Write-Host "[checkstyle-changed] ERROR: $($_.Exception.Message)"
    exit 1
}

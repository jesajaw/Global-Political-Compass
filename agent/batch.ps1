<#
.SYNOPSIS
    Let the agent rate many countries for one year, one after the other.

.DESCRIPTION
    Thin PowerShell wrapper around `python -m agent.evaluate`. It does no evaluating itself:
    it loops, calls the Python CLI once per country, reads its exit code
    (0 = stored, 3 = skipped, anything else = failed) and prints a summary at the end.
    Failures don't stop the run; they are listed at the end and written to agent\logs\.

.EXAMPLE
    .\agent\batch.ps1 -Year 2025 -Country Germany, France, Poland
.EXAMPLE
    .\agent\batch.ps1 -Year 2025 -ListFile countries.txt -SkipExisting
.EXAMPLE
    .\agent\batch.ps1 -Year 2025 -All -SkipExisting     # every country in countries.json (takes long!)

    countries.txt: one country name per line, empty lines and lines starting with # are ignored.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidatePattern('^\d{4}$')][string]$Year,
    [string[]]$Country,
    [string]$ListFile,
    [switch]$All,
    [switch]$SkipExisting,
    [int]$PauseSeconds = 0
)

# Native commands writing to stderr must not abort the script in Windows PowerShell 5.1.
$ErrorActionPreference = 'Continue'

# The python module path (agent.evaluate) only resolves from the repo root.
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

# -- which countries? ---------------------------------------------------------------
if ($All) {
    $names = (Get-Content -Raw -Encoding UTF8 (Join-Path $repo 'data\countries.json') | ConvertFrom-Json).name
}
elseif ($ListFile) {
    if (-not (Test-Path $ListFile)) { Write-Error "List file not found: $ListFile"; exit 1 }
    $names = Get-Content -Encoding UTF8 $ListFile | ForEach-Object { $_.Trim() } | Where-Object { $_ -and -not $_.StartsWith('#') }
}
elseif ($Country) {
    $names = $Country
}
else {
    Write-Error 'Give -Country <names>, -ListFile <file> or -All.'
    exit 1
}

# -- run ------------------------------------------------------------------------------
$total = @($names).Count
$ok = 0; $skipped = 0; $failed = @()
$extra = if ($SkipExisting) { @('--skip-existing') } else { @() }
$started = Get-Date
$i = 0

foreach ($name in $names) {
    $i++
    Write-Host ("[{0}/{1}] {2} {3} ... " -f $i, $total, $name, $Year) -NoNewline
    $output = (& python -m agent.evaluate $name $Year @extra 2>&1 | Out-String).Trim()
    switch ($LASTEXITCODE) {
        0 { $ok++;      Write-Host 'stored'  -ForegroundColor Green }
        3 { $skipped++; Write-Host 'skipped' -ForegroundColor DarkGray }
        default {
            $failed += [pscustomobject]@{ Country = $name; Message = $output }
            Write-Host 'FAILED' -ForegroundColor Red
            Write-Host "    $output" -ForegroundColor DarkRed
        }
    }
    if ($PauseSeconds -gt 0 -and $i -lt $total) { Start-Sleep -Seconds $PauseSeconds }
}

# -- summary ----------------------------------------------------------------------------
$elapsed = (Get-Date) - $started
Write-Host ''
Write-Host ("Done in {0:hh\:mm\:ss}: {1} stored, {2} skipped, {3} failed." -f $elapsed, $ok, $skipped, $failed.Count)

if ($failed.Count -gt 0) {
    $logDir = Join-Path $PSScriptRoot 'logs'
    New-Item -ItemType Directory -Force -Path $logDir | Out-Null
    $log = Join-Path $logDir ("batch-{0:yyyyMMdd-HHmmss}.log" -f $started)
    $failed | ForEach-Object { "{0}`t{1}" -f $_.Country, ($_.Message -replace '\s+', ' ') } | Set-Content -Encoding UTF8 $log
    Write-Host "Failures written to $log  (re-run with -SkipExisting to only retry what is missing)"
    exit 1
}

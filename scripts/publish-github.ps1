# Run from repo root AFTER: gh auth login
# Creates github.com/<you>/home-assistant-tarot-api (public), fixes manifest URLs, pushes main.

$ErrorActionPreference = "Stop"
$RepoName = "home-assistant-tarot-api"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

# Need at least one commit before gh repo create --push
$prevEap = $ErrorActionPreference
$ErrorActionPreference = "SilentlyContinue"
git log -1 --format=%H | Out-Null
$hasCommit = ($LASTEXITCODE -eq 0)
$ErrorActionPreference = $prevEap
if (-not $hasCommit) {
    git add -A
    git commit -m "Initial commit: Tarot API Home Assistant integration"
}

gh auth status | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Error "GitHub CLI is not authenticated. Run: gh auth login"
}

$User = gh api user -q .login
if (-not $User) { Write-Error "Could not read GitHub login." }

$Base = "https://github.com/$User/$RepoName"
$Manifest = Join-Path $Root "custom_components\tarot_api\manifest.json"
$Text = Get-Content $Manifest -Raw
# manifest uses OWNER/REPO in both documentation and issue_tracker URLs
$Text = $Text -replace "OWNER/REPO", "$User/$RepoName"
Set-Content -Path $Manifest -Value $Text.TrimEnd("`r`n") -Encoding utf8

git add $Manifest
if (git diff --cached --quiet) {
    Write-Host "Manifest already points at $Base"
} else {
    git commit -m "Set manifest documentation and issue_tracker URLs"
}

$hasRemote = $false
$prevEap2 = $ErrorActionPreference
$ErrorActionPreference = "SilentlyContinue"
git remote get-url origin | Out-Null
if ($LASTEXITCODE -eq 0) { $hasRemote = $true }
$ErrorActionPreference = $prevEap2

if (-not $hasRemote) {
    gh repo create $RepoName --public --source=. --remote=origin --push --description "Home Assistant custom integration: draw tarot cards (tarotapi.dev + dashboard images)"
} else {
    git push -u origin main
}

Write-Host "Done: $Base"

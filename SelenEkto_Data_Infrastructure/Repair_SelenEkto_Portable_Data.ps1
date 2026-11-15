# SelenEkto portable build: connect the app to the developer's existing NASA datasets
# without duplicating multi-gigabyte GeoTIFFs. Run FROM SelenEkto_Data_Infrastructure.
$ErrorActionPreference = 'Stop'
$project = (Get-Location).Path
$app = Join-Path $project 'dist\SelenEkto'
$exe = Join-Path $app 'SelenEkto.exe'
$source = Join-Path $project 'data\raw\lola'
$target = Join-Path $app 'data\raw\lola'
$profiles = Join-Path $project 'data\catalog\region_profiles'
$targetProfiles = Join-Path $app 'data\catalog\region_profiles'
$devCandidates = Join-Path $project 'data\catalog\named_candidates.json'
$appCandidates = Join-Path $app 'data\catalog\named_candidates.json'

if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) { throw "Missing executable: $exe. Confirm the build's actual dist path first." }
if (-not (Test-Path -LiteralPath $source -PathType Container)) { throw "Missing development NASA dataset folder: $source" }
$sourceTiffs = @(Get-ChildItem -LiteralPath $source -Filter '*.tif' -Recurse -File -ErrorAction Stop)
if ($sourceTiffs.Count -eq 0) { throw "The development data folder has no TIFFs: $source" }

New-Item -ItemType Directory -Force -Path (Split-Path $target -Parent) | Out-Null
if (Test-Path -LiteralPath $target) {
    $existing = Get-Item -LiteralPath $target -Force
    if (($existing.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        Write-Host "Data folder is already a junction/link: $target" -ForegroundColor Yellow
    } else {
        $children = @(Get-ChildItem -LiteralPath $target -Force)
        if ($children.Count -gt 0) {
            throw "App's data folder is NOT empty. Refusing to replace it: $target. Check it manually."
        }
        Remove-Item -LiteralPath $target -Force
        New-Item -ItemType Junction -Path $target -Target $source | Out-Null
        Write-Host 'Created a folder junction (no TIFFs copied).' -ForegroundColor Green
    }
} else {
    New-Item -ItemType Junction -Path $target -Target $source | Out-Null
    Write-Host 'Created a folder junction (no TIFFs copied).' -ForegroundColor Green
}

if (Test-Path -LiteralPath $profiles -PathType Container) {
    New-Item -ItemType Directory -Force -Path $targetProfiles | Out-Null
    Copy-Item -Path (Join-Path $profiles '*.json') -Destination $targetProfiles -ErrorAction SilentlyContinue
    Copy-Item -Path (Join-Path $profiles '*.csv') -Destination $targetProfiles -ErrorAction SilentlyContinue
    Write-Host "Copied lightweight region summaries to $targetProfiles"
}
if ((Test-Path -LiteralPath $devCandidates -PathType Leaf) -and -not (Test-Path -LiteralPath $appCandidates)) {
    New-Item -ItemType Directory -Force -Path (Split-Path $appCandidates -Parent) | Out-Null
    Copy-Item -LiteralPath $devCandidates -Destination $appCandidates
    Write-Host 'Copied saved named candidates (original preserved).'
}

$appTiffs = @(Get-ChildItem -LiteralPath $target -Filter '*.tif' -Recurse -File)
$appProfiles = @(Get-ChildItem -LiteralPath $targetProfiles -Filter '*_terrain_profile.json' -File -ErrorAction SilentlyContinue)
Write-Host "TIFFs visible to app: $($appTiffs.Count)" -ForegroundColor Cyan
Write-Host "Region JSON profiles visible to app: $($appProfiles.Count)" -ForegroundColor Cyan
Write-Host "Launch by double-clicking: $exe" -ForegroundColor Cyan
Write-Host 'Note: this junction only works on this PC; a downloadable release needs on-demand data setup.' -ForegroundColor Yellow

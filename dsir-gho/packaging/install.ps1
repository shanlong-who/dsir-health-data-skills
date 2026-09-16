[CmdletBinding()]
param(
    [string]$SkillsRoot = [System.IO.Path]::Combine(
        [Environment]::GetFolderPath('UserProfile'), '.agents', 'skills'
    )
)

$ErrorActionPreference = 'Stop'
$sourcePath = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$skillsPath = [System.IO.Path]::GetFullPath($SkillsRoot)
$destinationPath = Join-Path $skillsPath 'dsir-gho'

if (-not (Test-Path -LiteralPath (Join-Path $sourcePath 'SKILL.md') -PathType Leaf)) {
    throw 'SKILL.md was not found beside the packaging folder. Extract the complete dsir-gho package first.'
}
if (-not (Test-Path -LiteralPath (Join-Path $sourcePath 'scripts/cli.py') -PathType Leaf)) {
    throw 'scripts/cli.py was not found. Extract the complete dsir-gho package first.'
}

$sourcePrefix = $sourcePath.TrimEnd([System.IO.Path]::DirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar
if ($destinationPath.Equals($sourcePath, [StringComparison]::OrdinalIgnoreCase) -or
    $destinationPath.StartsWith($sourcePrefix, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'The installation destination must be outside the source skill folder.'
}

if ($null -ne (Get-Item -LiteralPath $destinationPath -Force -ErrorAction SilentlyContinue)) {
    throw "Installation stopped: '$destinationPath' already exists. Review the existing copy before choosing an update method. No files were overwritten."
}

New-Item -ItemType Directory -Path $skillsPath -Force | Out-Null
# Create the destination exclusively so an existing skill is never replaced.
New-Item -ItemType Directory -Path $destinationPath -ErrorAction Stop | Out-Null
try {
    Get-ChildItem -LiteralPath $sourcePath -Force | Copy-Item -Destination $destinationPath -Recurse -ErrorAction Stop
} catch {
    throw "Installation did not complete. The destination was left for review at '$destinationPath'. $($_.Exception.Message)"
}

Write-Output "Installed DSIR GHO at $destinationPath"
Write-Output 'Start a new Codex task and use $dsir-gho. Restart Codex if the skill is not visible.'
Write-Output 'Python and network permissions were not changed. Run the doctor command before retrieval.'

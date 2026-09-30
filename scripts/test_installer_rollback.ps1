$ErrorActionPreference = 'Stop'
$version = & .venv/Scripts/python app_version.py
$installer = (Resolve-Path "release/Oxford-to-Notion-Setup-$version.exe").Path
$folder = Join-Path $env:TEMP ('oton-rollback-' + [guid]::NewGuid())
New-Item -ItemType Directory -Path $folder | Out-Null
$exe = Join-Path $folder 'Oxford to Notion.exe'
$icon = Join-Path $folder 'app-icon.ico'
# A locked icon forces failure after the executable has been backed up.
[IO.File]::WriteAllText($exe, 'old-executable-sentinel')
[IO.File]::WriteAllText($icon, 'old-icon-sentinel')
$lock = [IO.File]::Open($icon, 'Open', 'ReadWrite', 'None')
try {
    $process = Start-Process -FilePath $installer -ArgumentList @('/S', "/D=$folder") -PassThru -WindowStyle Hidden
    if (-not $process.WaitForExit(120000)) {
        $process.Kill()
        throw 'Installer rollback test timed out'
    }
    if ($process.ExitCode -eq 0) { throw 'Expected an installation failure' }
    if ([IO.File]::ReadAllText($exe) -ne 'old-executable-sentinel') { throw 'Old executable was not restored' }
    if (Test-Path ($exe + '.previous')) { throw 'Restored executable left an unexpected backup' }
} finally {
    $lock.Dispose()
}
if ([IO.File]::ReadAllText($icon) -ne 'old-icon-sentinel') { throw 'Old icon was modified' }
Write-Output 'Installer failure rollback verified'
# Keep only temporary test artifacts; never touches personal settings.

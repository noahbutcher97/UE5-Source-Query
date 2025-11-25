[CmdletBinding(SupportsShouldProcess = $true)]
param(
    # The primary root directory to scan for source files. Defaults to the project root (two levels up from this script).
    [string]$Root = $null,
    # A list of additional source directories to scan.
    [string[]]$SourceDirs = @(),
    # If specified, scans a predefined list of Unreal Engine source directories instead of the project root.
    [switch]$UseEngineDirs,
    # The path to the text file containing engine source directories, one per line.
    [string]$EngineDirsFile = 'EngineDirs.txt',
    # The directory where the 'index.json' file will be saved. Defaults to 'ai_index' inside this script's directory.
    [string]$OutputDir = $null,
    # A list of file extensions to include in the index (e.g., .cpp, .h). Defaults to common C++ and C# extensions.
    [string[]]$IncludeExtensions = @('.cpp', '.h', '.hpp', '.inl', 'cs'),
    # A list of directory names to exclude from the scan (e.g., Intermediate, Binaries).
    [string[]]$ExcludeDirs = @(),
    # The maximum file size in bytes to include in the index.
    [long]$MaxFileBytes = 10MB,
    # The number of lines to include as a preview in the index for each file.
    [int]$PreviewLines = 20,
    # If specified, overwrites the output directory if it already exists.
    [switch]$Force,
    # If specified, starts a simple HTTP server to serve the output directory.
    [switch]$ServeHttp,
    # The host address for the HTTP server.
    [string]$BindHost = '127.0.0.1',
    # The port for the HTTP server.
    [int]$Port = 8008,
    # If specified with -ServeHttp, runs the server in the background.
    [switch]$BackgroundServer
)

#region Setup
function Write-Info($Msg){ Write-Host "[INFO] $Msg" -ForegroundColor Cyan }
function Write-Warn($Msg){ Write-Warning $Msg }
function Write-Err($Msg){ Write-Host "[ERROR] $Msg" -ForegroundColor Red }
function Write-Verbose-Msg($Msg) { if ($PSBoundParameters['Verbose']) { Write-Verbose $Msg } }

# Permissions check for engine directories
if ($UseEngineDirs) {
    $currentUser = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    if (-not $currentUser.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        Write-Err "Scanning engine directories requires Administrator privileges."
        Write-Err "Please re-run this script from a terminal with 'Run as Administrator'."
        exit 1
    }
}

# Load engine source directories from file if specified
$EngineSourceDirs = @()
if ($UseEngineDirs) {
    $ResolvedEngineDirsFile = Join-Path $PSScriptRoot $EngineDirsFile
    if (-not (Test-Path $ResolvedEngineDirsFile)) {
        Write-Err "Engine dirs file not found: $ResolvedEngineDirsFile"
        exit 1
    } else {
        $EngineSourceDirs = Get-Content $ResolvedEngineDirsFile | ForEach-Object { $_.Trim() } | Where-Object { $_ -and -not $_.StartsWith('#') }
    }
}

# Default directories to exclude from scanning
$DefaultExcludePatterns = @(
    'Intermediate', 'Saved\Logs', '.git', '.vs', '.idea', 'Binaries', 'DerivedDataCache'
)
$AllExcludePatterns = $DefaultExcludePatterns + $ExcludeDirs

# Set sane defaults that can reference $PSScriptRoot
if (-not $Root) {
    try { $Root = (Resolve-Path "$PSScriptRoot\..\..").Path } catch { $Root = "$PSScriptRoot\..\.." }
}
if (-not $OutputDir) { $OutputDir = Join-Path $PSScriptRoot 'ai_index' }

# Prepare output directory
if (Test-Path $OutputDir) {
    if ($Force) { Remove-Item $OutputDir -Recurse -Force -ErrorAction SilentlyContinue }
}
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir | Out-Null
}
$OutputDirFull = (Resolve-Path $OutputDir).Path

# Determine roots to scan
$ScanRoots = @()
if ($UseEngineDirs) { $ScanRoots += $EngineSourceDirs }
if ($SourceDirs)    { $ScanRoots += $SourceDirs }
if (-not $ScanRoots -and $Root) { $ScanRoots = @($Root) }

# Validate & dedupe roots
$ValidRoots = @()
$Seen = @{}
foreach ($r in $ScanRoots) {
    if (-not (Test-Path $r)) {
        Write-Warn "Missing root, skipping: $r"
        continue
    }
    $Resolved = (Resolve-Path $r).Path
    if (-not $Seen.ContainsKey($Resolved.ToLower())) {
        $Seen[$Resolved.ToLower()] = $true
        $ValidRoots += $Resolved
    }
}
if (-not $ValidRoots) { Write-Err "No valid roots found to scan."; exit 1 }

# Normalize include extensions to lowercase with leading dot
$IncExtSet = @{}
foreach ($e in $IncludeExtensions) {
    $ext = $e.Trim()
    if ($ext -eq '') { continue }
    if (-not $ext.StartsWith('.')) { $ext = '.' + $ext }
    $IncExtSet[$ext.ToLower()] = $true
}
#endregion

#region Scan & Index
$Stopwatch = [System.Diagnostics.Stopwatch]::StartNew()

# Counters and buckets for analytics
$totalFilesScanned = 0
$byExt = @{}
$skippedOutput = New-Object System.Collections.Generic.List[string]
$skippedExclude = New-Object System.Collections.Generic.List[string]
$skippedSize = New-Object System.Collections.Generic.List[string]
$unreadable = New-Object System.Collections.Generic.List[string]
$candidatesPerRoot = @{}
$Index = New-Object System.Collections.ArrayList

Write-Info "Scanning and indexing roots:"
$ValidRoots | ForEach-Object { Write-Host "  $_"; $candidatesPerRoot[$_] = 0 }
Write-Host ""

$rootIndex = 0
foreach ($scanRoot in $ValidRoots) {
    $rootIndex++
    Try {
        $items = Get-ChildItem -Path $scanRoot -Recurse -File -ErrorAction SilentlyContinue
    } catch {
        Write-Warn "Failed to list files in '$scanRoot': $($_.Exception.Message)"
        continue
    }
    $count = if ($items) { $items.Count } else { 0 }
    $i = 0
    foreach ($it in $items) {
        $i++
        if ($count -gt 0) {
            $percent = [math]::Round(100 * $i / $count)
            $activity = "Scanning root $rootIndex/$($ValidRoots.Count): $scanRoot"
            Write-Progress -Activity $activity -Status "$percent% Complete" -PercentComplete $percent -CurrentOperation "Processing: $($it.Name)"
        }

        $totalFilesScanned++
        $ext = if ($it.Extension) { $it.Extension.ToLower() } else { '' }
        if (-not $byExt.ContainsKey($ext)) { $byExt[$ext] = 0 }
        $byExt[$ext]++

        $full = $it.FullName

        if ($full.StartsWith($OutputDirFull, [System.StringComparison]::OrdinalIgnoreCase)) {
            $skippedOutput.Add($full); Write-Verbose-Msg "Skipped (in output dir): $full"; continue
        }

        $isExcluded = $false
        foreach ($exPattern in $AllExcludePatterns) {
            if ($full -match ('\\' + [regex]::Escape($exPattern) + '\\')) {
                $isExcluded = $true
                break
            }
        }
        if ($isExcluded) { $skippedExclude.Add($full); Write-Verbose-Msg "Skipped (excluded dir): $full"; continue }

        if (-not $IncExtSet.ContainsKey($ext)) { continue }

        if ($it.Length -gt $MaxFileBytes) { $skippedSize.Add($full); Write-Verbose-Msg "Skipped (too large): $full"; continue }

        try {
            $contentPreview = (Get-Content -Path $full -TotalCount $PreviewLines -ErrorAction Stop) -join "`n"
            $FileRecord = [PSCustomObject]@{
                path         = $full.Substring($scanRoot.Length).TrimStart('\')
                fullPath     = $full
                bytes        = $it.Length
                extension    = $ext
                preview      = $contentPreview
            }
            $Index.Add($FileRecord) | Out-Null
            $candidatesPerRoot[$scanRoot]++
        }
        catch {
            $unreadable.Add($full); Write-Verbose-Msg "Skipped (unreadable): $full"
        }
    }
}
Write-Progress -Activity "Scanning roots" -Completed
$Stopwatch.Stop()
#endregion

#region Report & Write
$Summary = [PSCustomObject]@{
    roots        = $ValidRoots
    generatedUtc = (Get-Date).ToUniversalTime().ToString('o')
    fileCount    = $Index.Count
    previewLines = $PreviewLines
    totalBytes   = ($Index | Measure-Object -Property bytes -Sum).Sum
    extensions   = ($Index.extension | Group-Object | ForEach-Object { @{ ext = $_.Name; count = $_.Count } })
}
$Output = [PSCustomObject]@{
    summary = $Summary
    files   = $Index
}
$JsonPath = Join-Path $OutputDir 'index.json'
$Output | ConvertTo-Json -Depth 6 | Set-Content -Path $JsonPath -Encoding UTF8

Write-Info "Scan and index complete."
Write-Host "Total files scanned across all roots: $totalFilesScanned"
Write-Host "Indexed candidate files: $($Index.Count)"
if ($ValidRoots.Count -gt 1) {
    Write-Host "Indexed file counts per root:"
    $candidatesPerRoot.GetEnumerator() | Sort-Object Name | ForEach-Object {
        Write-Host ("  {0,8} {1}" -f $_.Value, $_.Name)
    }
}
Write-Host "Skipped file counts:"
Write-Host ("  {0,8} (in output dir)" -f $skippedOutput.Count)
Write-Host ("  {0,8} (in excluded dir)" -f $skippedExclude.Count)
Write-Host ("  {0,8} (too large)" -f $skippedSize.Count)
Write-Host ("  {0,8} (unreadable)" -f $unreadable.Count)
Write-Host ""
Write-Host "Counts by extension (all files scanned):"
$byExt.GetEnumerator() | Sort-Object Name | ForEach-Object {
    $key = if ([string]::IsNullOrEmpty($_.Key)) { '[none]' } else { $_.Key }
    Write-Host ("  {0,-10} {1}" -f $key, $_.Value)
}
Write-Host ""
Write-Info "Index written to: `"$JsonPath`""
Write-Info ("Elapsed: {0:N2}s" -f $Stopwatch.Elapsed.TotalSeconds)
Write-Host ""

# Add pause to view analytics before closing or serving
if (-not $ServeHttp) {
    Read-Host "Press Enter to exit"
}
#endregion

#region Serve
if ($ServeHttp) {
    $PortInUse = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($PortInUse) {
        Write-Warn "Port $Port is already in use. Cannot start HTTP server."
    } else {
        Write-Info "Serving '$OutputDirFull' at http://$BindHost`:$Port/"
        $EscapedOutputDir = $OutputDirFull.Replace("'", "''")
        $PyCode = @'
import http.server, socketserver, os
os.chdir(r"{0}")
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
    def end_headers(self):
        self.send_header("Cache-Control","no-store, max-age=0")
        self.send_header("Access-Control-Allow-Origin","*")
        super().end_headers()
def main():
    with socketserver.TCPServer(("{1}", {2}), Quiet) as httpd:
        print(f"Serving on http://{1}:{2}/ (Ctrl+C to stop)")
        try: httpd.serve_forever()
        except KeyboardInterrupt: pass
if __name__ == "__main__":
    main()
'@ -f $EscapedOutputDir, $BindHost, $Port

        $TempPy = [System.IO.Path]::GetTempFileName() + '.py'
        try {
            Set-Content -Path $TempPy -Value $PyCode -Encoding UTF8
            $pyCmd = Get-Command python -ErrorAction SilentlyContinue -pv pythonFound
            if (-not $pythonFound) { $pyCmd = Get-Command python3 -ErrorAction SilentlyContinue -pv python3Found }

            if (-not $pyCmd) {
                Write-Err "python/python3 not found in PATH. Cannot start HTTP server."
            } else {
                if ($BackgroundServer) {
                    $ps = [System.Diagnostics.ProcessStartInfo]::new($pyCmd.Source, "`"$TempPy`"")
                    $ps.CreateNoWindow = $true
                    $ps.WindowStyle = 'Hidden'
                    [System.Diagnostics.Process]::Start($ps) | Out-Null
                } else {
                    & $pyCmd $TempPy
                }
            }
        }
        finally {
            if (-not $BackgroundServer -and (Test-Path $TempPy)) {
                Remove-Item $TempPy -Force -ErrorAction SilentlyContinue
            }
        }
    }
}
#endregion

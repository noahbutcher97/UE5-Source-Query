# UE5 Source Query - System Provisioner
# Automates Python installation with User Choice

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path "$PSScriptRoot\.."
$RuntimeDir = "$ProjectRoot\.runtime\python"
$PyVersion = "3.11.9"

# Load Assemblies for GUI
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

function Write-Log {
    param([string]$Message)
    Write-Host "[PROVISION] $Message" -ForegroundColor Cyan
}

function Test-Command {
    param([string]$Name)
    return (Get-Command $Name -ErrorAction SilentlyContinue) -ne $null
}

# 1. Hardware Detection (GPU)
# ---------------------------
Write-Log "Checking hardware environment..."
$gpu = Get-CimInstance Win32_VideoController | Where-Object { $_.Name -like "*NVIDIA*" }

if ($gpu) {
    Write-Host "  [GPU] Detected: $($gpu.Name)" -ForegroundColor Green
    $env:UE5_QUERY_HAS_GPU = "1"
} else {
    Write-Host "  [GPU] No NVIDIA GPU detected (CPU mode)" -ForegroundColor Yellow
    $env:UE5_QUERY_HAS_GPU = "0"
}

# 2. Check System Python Status
# -----------------------------
$SystemPyFound = $false
$SystemVer = ""
if (Test-Command "python") {
    $verStr = python --version 2>&1
    if ($verStr -match "3.11") {
        $SystemPyFound = $true
        $SystemVer = $verStr
    }
}

# 3. User Choice Dialog
# ---------------------
$form = New-Object System.Windows.Forms.Form
$form.Text = "Python Setup - UE5 Source Query"
$form.Size = New-Object System.Drawing.Size(500, 380)
$form.StartPosition = "CenterScreen"
$form.FormBorderStyle = "FixedDialog"
$form.MaximizeBox = $false

$lbl = New-Object System.Windows.Forms.Label
$lbl.Location = New-Object System.Drawing.Point(20, 20)
$lbl.Size = New-Object System.Drawing.Size(450, 60)
if ($SystemPyFound) {
    $lbl.Text = "System Python ($SystemVer) was detected.`nHow would you like to set up the environment?"
} else {
    $lbl.Text = "Compatible Python ($PyVersion) was not found.`nHow would you like to install it?"
}
$lbl.Font = New-Object System.Drawing.Font("Segoe UI", 10, [System.Drawing.FontStyle]::Bold)
$form.Controls.Add($lbl)

# Option A: Private
$btnPrivate = New-Object System.Windows.Forms.Button
$btnPrivate.Location = New-Object System.Drawing.Point(20, 90)
$btnPrivate.Size = New-Object System.Drawing.Size(440, 70)
$btnPrivate.Text = "Portable / Private (Recommended)`nInstalls to project folder only. Keeps system clean."
$btnPrivate.Font = New-Object System.Drawing.Font("Segoe UI", 9)
$btnPrivate.DialogResult = [System.Windows.Forms.DialogResult]::Yes
$form.Controls.Add($btnPrivate)

# Option B: System
$btnSystem = New-Object System.Windows.Forms.Button
$btnSystem.Location = New-Object System.Drawing.Point(20, 170)
$btnSystem.Size = New-Object System.Drawing.Size(440, 70)
if ($SystemPyFound) {
    $btnSystem.Text = "Use System Python`nUses your existing installation ($SystemVer)."
} else {
    $btnSystem.Text = "Install System Python (User Scope)`nInstalls to AppData and adds to PATH."
}
$btnSystem.Font = New-Object System.Drawing.Font("Segoe UI", 9)
$btnSystem.DialogResult = [System.Windows.Forms.DialogResult]::No
$form.Controls.Add($btnSystem)

# Cancel
$btnCancel = New-Object System.Windows.Forms.Button
$btnCancel.Location = New-Object System.Drawing.Point(360, 290)
$btnCancel.Text = "Cancel"
$btnCancel.DialogResult = [System.Windows.Forms.DialogResult]::Cancel
$form.Controls.Add($btnCancel)

$result = $form.ShowDialog()

if ($result -eq [System.Windows.Forms.DialogResult]::Cancel) {
    exit 1
}

# 4. Installation Logic
# ---------------------
$installerUrl = "https://www.python.org/ftp/python/$PyVersion/python-$PyVersion-amd64.exe"
$installerPath = "$env:TEMP\python_installer.exe"

try {
    if ($result -eq [System.Windows.Forms.DialogResult]::Yes) {
        # === PRIVATE INSTALL ===
        # Check if already exists first
        $LocalPython = "$RuntimeDir\python.exe"
        if (Test-Path $LocalPython) {
            Write-Log "Private runtime already exists."
            $env:PYTHON_CMD_OVERRIDE = $LocalPython
            exit 0
        }

        Write-Log "Downloading Python $PyVersion..."
        Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath

        Write-Log "Unpacking Private Runtime to: $RuntimeDir"
        $args = "/passive", "TargetDir=$RuntimeDir", "InstallAllUsers=0", "PrependPath=0", "Include_test=0", "Include_doc=0", "Include_tcltk=1", "Include_pip=1"
        
        $process = Start-Process -FilePath $installerPath -ArgumentList $args -Wait -PassThru
        
        if ($process.ExitCode -eq 0 -and (Test-Path $LocalPython)) {
            Write-Log "Private runtime ready!"
            $env:PYTHON_CMD_OVERRIDE = $LocalPython
        } else { throw "Private install failed." }

    } else {
        # === SYSTEM INSTALL (OR USE EXISTING) ===
        if ($SystemPyFound) {
            Write-Log "Using existing System Python."
            exit 0
        }

        Write-Log "Downloading Python $PyVersion..."
        Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath

        Write-Log "Installing to User Profile (PATH enabled)..."
        $args = "/passive", "InstallAllUsers=0", "PrependPath=1", "Include_test=0", "Include_doc=0", "Include_tcltk=1", "Include_pip=1"
        
        $process = Start-Process -FilePath $installerPath -ArgumentList $args -Wait -PassThru
        
        if ($process.ExitCode -eq 0) {
            Write-Log "System install successful!"
            
            # Refresh PATH
            $userPath = [Environment]::GetEnvironmentVariable("Path", [EnvironmentVariableTarget]::User)
            $env:Path = "$userPath;$env:Path"
            
            # Find python
            if (Test-Command "python") {
                exit 0
            } else {
                # Fallback check
                $localPy = "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"
                if (Test-Path $localPy) {
                    $env:PYTHON_CMD_OVERRIDE = $localPy
                } else { throw "Python installed but not found." }
            }
        } else { throw "System install failed." }
    }
}
catch {
    Write-Error "Provisioning failed: $_"
    exit 1
}
finally {
    if (Test-Path $installerPath) { Remove-Item $installerPath }
}
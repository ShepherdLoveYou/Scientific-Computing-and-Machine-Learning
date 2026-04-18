# SCML local development environment bootstrap (Windows PowerShell).
# Creates a conda env at D:\Conda\envs\scml per the project convention.
#
# Usage:
#   ./scripts/setup-env.ps1           # create env and verify
#   ./scripts/setup-env.ps1 -Force    # remove any existing env first

param([switch]$Force)

$ErrorActionPreference = "Stop"
$EnvPath = "D:\Conda\envs\scml"

if (-not (Get-Command conda -ErrorAction SilentlyContinue)) {
    Write-Error "conda not found on PATH. Install Miniconda/Mambaforge first."
    exit 1
}

if ($Force -and (Test-Path $EnvPath)) {
    Write-Host "Removing existing env at $EnvPath ..."
    conda env remove -p $EnvPath -y
}

if (Test-Path $EnvPath) {
    Write-Host "Env already exists at $EnvPath. Use -Force to recreate."
} else {
    Write-Host "Step 1/2: conda env create (5-10 minutes) ..."
    conda env create -p $EnvPath -f "$PSScriptRoot\..\environment.yml"

    Write-Host ""
    Write-Host "Step 2/2: pip install torch / keras / progress via PyTorch CPU index ..."
    # Running via the env's own python.exe avoids the base-env Python 3.13
    # stdlib leakage that breaks `conda env create`'s internal pip subprocess.
    & "$EnvPath\python.exe" -m pip install `
        --index-url https://download.pytorch.org/whl/cpu `
        --extra-index-url https://pypi.org/simple `
        "torch>=2.4,<3" torchvision "keras>=3.5,<4" "progress>=1.6"
}

Write-Host ""
Write-Host "Activate with:  conda activate $EnvPath"
Write-Host "Set backend:    `$env:KERAS_BACKEND = 'torch'"
Write-Host "Verify with:    python scripts/verify-env.py"

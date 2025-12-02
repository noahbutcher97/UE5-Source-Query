"""
UE5 Source Query Tool - GPU Detection and CUDA Management
Detects NVIDIA GPU capabilities and manages CUDA installation.
"""

import subprocess
import re
from pathlib import Path
from typing import Optional, Dict, List
import platform

class GPUInfo:
    """Container for GPU information"""
    def __init__(self, name: str, compute_capability: tuple, cuda_version_required: str):
        self.name = name
        self.compute_capability = compute_capability  # (major, minor) e.g., (12, 0) for SM 120
        self.cuda_version_required = cuda_version_required

    @property
    def sm_version(self) -> str:
        """Returns SM version as string like 'sm_120'"""
        major, minor = self.compute_capability
        return f"sm_{major}{minor}"

    @property
    def compute_capability_str(self) -> str:
        """Returns compute capability as string like '12.0'"""
        major, minor = self.compute_capability
        return f"{major}.{minor}"

# NVIDIA GPU Compute Capability to CUDA version mapping
# Based on https://developer.nvidia.com/cuda-gpus
SM_TO_CUDA = {
    # Latest generation (Ada Lovelace / Hopper / Blackwell)
    (12, 0): "12.8",  # RTX 50 series (Blackwell) - SM 120 requires CUDA 12.8+
    (9, 0): "12.0",   # H100 (Hopper) - SM 90
    (8, 9): "11.8",   # RTX 40 series (Ada Lovelace) - SM 89
    (8, 6): "11.1",   # RTX 30 series (Ampere) - SM 86
    (8, 0): "11.0",   # A100 (Ampere) - SM 80
    (7, 5): "10.0",   # RTX 20 series, GTX 16 series (Turing) - SM 75
    (7, 0): "9.0",    # Titan V, V100 (Volta) - SM 70
    (6, 1): "8.0",    # GTX 10 series (Pascal) - SM 61
    (6, 0): "8.0",    # P100 (Pascal) - SM 60
    (5, 2): "8.0",    # GTX 900 series (Maxwell) - SM 52
    (5, 0): "8.0",    # GTX 750 series (Maxwell) - SM 50
    (3, 7): "8.0",    # K80 (Kepler) - SM 37
    (3, 5): "8.0",    # K40 (Kepler) - SM 35
}

def get_cuda_version_for_sm(major: int, minor: int) -> str:
    """Get minimum CUDA version required for given compute capability"""
    key = (major, minor)
    if key in SM_TO_CUDA:
        return SM_TO_CUDA[key]

    # If exact match not found, find closest lower version
    for (sm_major, sm_minor), cuda_ver in sorted(SM_TO_CUDA.items(), reverse=True):
        if major > sm_major or (major == sm_major and minor >= sm_minor):
            return cuda_ver

    return "12.8"  # Default to latest

def detect_nvidia_gpu() -> Optional[GPUInfo]:
    """
    Detect NVIDIA GPU using nvidia-smi.
    Returns GPUInfo if NVIDIA GPU found, None otherwise.
    """
    try:
        # Run nvidia-smi to get GPU info
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,compute_cap", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            return None

        output = result.stdout.strip()
        if not output:
            return None

        # Parse output: "GPU Name, compute_capability"
        # Example: "NVIDIA GeForce RTX 5090, 12.0"
        lines = output.split('\n')
        if not lines:
            return None

        # Take first GPU
        parts = lines[0].split(',')
        if len(parts) < 2:
            return None

        gpu_name = parts[0].strip()
        compute_cap = parts[1].strip()

        # Parse compute capability
        match = re.match(r'(\d+)\.(\d+)', compute_cap)
        if not match:
            return None

        major = int(match.group(1))
        minor = int(match.group(2))

        cuda_version = get_cuda_version_for_sm(major, minor)

        return GPUInfo(gpu_name, (major, minor), cuda_version)

    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        return None

def check_cuda_installed() -> Optional[str]:
    """
    Check if CUDA is installed and return version.
    Returns version string like "12.8" or None if not found.
    """
    try:
        # Try nvcc --version
        result = subprocess.run(
            ["nvcc", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            # Parse version from output
            # Example: "Cuda compilation tools, release 12.8, V12.8.89"
            match = re.search(r'release (\d+\.\d+)', result.stdout)
            if match:
                return match.group(1)

        # Try reading from registry on Windows
        if platform.system() == "Windows":
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\NVIDIA Corporation\GPU Computing Toolkit\CUDA")
                num_subkeys = winreg.QueryInfoKey(key)[0]

                versions = []
                for i in range(num_subkeys):
                    subkey_name = winreg.EnumKey(key, i)
                    # Subkey names are like "v12.8"
                    match = re.match(r'v(\d+\.\d+)', subkey_name)
                    if match:
                        versions.append(match.group(1))

                winreg.CloseKey(key)

                if versions:
                    # Return latest version
                    versions.sort(key=lambda x: [int(p) for p in x.split('.')], reverse=True)
                    return versions[0]
            except:
                pass

    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        pass

    return None

def get_cuda_download_url(version: str) -> str:
    """
    Get CUDA Toolkit download URL for specific version.
    Returns URL for Windows installer.
    """
    # CUDA Toolkit download URLs (Windows)
    cuda_urls = {
        "12.8": "https://developer.download.nvidia.com/compute/cuda/12.8.0/network_installers/cuda_12.8.0_windows_network.exe",
        "12.7": "https://developer.download.nvidia.com/compute/cuda/12.7.0/network_installers/cuda_12.7.0_windows_network.exe",
        "12.6": "https://developer.download.nvidia.com/compute/cuda/12.6.0/network_installers/cuda_12.6.0_windows_network.exe",
        "12.0": "https://developer.download.nvidia.com/compute/cuda/12.0.0/network_installers/cuda_12.0.0_windows_network.exe",
        "11.8": "https://developer.download.nvidia.com/compute/cuda/11.8.0/network_installers/cuda_11.8.0_windows_network.exe",
    }

    return cuda_urls.get(version, cuda_urls["12.8"])

def get_gpu_summary() -> Dict[str, any]:
    """
    Get comprehensive GPU summary for diagnostics.
    Returns dict with all GPU information.
    """
    gpu_info = detect_nvidia_gpu()
    cuda_installed = check_cuda_installed()

    # PyTorch 2.6.0 maximum supported compute capability
    # SM 90 = Hopper (H100), SM 120 = Blackwell (RTX 5090) NOT YET SUPPORTED
    PYTORCH_MAX_SM = (9, 0)  # Update when PyTorch adds SM 120 support

    summary = {
        "has_nvidia_gpu": gpu_info is not None,
        "gpu_name": gpu_info.name if gpu_info else None,
        "compute_capability": gpu_info.compute_capability_str if gpu_info else None,
        "sm_version": gpu_info.sm_version if gpu_info else None,
        "cuda_required": gpu_info.cuda_version_required if gpu_info else None,
        "cuda_installed": cuda_installed,
        "cuda_compatible": False,
        "pytorch_compatible": False,
        "needs_cuda_install": False,
        "download_url": None,
        "warning": None
    }

    # Check PyTorch compatibility
    if gpu_info:
        gpu_sm = gpu_info.compute_capability
        if gpu_sm[0] < PYTORCH_MAX_SM[0] or \
           (gpu_sm[0] == PYTORCH_MAX_SM[0] and gpu_sm[1] <= PYTORCH_MAX_SM[1]):
            summary["pytorch_compatible"] = True
        else:
            summary["pytorch_compatible"] = False
            summary["warning"] = f"GPU compute capability SM {gpu_sm[0]}.{gpu_sm[1]} exceeds PyTorch 2.6.0 support (max SM {PYTORCH_MAX_SM[0]}.{PYTORCH_MAX_SM[1]}). GPU acceleration will not work. Recommend CPU-only installation until PyTorch adds support."

    if gpu_info and cuda_installed:
        # Check if installed CUDA version is sufficient
        required_parts = [int(x) for x in gpu_info.cuda_version_required.split('.')]
        installed_parts = [int(x) for x in cuda_installed.split('.')]

        # Compare major.minor
        if installed_parts[0] > required_parts[0] or \
           (installed_parts[0] == required_parts[0] and installed_parts[1] >= required_parts[1]):
            summary["cuda_compatible"] = True
        else:
            summary["needs_cuda_install"] = True
            summary["download_url"] = get_cuda_download_url(gpu_info.cuda_version_required)
    elif gpu_info:
        summary["needs_cuda_install"] = True
        summary["download_url"] = get_cuda_download_url(gpu_info.cuda_version_required)

    return summary

def get_gpu_requirements_text() -> str:
    """Generate human-readable GPU requirements text"""
    gpu_info = detect_nvidia_gpu()

    if not gpu_info:
        return "No NVIDIA GPU detected. GPU acceleration will be disabled."

    gpu_summary = get_gpu_summary()
    cuda_installed = check_cuda_installed()

    text = f"GPU Detected: {gpu_info.name}\n"
    text += f"Compute Capability: {gpu_info.compute_capability_str} ({gpu_info.sm_version})\n"
    text += f"CUDA Required: {gpu_info.cuda_version_required}+\n"

    # Check PyTorch compatibility first
    if not gpu_summary["pytorch_compatible"]:
        text += f"\n[WARNING] {gpu_summary['warning']}\n"
        text += "\nRecommendation: Use CPU-only installation for now.\n"
        text += "GPU support will be available when PyTorch adds SM 120 support.\n"
        return text

    if cuda_installed:
        text += f"CUDA Installed: {cuda_installed}\n"

        required_parts = [int(x) for x in gpu_info.cuda_version_required.split('.')]
        installed_parts = [int(x) for x in cuda_installed.split('.')]

        if installed_parts[0] > required_parts[0] or \
           (installed_parts[0] == required_parts[0] and installed_parts[1] >= required_parts[1]):
            text += "[OK] CUDA version is compatible!"
        else:
            text += f"[ERROR] CUDA version too old. Please install CUDA {gpu_info.cuda_version_required}+"
    else:
        text += "[ERROR] CUDA not installed\n"
        text += f"Please install CUDA {gpu_info.cuda_version_required} or later"

    return text

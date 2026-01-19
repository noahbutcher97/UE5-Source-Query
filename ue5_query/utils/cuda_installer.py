"""
UE5 Source Query Tool - CUDA Toolkit Installer
Downloads and installs CUDA Toolkit for GPU acceleration.
"""

import subprocess
import urllib.request
import tempfile
from pathlib import Path
from typing import Callable, Optional
import os

def download_cuda(url: str, progress_callback: Optional[Callable[[int, int], None]] = None) -> Path:
    """
    Download CUDA installer from URL.

    Args:
        url: URL to download from
        progress_callback: Optional callback(bytes_downloaded, total_bytes)

    Returns:
        Path to downloaded installer
    """
    temp_dir = Path(tempfile.gettempdir())
    installer_path = temp_dir / "cuda_installer.exe"

    def report_hook(block_num, block_size, total_size):
        if progress_callback:
            downloaded = block_num * block_size
            progress_callback(downloaded, total_size)

    urllib.request.urlretrieve(url, str(installer_path), reporthook=report_hook)

    return installer_path

def install_cuda(installer_path: Path, silent: bool = True) -> bool:
    """
    Install CUDA Toolkit with administrator privileges.

    Args:
        installer_path: Path to CUDA installer executable
        silent: If True, perform silent installation

    Returns:
        True if installation successful, False otherwise
    """
    try:
        import ctypes

        # Check if we're running as admin
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0

        if not is_admin:
            # Try to elevate and run installer
            args = f'"{installer_path}"'
            if silent:
                args += " -s"

            # ShellExecute with 'runas' to request elevation
            result = ctypes.windll.shell32.ShellExecuteW(
                None,
                "runas",
                str(installer_path),
                "-s" if silent else "",
                None,
                1  # SW_SHOWNORMAL
            )

            # ShellExecute returns > 32 on success
            return result > 32
        else:
            # Already admin, run directly
            args = [str(installer_path)]
            if silent:
                args.extend(["-s"])

            result = subprocess.run(
                args,
                capture_output=True,
                text=True
            )

            return result.returncode == 0

    except Exception as e:
        print(f"CUDA installation failed: {e}")
        return False

def install_cuda_with_progress(
    url: str,
    download_callback: Optional[Callable[[int, int], None]] = None,
    install_callback: Optional[Callable[[str], None]] = None
) -> bool:
    """
    Download and install CUDA with progress callbacks.

    Args:
        url: CUDA installer download URL
        download_callback: Callback for download progress(bytes_downloaded, total_bytes)
        install_callback: Callback for install status messages

    Returns:
        True if successful, False otherwise
    """
    try:
        # Download
        if install_callback:
            install_callback("Downloading CUDA Toolkit...")

        installer_path = download_cuda(url, download_callback)

        if install_callback:
            install_callback("Download complete. Starting installation...")

        # Install
        success = install_cuda(installer_path, silent=True)

        # Cleanup
        try:
            installer_path.unlink()
        except:
            pass

        if success:
            if install_callback:
                install_callback("CUDA installation complete!")
        else:
            if install_callback:
                install_callback("CUDA installation failed.")

        return success

    except Exception as e:
        if install_callback:
            install_callback(f"Error: {str(e)}")
        return False

def get_gpu_requirements_file_content(cuda_version: str) -> str:
    """
    Generate requirements-gpu.txt content based on CUDA version.

    Returns content for requirements file with GPU-accelerated packages.
    """
    import platform

    # Map CUDA version to compatible PyTorch CUDA version
    cuda_major_minor = '.'.join(cuda_version.split('.')[:2])

    # PyTorch uses cu118, cu121, cu124, cu128 naming
    # cu128 supports RTX 5090 (SM 12.0) natively for optimal performance
    if cuda_major_minor >= "12.6":
        torch_cuda = "cu128"
    elif cuda_major_minor >= "12.4":
        torch_cuda = "cu124"
    elif cuda_major_minor >= "12.1":
        torch_cuda = "cu121"
    elif cuda_major_minor >= "11.8":
        torch_cuda = "cu118"
    else:
        torch_cuda = "cu118"  # fallback

    # FAISS-GPU on Windows is problematic, use CPU version with GPU PyTorch
    # The embeddings will still use GPU via PyTorch
    faiss_package = "faiss-cpu==1.9.0"

    # For Linux, we can use faiss-gpu
    if platform.system() == "Linux":
        faiss_package = "faiss-gpu==1.9.0"

    return f"""# GPU-accelerated packages for CUDA {cuda_version}
# PyTorch with CUDA support (this enables GPU for embeddings)
# NOTE: Using 2.9.1+ for native RTX 5090 (SM 12.0) support and security fixes
torch==2.9.1+{torch_cuda}
torchvision==0.24.1+{torch_cuda}
--extra-index-url https://download.pytorch.org/whl/{torch_cuda}

# GPU-accelerated transformers (uses PyTorch GPU)
sentence-transformers==3.3.1

# FAISS for vector similarity search
# Note: Using CPU version on Windows (PyTorch still uses GPU for embeddings)
{faiss_package}

# Optional: cupy for GPU-accelerated numpy operations
# cupy-cuda12x==13.3.0
"""

def create_gpu_requirements_file(output_path: Path, cuda_version: str) -> None:
    """
    Create requirements-gpu.txt file for GPU-accelerated packages.

    Args:
        output_path: Path where to write requirements-gpu.txt
        cuda_version: CUDA version string (e.g., "12.8")
    """
    content = get_gpu_requirements_file_content(cuda_version)
    output_path.write_text(content)

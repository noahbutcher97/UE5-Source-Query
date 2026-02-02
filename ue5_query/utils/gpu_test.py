import sys
import time
import json
import traceback
from pathlib import Path

def run_diagnostic():
    result = {
        "status": "fail",
        "torch_available": False,
        "cuda_available": False,
        "system_cuda": "Not Detected",
        "device_name": "Unknown",
        "capability": None,
        "vram_gb": 0,
        "test_duration": 0,
        "jit_status": "unknown",
        "error": None,
        "recommendation": ""
    }

    try:
        # Check System CUDA (nvcc)
        import subprocess
        try:
            nvcc_res = subprocess.run(["nvcc", "--version"], capture_output=True, text=True, timeout=2)
            if nvcc_res.returncode == 0:
                import re
                match = re.search(r'release (\d+\.\d+)', nvcc_res.stdout)
                if match:
                    result["system_cuda"] = f"Installed (v{match.group(1)})"
                else:
                    result["system_cuda"] = "Installed (Unknown Version)"
        except FileNotFoundError:
            pass # nvcc not in PATH

        import torch
        result["torch_available"] = True
        result["torch_version"] = torch.__version__
        
        if torch.cuda.is_available():
            result["cuda_available"] = True
            result["device_name"] = torch.cuda.get_device_name(0)
            
            # Get VRAM
            props = torch.cuda.get_device_properties(0)
            result["vram_gb"] = round(props.total_memory / (1024**3), 1)
            
            # Get Compute Capability
            cap = torch.cuda.get_device_capability(0)
            result["capability"] = f"{cap[0]}.{cap[1]}"
            
            # --- Performance & JIT Test ---
            t0 = time.time()
            
            # 1. Allocate Tensor (Memory Check)
            x = torch.randn(4096, 4096, device='cuda')
            y = torch.randn(4096, 4096, device='cuda')
            
            # 2. Compute (Core Check)
            # This triggers JIT compilation on unsupported architectures
            torch.matmul(x, y)
            torch.cuda.synchronize()
            
            result["test_duration"] = time.time() - t0
            result["status"] = "pass"
            
            # Analyze JIT need
            # PyTorch 2.9/2.6 usually supports up to SM 9.0/10.0 natively.
            # SM 12.0 (RTX 5090) usually triggers JIT.
            if cap[0] >= 12:
                result["jit_status"] = "active"
                result["recommendation"] = (
                    "Your GPU architecture (Blackwell/SM 12.0) is newer than the bundled PyTorch binary. "
                    "It is working correctly via JIT compilation (Driver-based compatibility). "
                    "Installing the System CUDA Toolkit is NOT required unless you experience long startup times."
                )
            else:
                result["jit_status"] = "native"
                result["recommendation"] = (
                    "Your GPU is natively supported by the local PyTorch runtime. "
                    "You do NOT need to install the System CUDA Toolkit."
                )
                
        else:
            result["error"] = "PyTorch could not detect a GPU. Drivers may be missing or outdated."
            result["recommendation"] = "Please install the NVIDIA Drivers and CUDA Toolkit using the 'Setup CUDA' button."

    except ImportError:
        result["error"] = "PyTorch not installed in this environment."
    except Exception as e:
        result["error"] = str(e)
        result["details"] = traceback.format_exc()
        result["recommendation"] = "An error occurred during GPU testing. Installing System CUDA might fix this."

    # Print JSON to stdout for capture
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    run_diagnostic()

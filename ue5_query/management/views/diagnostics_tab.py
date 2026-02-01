import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import sys
import subprocess
import threading
from pathlib import Path

# Try to import Theme, handle missing imports gracefully
try:
    from ue5_query.utils.gui_theme import Theme
    from ue5_query.utils.gpu_helper import detect_nvidia_gpu, get_gpu_summary
except ImportError:
    # If run standalone
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
        from ue5_query.utils.gui_theme import Theme
        from ue5_query.utils.gpu_helper import detect_nvidia_gpu, get_gpu_summary
    except ImportError:
        Theme = None

class DiagnosticsTab:
    """
    Handles the Diagnostics tab logic and layout.
    """
    def __init__(self, parent_frame, dashboard):
        """
        Args:
            parent_frame: The ttk.Frame to build the tab into
            dashboard: Reference to the main UnifiedDashboard instance (controller)
        """
        self.frame = parent_frame
        self.dashboard = dashboard
        self.script_dir = dashboard.script_dir
        self.root = dashboard.root

        self.build_ui()

    def build_ui(self):
        """Build enhanced Diagnostics tab with comprehensive testing options"""
        frame = ttk.Frame(self.frame, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        # Test Options Section
        options_frame = ttk.LabelFrame(frame, text=" Test Suite Options ", padding=15)
        options_frame.pack(fill=tk.X, pady=(0, 15))

        # Grid layout for test buttons
        test_grid = tk.Frame(options_frame, bg=Theme.BG_LIGHT)
        test_grid.pack(fill=tk.X)

        # Row 1: Basic Health Checks
        row1_label = tk.Label(
            test_grid,
            text="Basic Health:",
            font=("Arial", 10, "bold"),
            bg=Theme.BG_LIGHT,
            fg=Theme.TEXT_DARK,
            width=15,
            anchor=tk.W
        )
        row1_label.grid(row=0, column=0, sticky=tk.W, padx=(0, 10), pady=5)

        btn_health = tk.Button(
            test_grid,
            text="System Health",
            command=self.run_health_check,
            bg=Theme.SUCCESS,
            fg="white",
            padx=10,
            pady=5,
            relief=tk.FLAT,
            cursor="hand2"
        )
        btn_health.grid(row=0, column=1, padx=5, pady=5)

        btn_vector = tk.Button(
            test_grid,
            text="Vector Store Validation",
            command=self.run_vector_validation,
            bg=Theme.SUCCESS,
            fg="white",
            padx=10,
            pady=5,
            relief=tk.FLAT,
            cursor="hand2"
        )
        btn_vector.grid(row=0, column=2, padx=5, pady=5)

        # Row 2: Unit Tests
        row2_label = tk.Label(
            test_grid,
            text="Unit Tests:",
            font=("Arial", 10, "bold"),
            bg=Theme.BG_LIGHT,
            fg=Theme.TEXT_DARK,
            width=15,
            anchor=tk.W
        )
        row2_label.grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=5)

        btn_deployment = tk.Button(
            test_grid,
            text="Deployment Detection",
            command=lambda: self.run_test_suite("deployment"),
            bg=Theme.SECONDARY,
            fg="white",
            padx=10,
            pady=5,
            relief=tk.FLAT,
            cursor="hand2"
        )
        btn_deployment.grid(row=1, column=1, padx=5, pady=5)

        btn_update = tk.Button(
            test_grid,
            text="Update Integration",
            command=lambda: self.run_test_suite("update"),
            bg=Theme.SECONDARY,
            fg="white",
            padx=10,
            pady=5,
            relief=tk.FLAT,
            cursor="hand2"
        )
        btn_update.grid(row=1, column=2, padx=5, pady=5)

        # Row 3: Smoke Tests
        row3_label = tk.Label(
            test_grid,
            text="Smoke Tests:",
            font=("Arial", 10, "bold"),
            bg=Theme.BG_LIGHT,
            fg=Theme.TEXT_DARK,
            width=15,
            anchor=tk.W
        )
        row3_label.grid(row=2, column=0, sticky=tk.W, padx=(0, 10), pady=5)

        btn_gui_smoke = tk.Button(
            test_grid,
            text="GUI Launch",
            command=self.run_gui_smoke_test,
            bg=Theme.WARNING,
            fg="white",
            padx=10,
            pady=5,
            relief=tk.FLAT,
            cursor="hand2"
        )
        btn_gui_smoke.grid(row=2, column=1, padx=5, pady=5)

        btn_import_smoke = tk.Button(
            test_grid,
            text="Module Imports",
            command=self.run_import_smoke_test,
            bg=Theme.WARNING,
            fg="white",
            padx=10,
            pady=5,
            relief=tk.FLAT,
            cursor="hand2"
        )
        btn_import_smoke.grid(row=2, column=2, padx=5, pady=5)

        # Row 4: Full Test Suite
        row4_label = tk.Label(
            test_grid,
            text="Full Suite:",
            font=("Arial", 10, "bold"),
            bg=Theme.BG_LIGHT,
            fg=Theme.TEXT_DARK,
            width=15,
            anchor=tk.W
        )
        row4_label.grid(row=3, column=0, sticky=tk.W, padx=(0, 10), pady=5)

        btn_all_tests = tk.Button(
            test_grid,
            text="Run All Tests",
            command=lambda: self.run_test_suite("all"),
            bg=Theme.ERROR,
            fg="white",
            padx=15,
            pady=5,
            relief=tk.FLAT,
            cursor="hand2",
            font=("Arial", 10, "bold")
        )
        btn_all_tests.grid(row=3, column=1, columnspan=2, padx=5, pady=5, sticky=tk.EW)

        # Output Area
        output_frame = ttk.LabelFrame(frame, text=" Test Output ", padding=10)
        output_frame.pack(fill=tk.BOTH, expand=True)

        self.diag_log = scrolledtext.ScrolledText(
            output_frame,
            font=("Consolas", 9),
            bg="#1E1E1E",
            fg="#D4D4D4",
            state=tk.DISABLED
        )
        self.diag_log.pack(fill=tk.BOTH, expand=True)

        # Initial instruction
        self.log_diag("Test suite ready. Select a test category to run.\n")
        self.log_diag("\nTest Categories:\n")
        self.log_diag("  • Basic Health - Quick system validation\n")
        self.log_diag("  • Unit Tests - Component-level testing\n")
        self.log_diag("  • Smoke Tests - Fast integration checks\n")
        self.log_diag("  • Full Suite - Comprehensive testing (may take several minutes)\n")

    def run_health_check(self):
        """Run basic system health check"""
        self.log_diag("Running system health check...", clear=True)

        def _run():
            # First, check GPU
            try:
                self.root.after(0, lambda: self.log_diag("=== GPU Status ===", append=True))
                gpu_info = detect_nvidia_gpu()
                if gpu_info:
                    gpu_summary = get_gpu_summary()
                    self.root.after(0, lambda: self.log_diag(f"GPU: {gpu_info.name}", append=True))
                    self.root.after(0, lambda: self.log_diag(f"Compute Capability: {gpu_info.compute_capability_str} ({gpu_info.sm_version})", append=True))
                    self.root.after(0, lambda: self.log_diag(f"CUDA Required: {gpu_info.cuda_version_required}+", append=True))

                    if gpu_summary["cuda_installed"]:
                        self.root.after(0, lambda: self.log_diag(f"CUDA Installed: {gpu_summary['cuda_installed']}", append=True))
                        if gpu_summary["cuda_compatible"]:
                            self.root.after(0, lambda: self.log_diag("✓ CUDA version compatible for GPU acceleration", append=True))
                        else:
                            self.root.after(0, lambda: self.log_diag(f"✗ CUDA {gpu_info.cuda_version_required}+ required for full GPU support", append=True))
                    else:
                        self.root.after(0, lambda: self.log_diag("✗ CUDA not installed - GPU acceleration unavailable", append=True))
                else:
                    self.root.after(0, lambda: self.log_diag("No NVIDIA GPU detected - CPU mode only", append=True))

                self.root.after(0, lambda: self.log_diag("\n=== System Health Check ===", append=True))
            except Exception as e:
                self.root.after(0, lambda: self.log_diag(f"GPU check error: {e}\n", append=True))

            # Then run the standard health check
            script = self.script_dir / "tools" / "health-check.bat"
            try:
                process = subprocess.Popen(
                    [str(script), "--verbose"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    cwd=str(self.script_dir)
                )

                for line in process.stdout:
                    self.root.after(0, lambda l=line: self.log_diag(l.rstrip(), append=True))

                process.wait()

                if process.returncode == 0:
                    self.root.after(0, lambda: self.log_diag("\n[SUCCESS] System is healthy.", append=True))
                else:
                    self.root.after(0, lambda: self.log_diag("\n[WARNING] Issues detected.", append=True))

            except Exception as e:
                self.root.after(0, lambda err=str(e): self.log_diag(f"\nError running script: {err}", append=True))

        threading.Thread(target=_run, daemon=True).start()

    def log_diag(self, message, clear=False, append=False):
        self.diag_log.config(state=tk.NORMAL)
        if clear:
            self.diag_log.delete(1.0, tk.END)
        self.diag_log.insert(tk.END, message + ("\n" if not message.endswith("\n") else ""))
        self.diag_log.see(tk.END)
        self.diag_log.config(state=tk.DISABLED)

    def run_vector_validation(self):
        """Run vector store validation"""
        # Run check
        # Use -m module execution to avoid path issues
        cmd = [sys.executable, "-m", "ue5_query.utils.verify_vector_store"]
        
        self.log_diag(f"Running: {' '.join(cmd)}", clear=True)
        
        def run():
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    cwd=str(self.script_dir)
                )
                
                output = result.stdout + result.stderr
                self.dashboard.root.after(0, lambda: self.log_diag(output, append=True))
                
                if result.returncode == 0:
                    self.dashboard.root.after(0, lambda: messagebox.showinfo("Validation", "Vector store is valid!"))
                else:
                    self.dashboard.root.after(0, lambda: messagebox.showwarning("Validation", "Issues detected. See output log."))
                    
            except Exception as e:
                self.dashboard.root.after(0, lambda: self.log_diag(f"Error: {e}", append=True))

        threading.Thread(target=run, daemon=True).start()

    def run_test_suite(self, suite_name):
        """Run specific test suite"""
        self.log_diag(f"Running {suite_name} test suite...", clear=True)

        def _run():
            test_file_map = {
                "deployment": "tests/test_deployment_detection.py",
                "update": "tests/test_update_integration.py",
                "all": "tests/run_tests.py"
            }

            test_file = self.script_dir / test_file_map.get(suite_name, "tests/run_tests.py")

            if not test_file.exists():
                self.root.after(0, lambda: self.log_diag(f"\n[ERROR] Test file not found: {test_file}", append=True))
                return

            try:
                self.root.after(0, lambda: self.log_diag(f"Test file: {test_file}\n", append=True))

                process = subprocess.Popen(
                    [sys.executable, str(test_file)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    cwd=str(self.script_dir)
                )

                for line in process.stdout:
                    self.root.after(0, lambda l=line: self.log_diag(l.rstrip(), append=True))

                process.wait()

                if process.returncode == 0:
                    self.root.after(0, lambda: self.log_diag("\n[SUCCESS] Tests passed!", append=True))
                else:
                    self.root.after(0, lambda: self.log_diag("\n[FAILED] Tests failed.", append=True))

            except Exception as e:
                self.root.after(0, lambda err=str(e): self.log_diag(f"\nError running tests: {err}", append=True))

        threading.Thread(target=_run, daemon=True).start()

    def run_gui_smoke_test(self):
        """Run GUI smoke test"""
        self.log_diag("Running GUI smoke test...", clear=True)

        def _run():
            test_file = self.script_dir / "tests" / "test_gui_smoke.py"

            if not test_file.exists():
                self.root.after(0, lambda: self.log_diag(f"\n[ERROR] Test file not found: {test_file}", append=True))
                return

            try:
                process = subprocess.Popen(
                    [sys.executable, str(test_file)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    cwd=str(self.script_dir)
                )

                for line in process.stdout:
                    self.root.after(0, lambda l=line: self.log_diag(l.rstrip(), append=True))

                process.wait()

                if process.returncode == 0:
                    self.root.after(0, lambda: self.log_diag("\n[SUCCESS] GUI smoke test passed", append=True))
                else:
                    self.root.after(0, lambda: self.log_diag(f"\n[FAILED] GUI smoke test failed", append=True))

            except Exception as e:
                self.root.after(0, lambda err=str(e): self.log_diag(f"\nError: {err}", append=True))

        threading.Thread(target=_run, daemon=True).start()

    def run_import_smoke_test(self):
        """Run import smoke test"""
        self.log_diag("Running module import smoke test...", clear=True)

        def _run():
            self.root.after(0, lambda: self.log_diag("Testing core module imports...\n", append=True))

            test_imports = [
                ("Core Query Engine", "ue5_query.core.hybrid_query", "HybridQueryEngine"),
                ("Definition Extractor", "ue5_query.core.definition_extractor", "DefinitionExtractor"),
                ("Query Intent", "ue5_query.core.query_intent", "QueryIntentAnalyzer"),
                ("Deployment Detector", "ue5_query.utils.deployment_detector", "DeploymentDetector"),
                ("Source Manager", "ue5_query.utils.source_manager", "SourceManager"),
                ("Config Manager", "ue5_query.utils.config_manager", "ConfigManager"),
            ]

            passed = 0
            failed = 0

            for name, module_path, class_name in test_imports:
                try:
                    # Try importing
                    parts = module_path.split('.')
                    module = __import__(module_path)
                    for part in parts[1:]:
                        module = getattr(module, part)

                    # Try accessing class
                    cls = getattr(module, class_name)

                    self.root.after(0, lambda n=name: self.log_diag(f"  ✓ {n}", append=True))
                    passed += 1
                except Exception as e:
                    self.root.after(0, lambda n=name, err=str(e): self.log_diag(f"  ✗ {n}: {err}", append=True))
                    failed += 1

            self.root.after(0, lambda p=passed, f=failed: self.log_diag(f"\n[RESULT] {p} passed, {f} failed", append=True))

            if failed == 0:
                self.root.after(0, lambda: self.log_diag("[SUCCESS] All imports successful", append=True))
            else:
                self.root.after(0, lambda: self.log_diag("[WARNING] Some imports failed", append=True))

        threading.Thread(target=_run, daemon=True).start()

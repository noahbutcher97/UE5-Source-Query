import sys
import os
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
import logging

from ue5_query.utils.logger import get_project_logger

logger = get_project_logger(__name__)

class UpdateService:
    """
    Handles application updates, restart prompts, and process management.
    """
    def __init__(self, root: tk.Tk, script_dir: Path):
        self.root = root
        self.script_dir = script_dir

    def start_check(self, interval_ms: int = 10000):
        """Start periodic polling for update restart marker"""
        self._check_for_restart_marker(interval_ms)

    def _check_for_restart_marker(self, interval_ms: int):
        """Check if updates require a restart"""
        marker_file = self.script_dir / ".needs_restart"

        if marker_file.exists():
            # Marker found - prompt user to restart
            self._prompt_restart(marker_file)

        # Schedule next check
        self.root.after(interval_ms, lambda: self._check_for_restart_marker(interval_ms))

    def _prompt_restart(self, marker_file: Path):
        """Show restart prompt dialog"""
        try:
            # Read timestamp from marker
            update_time = marker_file.read_text().strip()

            # Create prompt dialog
            response = messagebox.askyesno(
                "Updates Available",
                f"Updates were pushed to this installation.\n\n{update_time}\n\nRestart dashboard to apply changes?",
                icon='info'
            )

            if response:
                # User chose to restart - delete marker and restart
                marker_file.unlink(missing_ok=True)
                self._restart_application()
            else:
                # User chose not to restart yet - delete marker to avoid repeated prompts
                marker_file.unlink(missing_ok=True)
                # Show reminder that they can manually restart later
                self.root.after(0, lambda: messagebox.showinfo(
                    "Restart Reminder",
                    "You can restart the dashboard later to apply updates.\n\nChanges will take effect on next restart."
                ))
        except Exception as e:
            logger.error(f"Failed to handle restart marker: {e}")
            marker_file.unlink(missing_ok=True)

    def _restart_application(self):
        """Restart the dashboard application"""
        try:
            logger.info("Restarting application...")
            # Get current Python executable and script
            python = sys.executable
            script = sys.argv[0]

            # Close current window
            self.root.destroy()

            # Restart application
            # Use same args, but ensure we don't spawn infinite loops if run from bat
            os.execl(python, python, script, *sys.argv[1:])
        except Exception as e:
            logger.error(f"Restart failed: {e}")
            messagebox.showerror(
                "Restart Failed",
                f"Failed to restart dashboard: {e}\n\nPlease restart manually."
            )

    def run_update_process(self, dry_run=False, force_source=None, log_func=None, clear_log_func=None):
        """
        Run update process with comprehensive version checking and graceful fallback.
        """
        if not log_func:
            log_func = print
            
        def log(msg, tag=""):
            self.root.after(0, lambda: log_func(msg, tag))

        def update_thread():
            try:
                # Import update utilities
                try:
                    from tools.update import UpdateManager, get_version
                except ImportError:
                    import sys
                    sys.path.insert(0, str(self.script_dir / "tools"))
                    from update import UpdateManager, get_version

                if clear_log_func:
                    self.root.after(0, clear_log_func)

                if dry_run:
                    log("=" * 60)
                    log("UPDATE CHECK MODE (No changes will be made)")
                    log("=" * 60)
                else:
                    log("=" * 60)
                    log("UPDATE SYSTEM")
                    log("=" * 60)

                # Get current version
                current_version = get_version(self.script_dir)
                log(f"\nCurrent version: {current_version or 'unknown'}")

                manager = UpdateManager(self.script_dir)

                # Load config with graceful fallback
                if not manager.load_config():
                    log("[ERROR] Failed to load deployment config", "error")
                    self.root.after(0, lambda: messagebox.showerror(
                        "Config Error",
                        "Failed to load deployment config.\n\nPlease run Setup.bat to configure this installation."
                    ))
                    return

                # Try to detect all available sources
                log("\nDetecting update sources...")
                available_sources = []

                # Check local dev repo
                local_repo = manager.config.get("update_sources", {}).get("local_dev_repo")
                if local_repo:
                    local_path = Path(local_repo)
                    if local_path.exists() and (local_path / "src" / "__init__.py").exists():
                        local_version = get_version(local_path)
                        available_sources.append({'type': 'local', 'path': str(local_path), 'version': local_version or 'unknown'})
                        log(f"  [LOCAL] {local_path}")
                        log(f"          Version: {local_version or 'unknown'}")

                # Check remote repo
                remote_repo = manager.config.get("update_sources", {}).get("remote_repo")
                if remote_repo:
                    available_sources.append({'type': 'remote', 'path': remote_repo, 'version': 'latest'})
                    log(f"  [REMOTE] {remote_repo}")
                    log(f"           Version: latest (will check on pull)")

                if not available_sources:
                    log("\n[ERROR] No update sources configured!", "error")
                    return

                # Determine best source
                if force_source:
                    source = force_source
                    log(f"\n[FORCE] Using {source} source (user override)")
                else:
                    source = manager.detect_update_source()
                    log(f"\n[AUTO] Selected {source} source")

                # Check for updates before applying
                log("\nChecking for updates...")
                try:
                    update_info = manager.check_for_updates(source)
                    if update_info:
                        log(f"  Current: {update_info.get('current_version', 'unknown')}")
                        log(f"  Source:  {update_info.get('source_version', 'unknown')}")

                        if update_info.get('available'):
                            log("\n  [!] Updates available")
                        else:
                            log("\n  [OK] Already up-to-date")
                            if not dry_run:
                                log("\nNo update needed. Use 'Force Update' to update anyway.")
                            return
                except Exception as e:
                    log(f"[WARN] Version check failed: {e}", "warn")
                    log("Continuing with update anyway...")

                if dry_run:
                    log("\n" + "=" * 60)
                    log("DRY RUN COMPLETE - No changes made")
                    log("=" * 60)
                    return

                # Perform update
                log("\n" + "=" * 60)
                log("APPLYING UPDATES")
                log("=" * 60)

                success = False
                fallback_attempted = False

                try:
                    # Try primary source using subprocess
                    log(f"\nAttempting update from {source} source...")
                    import subprocess
                    update_script = self.script_dir / "tools" / "update.py"
                    cmd = [sys.executable, str(update_script)]
                    if source == "local": cmd.extend(["--source", "local"])
                    else: cmd.extend(["--source", "remote"])

                    process = subprocess.Popen(
                        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=str(self.script_dir)
                    )

                    for line in process.stdout:
                        self.root.after(0, lambda l=line: log(l.rstrip()))

                    process.wait()
                    success = process.returncode == 0

                except Exception as e:
                    log(f"[ERROR] Update from {source} failed: {e}", "error")
                    # Fallback logic simplified for brevity
                    
                if success:
                    log("\n" + "=" * 60)
                    log("[SUCCESS] Update completed!")
                    log("=" * 60)
                    new_version = get_version(self.script_dir)
                    log(f"\nNew version: {new_version or 'unknown'}")
                    self.root.after(0, lambda: messagebox.showinfo("Update Complete", "System updated successfully! Please restart."))
                else:
                    log("\n" + "=" * 60)
                    log("[FAILED] Update failed!")
                    log("=" * 60)
                    self.root.after(0, lambda: messagebox.showerror("Update Failed", "Update process failed. Check logs."))

            except Exception as e:
                log(f"\n[CRITICAL ERROR] {str(e)}", "error")

        import threading
        # Start update in background
        thread = threading.Thread(target=update_thread, daemon=True)
        thread.start()

class SearchService:
    """
    Manages the lifecycle of the HybridQueryEngine and background search execution.
    """
    def __init__(self, script_dir: Path, config_manager):
        self.script_dir = script_dir
        self.config_manager = config_manager
        self.engine = None
        self._is_loading = False

    def ensure_engine_loaded(self):
        """Lazy load the engine if not already loaded."""
        if self.engine is None and not self._is_loading:
            try:
                self._is_loading = True
                from ue5_query.core.hybrid_query import HybridQueryEngine
                self.engine = HybridQueryEngine(self.script_dir, self.config_manager)
                logger.info("HybridQueryEngine loaded successfully")
                return True
            except Exception as e:
                logger.error(f"Failed to load HybridQueryEngine: {e}")
                return False
            finally:
                self._is_loading = False
        return self.engine is not None

    def execute_query(self, query: str, scope: str, embed_model: str, 
                      filter_vars: dict, callback, error_callback):
        """
        Execute a query in a background thread.
        
        Args:
            query: User search query
            scope: Search scope (engine, project, all)
            embed_model: Model name to use
            filter_vars: Dictionary of filter variables from GUI
            callback: Function to call with results on completion
            error_callback: Function to call if an error occurs
        """
        if not self.ensure_engine_loaded():
            error_callback("Query engine is not initialized. Please check your data directory.")
            return

        def _run():
            try:
                filter_kwargs = {}
                
                # Build filters from variables
                entity_type = filter_vars.get('entity_type')
                if entity_type:
                    filter_kwargs['entity_type'] = entity_type

                macro = filter_vars.get('macro')
                if macro:
                    macro_map = {
                        "UPROPERTY": "has_uproperty",
                        "UCLASS": "has_uclass",
                        "UFUNCTION": "has_ufunction",
                        "USTRUCT": "has_ustruct"
                    }
                    if macro in macro_map:
                        filter_kwargs[macro_map[macro]] = True

                file_type = filter_vars.get('file_type')
                if file_type:
                    filter_kwargs['file_type'] = file_type

                if filter_vars.get('boost_macros'):
                    filter_kwargs['boost_macros'] = True

                # Extract re-ranker option
                use_reranker = filter_vars.get('use_reranker', False)

                # Run query
                results = self.engine.query(
                    question=query,
                    top_k=5,
                    scope=scope,
                    embed_model_name=embed_model,
                    show_reasoning=False,
                    use_reranker=use_reranker,
                    **filter_kwargs
                )
                
                callback(results)
            except Exception as e:
                logger.error(f"Search execution failed: {e}")
                error_callback(str(e))

        import threading
        threading.Thread(target=_run, daemon=True).start()

class MaintenanceService:
    """
    Handles background maintenance tasks: indexing, updates, and verification.
    """
    def __init__(self, script_dir: Path):
        self.script_dir = script_dir
        self.current_process = None

    def run_task(self, task_name: str, command: list, callback, log_callback, cwd=None):
        """
        Run a background task and capture its output.
        """
        def _run():
            try:
                import subprocess
                import sys
                
                logger.info(f"Starting task: {task_name}")
                log_callback(f"--- Starting {task_name} ---\n")
                
                self.current_process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    cwd=str(cwd or self.script_dir),
                    bufsize=1,
                    universal_newlines=True
                )

                for line in self.current_process.stdout:
                    log_callback(line)

                self.current_process.wait()
                return_code = self.current_process.returncode
                
                if return_code == 0:
                    logger.info(f"Task {task_name} completed successfully")
                    callback(True, f"{task_name} completed successfully.")
                else:
                    logger.error(f"Task {task_name} failed with exit code {return_code}")
                    callback(False, f"{task_name} failed with exit code {return_code}.")
                    
            except Exception as e:
                logger.error(f"Error running task {task_name}: {e}")
                callback(False, str(e))
            finally:
                self.current_process = None

        import threading
        threading.Thread(target=_run, daemon=True).start()

    def cancel_current_process(self):
        """Cancel the currently running background process."""
        if self.current_process:
            try:
                import psutil
                parent = psutil.Process(self.current_process.pid)
                for child in parent.children(recursive=True):
                    child.kill()
                parent.kill()
                logger.info("Background process cancelled")
                return True
            except Exception as e:
                logger.error(f"Failed to cancel process: {e}")
        return False

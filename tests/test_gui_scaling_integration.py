"""
Integration tests for GUI Scaling persistence and application.
"""
import unittest
import sys
import tempfile
import shutil
import tkinter as tk
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ue5_query.management.gui_dashboard import UnifiedDashboard
from ue5_query.utils.gui_layout import LayoutMetrics
from ue5_query.utils.config_manager import ConfigManager

class TestDashboardScaling(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        
        # Setup mock config structure
        self.config_dir = self.test_dir / "config"
        self.config_dir.mkdir()
        self.env_file = self.config_dir / ".env"
        self.env_file.write_text("GUI_TEXT_SCALE=1.0\n")
        
        # Create root for tk variables
        # We need a partial real root for StringVar to work, OR we mock StringVar
        self.patcher = patch('tkinter.Tk')
        self.MockTk = self.patcher.start()
        self.root = self.MockTk.return_value
        
        # Configure screen dimensions for WindowManager
        self.root.winfo_screenwidth.return_value = 1920
        self.root.winfo_screenheight.return_value = 1080
        self.root.winfo_fpixels.return_value = 96.0
        
        # Reset Metrics
        LayoutMetrics._instance = None

    def tearDown(self):
        self.patcher.stop()
        shutil.rmtree(self.test_dir)
        LayoutMetrics._instance = None

    @patch("ue5_query.management.gui_dashboard.ConfigManager")
    @patch("ue5_query.management.gui_dashboard.LayoutMetrics")
    @patch("ue5_query.management.gui_dashboard.Theme")
    def test_gui_init_with_scaling(self, mock_theme, mock_metrics, mock_config):
        """Test dashboard initialization with different scaling factors"""
        root = MagicMock()
        mock_config.return_value.get_scale_factor.return_value = 1.5
        
        # Mock Metrics
        mock_metrics = mock_metrics_cls.return_value
        mock_metrics.text_scale = 1.0 # Default before load
        
        # Mock tk variables
        with patch('tkinter.StringVar') as MockStringVar, \
             patch('tkinter.DoubleVar') as MockDoubleVar, \
             patch('tkinter.BooleanVar') as MockBooleanVar, \
             patch('tkinter.ttk.Style'):
            
            MockDoubleVar.return_value.get.return_value = 1.5
            
            # Init dashboard
            with patch.object(UnifiedDashboard, 'create_layout'), \
                 patch.object(UnifiedDashboard, '_load_initial_engine_path'), \
                 patch.object(UnifiedDashboard, '_check_first_run'):
                
                dashboard = UnifiedDashboard(self.root)
                dashboard.script_dir = self.test_dir
                
                # Verify text_scale_var initialized
                MockDoubleVar.assert_called()
                
                # Check calls
                mock_cm.get.assert_any_call('GUI_TEXT_SCALE', mock_metrics.text_scale)

    @patch("ue5_query.management.gui_dashboard.ConfigManager")
    @patch("ue5_query.management.gui_dashboard.LayoutMetrics")
    @patch("ue5_query.management.gui_dashboard.messagebox")
    def test_manual_scale_override(self, mock_msg, mock_metrics, mock_config):
        """Test applying scale saves config and prompts restart"""
        mock_cm = mock_cm_cls.return_value
        mock_metrics = mock_metrics_cls.return_value
        
        with patch('tkinter.StringVar'), \
             patch('tkinter.DoubleVar') as MockDoubleVar, \
             patch('tkinter.BooleanVar'), \
             patch('tkinter.ttk.Style'), \
             patch.object(UnifiedDashboard, 'create_layout'), \
             patch.object(UnifiedDashboard, '_load_initial_engine_path'), \
             patch.object(UnifiedDashboard, '_check_first_run'):
             
            dashboard = UnifiedDashboard(self.root)
            dashboard.text_scale_var = MagicMock()
            dashboard.text_scale_var.get.return_value = 1.25
            
            # User says No to restart
            mock_msgbox.askyesno.return_value = False
            
            dashboard.apply_ui_scale()
            
            # Verify Metrics updated
            mock_metrics.set_text_scale.assert_called_with(1.25)
            
            # Verify Config updated
            self.assertTrue(mock_cm.set.called)
            self.assertTrue(mock_cm.save.called)

if __name__ == "__main__":
    unittest.main()

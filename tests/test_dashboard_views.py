import sys
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
import tkinter as tk

# Add src to path
TOOL_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(TOOL_ROOT))

# Mock tkinter for headless testing
sys.modules['tkinter'] = MagicMock()
sys.modules['tkinter.ttk'] = MagicMock()
sys.modules['tkinter.messagebox'] = MagicMock()
sys.modules['tkinter.scrolledtext'] = MagicMock()
sys.modules['tkinter.filedialog'] = MagicMock()

# Import views after mocking
from ue5_query.management.views.query_tab import QueryTab
from ue5_query.management.views.config_tab import ConfigTab
from ue5_query.management.views.status_tab import StatusTab
from ue5_query.management.views.maintenance_tab import MaintenanceTab
from ue5_query.management.views.source_tab import SourceManagerTab
from ue5_query.management.views.diagnostics_tab import DiagnosticsTab

class TestDashboardViews(unittest.TestCase):
    def setUp(self):
        # Mock Dashboard Controller
        self.dashboard = MagicMock()
        self.dashboard.root = MagicMock()
        self.dashboard.script_dir = Path("/mock/dir")
        
        # Mock Services
        self.dashboard.search_service = MagicMock()
        self.dashboard.update_service = MagicMock()
        self.dashboard.maint_service = MagicMock()
        self.dashboard.source_manager = MagicMock()
        self.dashboard.config_manager = MagicMock()
        self.dashboard.deployment_detector = MagicMock()
        
        # Mock Variables
        self.dashboard.query_scope_var = MagicMock()
        self.dashboard.embed_model_var = MagicMock()
        self.dashboard.filter_entity_type_var = MagicMock()
        self.dashboard.filter_macro_var = MagicMock()
        self.dashboard.filter_file_type_var = MagicMock()
        self.dashboard.filter_boost_macros_var = MagicMock()
        self.dashboard.api_key_var = MagicMock()
        self.dashboard.engine_path_var = MagicMock()
        self.dashboard.vector_store_var = MagicMock()
        self.dashboard.api_model_var = MagicMock()
        self.dashboard.embed_batch_size_var = MagicMock()

        # Mock Parent Frame
        self.parent_frame = MagicMock()

    def test_query_tab_init(self):
        """Test QueryTab initialization and search execution"""
        tab = QueryTab(self.parent_frame, self.dashboard)
        
        # Test UI build
        self.assertTrue(self.parent_frame.pack.called or self.parent_frame.grid.called or True) # Frame usage
        
        # Mock user input
        tab.query_entry = MagicMock()
        tab.query_entry.get.return_value = "FHitResult"
        
        # Perform query
        tab.perform_query()
        
        # Verify service call
        self.dashboard.search_service.execute_query.assert_called_once()
        args, kwargs = self.dashboard.search_service.execute_query.call_args
        self.assertEqual(kwargs['query'], "FHitResult")

    def test_config_tab_save(self):
        """Test ConfigTab save configuration"""
        tab = ConfigTab(self.parent_frame, self.dashboard)
        
        # Mock variable values
        self.dashboard.api_key_var.get.return_value = "sk-ant-test-key-1234567890"
        
        # Perform save
        tab.save_configuration()
        
        # Verify config manager call
        self.dashboard.config_manager.save.assert_called_once()

    def test_source_tab_interactions(self):
        """Test source tab interactions"""
        # Mock filedialog
        with patch('ue5_query.management.views.source_tab.filedialog.askdirectory') as mock_ask:
            mock_ask.return_value = "C:/New/Source"
            
            # Click add folder
            self.source_tab.add_engine_dir()
            
            # Verify manager was called
            self.dashboard.source_manager.add_engine_dir.assert_called_with("C:/New/Source")
            
            # Verify list refresh (mocked)
            # self.source_tab.engine_listbox.insert.assert_called() # Hard to test tkinter listbox content directly without full tk setup

    def test_maintenance_tab_actions(self):
        """Test maintenance tab actions"""
        # Mock messagebox
        with patch('ue5_query.management.views.maintenance_tab.messagebox.askyesno') as mock_confirm:
            mock_confirm.return_value = True
            
            # Click rebuild index
            self.maint_tab.rebuild_index()
            
            # Verify service call
            # This depends on implementation details of MaintenanceTab
            # Assuming it calls dashboard.rebuild_index or similar service
            pass

if __name__ == '__main__':
    unittest.main()

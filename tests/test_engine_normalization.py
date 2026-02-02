import unittest
import tempfile
import shutil
from pathlib import Path
from ue5_query.core.engine_definitions import EnginePathNormalizer, InvalidEngineLayoutError

class TestEnginePathNormalizer(unittest.TestCase):
    def setUp(self):
        self.normalizer = EnginePathNormalizer()
        self.test_dir = tempfile.mkdtemp()
        self.root = Path(self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def create_structure(self, base: Path, markers):
        for marker in markers:
            path = base / marker
            if '.' in marker: # Assume file
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
            else: # Assume directory
                path.mkdir(parents=True, exist_ok=True)

    def test_launcher_standard_internal(self):
        """Test detection of internal root (e.g. C:/.../UE_5.3/Engine)"""
        # Create "Engine" dir with markers inside
        engine_root = self.root / "UE_5.3" / "Engine"
        markers = ["Source", "Config", "Content", "Binaries"]
        self.create_structure(engine_root, markers)
        
        normalized = self.normalizer.normalize(engine_root)
        self.assertEqual(normalized, engine_root)

    def test_launcher_standard_base(self):
        """Test detection of base root (e.g. C:/.../UE_5.3)"""
        base_root = self.root / "UE_5.3"
        markers = ["Engine", "Engine/Source"]
        self.create_structure(base_root, markers)
        
        normalized = self.normalizer.normalize(base_root)
        # Should return the 'Engine' subdirectory
        self.assertEqual(normalized, base_root / "Engine")

    def test_source_build_github(self):
        """Test detection of source build (with GenerateProjectFiles.bat)"""
        source_root = self.root / "UnrealEngine"
        markers = ["GenerateProjectFiles.bat", "Engine/Source"]
        self.create_structure(source_root, markers)
        
        normalized = self.normalizer.normalize(source_root)
        # Should return the 'Engine' subdirectory
        self.assertEqual(normalized, source_root / "Engine")

    def test_invalid_layout(self):
        """Test rejection of random folder"""
        random_dir = self.root / "RandomDir"
        random_dir.mkdir()
        
        with self.assertRaises(InvalidEngineLayoutError):
            self.normalizer.normalize(random_dir)

    def test_partial_match_fail(self):
        """Test rejection of partial match (e.g. missing Source)"""
        broken_engine = self.root / "BrokenEngine"
        # Only Config, missing Source
        self.create_structure(broken_engine, ["Config", "Content"])
        
        with self.assertRaises(InvalidEngineLayoutError):
            self.normalizer.normalize(broken_engine)

    def test_nonexistent_path(self):
        """Test rejection of non-existent path"""
        with self.assertRaises(FileNotFoundError):
            self.normalizer.normalize(self.root / "Doesnotexist")

if __name__ == '__main__':
    unittest.main()

import unittest
from pathlib import Path
from ue5_query.utils.ue_path_utils import UEPathUtils

class TestPathUtilsOptimization(unittest.TestCase):
    def test_optimize_paths_basic(self):
        paths = ["C:/A/B", "C:/A"]
        optimized = UEPathUtils.optimize_path_list(paths)
        # Normalize comparison
        expected = str(Path("C:/A"))
        self.assertEqual(optimized, [expected])

    def test_optimize_paths_subsumption(self):
        # Existing: Child. New: Parent. Result: Parent.
        paths = ["C:/Project/Source/Module", "C:/Project/Source"]
        optimized = UEPathUtils.optimize_path_list(paths)
        self.assertEqual(len(optimized), 1)
        self.assertTrue(str(Path("C:/Project/Source")) in optimized[0])

    def test_optimize_paths_redundancy(self):
        # Existing: Parent. New: Child. Result: Parent.
        paths = ["C:/Project/Source", "C:/Project/Source/Module"]
        optimized = UEPathUtils.optimize_path_list(paths)
        self.assertEqual(len(optimized), 1)
        self.assertTrue(str(Path("C:/Project/Source")) in optimized[0])

if __name__ == '__main__':
    unittest.main()

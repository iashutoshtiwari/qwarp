"""Run with pytest or system Python after installing a distro package.

QT_QPA_PLATFORM=offscreen /usr/bin/python3 tests/test_runtime_imports.py
No pytest dependency is needed for the installed-package smoke check.
"""

import ast
import importlib
import unittest
from pathlib import Path


class RuntimeImportsTest(unittest.TestCase):
    def test_required_qt_imports(self):
        from PyQt6.QtSvg import QSvgRenderer

        import qwarp
        import qwarp.main

        self.assertTrue(callable(QSvgRenderer))
        # Include lazy imports, which --version and importing main do not reach.
        # Read the installed package so this also covers the built artifact.
        for source in Path(qwarp.__file__).parent.rglob("*.py"):
            tree = ast.parse(source.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("PyQt6."):
                    with self.subTest(module=node.module, source=source.name):
                        module = importlib.import_module(node.module)
                        for alias in node.names:
                            self.assertTrue(hasattr(module, alias.name), f"{node.module}.{alias.name}")


if __name__ == "__main__":
    unittest.main()

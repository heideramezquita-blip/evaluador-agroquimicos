import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def top_level_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    return imports


class ArchitectureBoundaryTests(unittest.TestCase):
    def test_core_modules_do_not_depend_on_streamlit(self):
        offenders = []
        for path in SRC.glob("*.py"):
            if "streamlit" in top_level_imports(path):
                offenders.append(path.name)
        self.assertEqual(offenders, [])

    def test_ui_helpers_are_framework_independent(self):
        imports = top_level_imports(SRC / "ui_helpers.py")
        self.assertNotIn("streamlit", imports)

    def test_engine_has_no_presentation_dependency(self):
        imports = (SRC / "engine.py").read_text(encoding="utf-8")
        self.assertNotIn("ui_helpers", imports)
        self.assertNotIn("streamlit", imports)


if __name__ == "__main__":
    unittest.main()

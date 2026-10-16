import importlib.util
import json
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "initcall_order.py"
SPEC = importlib.util.spec_from_file_location("initcall_order", SCRIPT)
initcall_order = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(initcall_order)


# Function addresses deliberately differ from pointer order, and input is unsorted.
COMPLETE_MAP = """ffffff8008100200 t alpha_init
ffffff8009000010 d __initcall_final_init7
ffffff8009000008 d __initcall_alpha_init6s
ffffff8009000000 D __initcall6_start
ffffff8008100100 t final_init
ffffff8009000018 D __initcall_end
ffffff8009000000 d __initcall_zeta_init6
ffffff8009000010 D __initcall7_start
ffffff8008100300 t zeta_init
"""


class InitcallOrderTests(unittest.TestCase):
    def test_pointer_order_includes_sync_calls(self):
        entries = initcall_order.read_order(COMPLETE_MAP)
        self.assertEqual([e["function_inferred"] for e in entries],
                         ["zeta_init", "alpha_init", "final_init"])
        self.assertEqual([e["level"] for e in entries], [6, 6, 7])
        self.assertEqual([e["sync"] for e in entries], [False, True, False])

    def test_clang_lto_symbols_and_numbered_function_names(self):
        contents = COMPLETE_MAP.replace("__initcall_zeta_init6", "__initcall_12_345_driver66.llvm.12345")
        self.assertEqual(initcall_order.read_order(contents)[0]["function_inferred"], "driver6")

    def test_missing_boundary_is_rejected(self):
        contents = COMPLETE_MAP.replace("ffffff8009000010 D __initcall7_start\n", "")
        with self.assertRaisesRegex(ValueError, "missing boundaries"):
            initcall_order.read_order(contents)

    def test_truncated_table_is_rejected(self):
        contents = COMPLETE_MAP.replace("ffffff8009000008 d __initcall_alpha_init6s\n", "")
        with self.assertRaisesRegex(ValueError, "incomplete initcall table"):
            initcall_order.read_order(contents)

    def test_level_mismatch_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "disagrees with boundaries"):
            initcall_order.read_order(COMPLETE_MAP.replace("__initcall_final_init7", "__initcall_final_init6"))

    def test_duplicate_pointer_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "ambiguous initcall pointer"):
            initcall_order.read_order(COMPLETE_MAP + "ffffff8009000000 d __initcall_other6\n")

    def test_unaligned_pointer_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unaligned initcall pointer"):
            initcall_order.read_order(COMPLETE_MAP.replace("ffffff8009000008 d", "ffffff8009000009 d"))

    def test_reversed_boundaries_are_rejected(self):
        contents = COMPLETE_MAP.replace("ffffff8009000010 D __initcall7_start", "ffffff8009000020 D __initcall7_start")
        with self.assertRaisesRegex(ValueError, "invalid boundaries"):
            initcall_order.read_order(contents)

    def test_empty_level_six_is_valid(self):
        contents = """ffffff8009000000 D __initcall6_start
ffffff8009000000 D __initcall7_start
ffffff8009000000 d __initcall_late_init7s
ffffff8009000008 D __initcall_end
"""
        self.assertEqual(initcall_order.read_order(contents)[0]["level"], 7)

    def test_json_cli_filters_level_without_changing_input(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "System.map"
            path.write_text(COMPLETE_MAP, encoding="utf-8")
            output, warning = StringIO(), StringIO()
            with redirect_stdout(output), redirect_stderr(warning):
                self.assertEqual(initcall_order.main([str(path), "--level", "7", "--json"]), 0)
            self.assertEqual([e["function_inferred"] for e in json.loads(output.getvalue())], ["final_init"])
            self.assertIn("inferred", warning.getvalue())
            self.assertEqual(path.read_text(encoding="utf-8"), COMPLETE_MAP)


if __name__ == "__main__":
    unittest.main()

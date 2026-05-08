import tempfile
import unittest
from pathlib import Path

from pedigreelab.ped_io import load_ped, save_ped


class PedIoTests(unittest.TestCase):
    def test_load_and_save_ped_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            source = tmp_path / "family.ped"
            source.write_text(
                "\n".join(
                    [
                        "# comment",
                        "# PedigreeLab position C1 10 20",
                        "FAM1 F1 0 0 1 0",
                        "FAM1 M1 0 0 2 0",
                        "FAM1 C1 F1 M1 2 affected marker1 marker2",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            pedigree = load_ped(source)

            self.assertEqual(len(pedigree.people), 3)
            self.assertEqual(pedigree.people["C1"].x, 10)
            self.assertEqual(pedigree.people["C1"].extra_columns, ["marker1", "marker2"])
            self.assertEqual(pedigree.validate(), [])

            target = tmp_path / "saved.ped"
            save_ped(pedigree, target)
            reloaded = load_ped(target)

            self.assertEqual(reloaded.people["C1"].maternal_id, "M1")
            self.assertEqual(reloaded.people["C1"].phenotype, "affected")


if __name__ == "__main__":
    unittest.main()

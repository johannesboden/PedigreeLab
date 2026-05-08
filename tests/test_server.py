import json
import tempfile
import unittest
from pathlib import Path

from pedigreelab.server import PedigreeApp


class ServerStateTests(unittest.TestCase):
    def test_layout_uses_posted_current_state_instead_of_old_file_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "family.ped"
            path.write_text(
                "\n".join(
                    [
                        "FAM1 OLD1 0 0 1 0",
                        "FAM1 OLD2 0 0 2 0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            app = PedigreeApp(path)

            current_browser_state = {
                "mode": "pedigree",
                "people": [
                    {
                        "family_id": "FAM1",
                        "individual_id": "P001",
                        "paternal_id": "0",
                        "maternal_id": "0",
                        "sex": "1",
                        "phenotype": "0",
                        "x": 260,
                        "y": 120,
                        "extra_columns": [],
                    },
                    {
                        "family_id": "FAM1",
                        "individual_id": "P002",
                        "paternal_id": "0",
                        "maternal_id": "0",
                        "sex": "2",
                        "phenotype": "0",
                        "x": 430,
                        "y": 120,
                        "extra_columns": [],
                    },
                    {
                        "family_id": "FAM1",
                        "individual_id": "P003",
                        "paternal_id": "P001",
                        "maternal_id": "P002",
                        "sex": "1",
                        "phenotype": "0",
                        "x": 345,
                        "y": 300,
                        "extra_columns": [],
                    },
                ],
                "comments": [],
                "partner_links": [["P001", "P002"]],
            }

            app.layout_and_save_from_json(json.dumps(current_browser_state).encode("utf-8"))
            result = json.loads(app.as_json())
            result_ids = {person["individual_id"] for person in result["people"]}
            saved = path.read_text(encoding="utf-8")

            self.assertEqual(result_ids, {"P001", "P002", "P003"})
            self.assertIn("# PedigreeLab partner P001 P002", saved)
            self.assertNotIn("OLD1", saved)


if __name__ == "__main__":
    unittest.main()

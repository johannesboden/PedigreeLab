import unittest

from pedigreelab.layout import apply_generation_layout
from pedigreelab.models import Pedigree, Person


class LayoutTests(unittest.TestCase):
    def test_generation_layout_keeps_minimum_spacing(self) -> None:
        pedigree = Pedigree()
        pedigree.add_person(Person("FAM1", "F1", sex="1"))
        pedigree.add_person(Person("FAM1", "M1", sex="2"))
        for index in range(5):
            pedigree.add_person(Person("FAM1", f"C{index}", paternal_id="F1", maternal_id="M1"))

        apply_generation_layout(pedigree)

        children = sorted(
            [person for person in pedigree.people.values() if person.individual_id.startswith("C")],
            key=lambda person: person.x or 0,
        )
        distances = [
            (right.x or 0) - (left.x or 0)
            for left, right in zip(children, children[1:])
        ]

        self.assertTrue(all(distance >= 170 for distance in distances))


if __name__ == "__main__":
    unittest.main()

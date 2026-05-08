from __future__ import annotations

from .models import UNKNOWN_PARENT, Pedigree, Person


def apply_generation_layout(pedigree: Pedigree) -> None:
    generations = _compute_generations(pedigree)
    rows: dict[int, list[Person]] = {}
    for person in pedigree.people.values():
        rows.setdefault(generations.get(person.individual_id, 0), []).append(person)

    for generation, people in sorted(rows.items()):
        people.sort(key=lambda item: item.individual_id)
        for index, person in enumerate(people):
            person.x = 120 + index * 150
            person.y = 90 + generation * 150


def _compute_generations(pedigree: Pedigree) -> dict[str, int]:
    generations: dict[str, int] = {}

    def visit(person_id: str, stack: set[str]) -> int:
        if person_id in generations:
            return generations[person_id]
        if person_id in stack or person_id not in pedigree.people:
            return 0

        person = pedigree.people[person_id]
        parent_generations = [
            visit(parent_id, stack | {person_id})
            for parent_id in (person.paternal_id, person.maternal_id)
            if parent_id != UNKNOWN_PARENT and parent_id in pedigree.people
        ]
        generation = max(parent_generations) + 1 if parent_generations else 0
        generations[person_id] = generation
        return generation

    for individual_id in pedigree.people:
        visit(individual_id, set())
    return generations

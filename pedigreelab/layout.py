from __future__ import annotations

from .models import UNKNOWN_PARENT, Pedigree, Person


def apply_generation_layout(pedigree: Pedigree) -> None:
    generations = _compute_generations(pedigree)
    rows: dict[int, list[Person]] = {}
    for person in pedigree.people.values():
        rows.setdefault(generations.get(person.individual_id, 0), []).append(person)

    order: dict[str, int] = {}
    min_gap = 170
    top = 90
    row_gap = 155

    for generation in sorted(rows):
        people = rows[generation]
        people.sort(key=lambda item: _family_order_key(item, order, pedigree))
        for index, person in enumerate(people):
            parent_xs = [
                pedigree.people[parent_id].x
                for parent_id in (person.paternal_id, person.maternal_id)
                if parent_id != UNKNOWN_PARENT
                and parent_id in pedigree.people
                and pedigree.people[parent_id].x is not None
            ]
            person.x = sum(parent_xs) / len(parent_xs) if parent_xs else 120 + index * min_gap
            person.y = top + generation * row_gap
        _spread_row(people, min_gap=min_gap)
        for index, person in enumerate(sorted(people, key=lambda item: item.x or 0)):
            order[person.individual_id] = index


def _family_order_key(person: Person, order: dict[str, int], pedigree: Pedigree) -> tuple[float, str]:
    parent_orders = [
        order[parent_id]
        for parent_id in (person.paternal_id, person.maternal_id)
        if parent_id != UNKNOWN_PARENT and parent_id in order
    ]
    if parent_orders:
        return (sum(parent_orders) / len(parent_orders), person.individual_id)
    return (10_000, person.individual_id)


def _spread_row(people: list[Person], min_gap: int) -> None:
    if not people:
        return
    people.sort(key=lambda item: (item.x if item.x is not None else 0, item.individual_id))
    people[0].x = max(120, people[0].x or 120)
    for previous, current in zip(people, people[1:]):
        current.x = max(current.x or 120, (previous.x or 120) + min_gap)


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

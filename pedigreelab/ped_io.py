from __future__ import annotations

from pathlib import Path

from .models import Pedigree, Person


POSITION_PREFIX = "# PedigreeLab position "


def load_ped(path: str | Path) -> Pedigree:
    ped_path = Path(path)
    pedigree = Pedigree(source_path=str(ped_path))
    positions: dict[str, tuple[float, float]] = {}

    if not ped_path.exists():
        return pedigree

    for line_number, raw_line in enumerate(ped_path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#"):
            if line.startswith(POSITION_PREFIX):
                parts = line[len(POSITION_PREFIX) :].split()
                if len(parts) == 3:
                    try:
                        positions[parts[0]] = (float(parts[1]), float(parts[2]))
                    except ValueError:
                        pedigree.comments.append(raw_line)
                else:
                    pedigree.comments.append(raw_line)
            else:
                pedigree.comments.append(raw_line)
            continue

        parts = line.split()
        if len(parts) < 6:
            raise ValueError(f"{ped_path}:{line_number}: expected at least 6 columns")

        person = Person(
            family_id=parts[0],
            individual_id=parts[1],
            paternal_id=parts[2],
            maternal_id=parts[3],
            sex=parts[4],
            phenotype=parts[5],
            extra_columns=parts[6:],
        ).normalized()
        if person.individual_id in positions:
            person.x, person.y = positions[person.individual_id]
        pedigree.add_person(person)

    for individual_id, (x, y) in positions.items():
        if individual_id in pedigree.people:
            pedigree.people[individual_id].x = x
            pedigree.people[individual_id].y = y

    return pedigree


def save_ped(pedigree: Pedigree, path: str | Path) -> None:
    ped_path = Path(path)
    ped_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    for comment in pedigree.comments:
        if not comment.startswith(POSITION_PREFIX):
            lines.append(comment if comment.startswith("#") else f"# {comment}")

    for person in pedigree.people.values():
        if person.x is not None and person.y is not None:
            lines.append(f"{POSITION_PREFIX}{person.individual_id} {person.x:.1f} {person.y:.1f}")

    for person in pedigree.people.values():
        columns = [
            person.family_id,
            person.individual_id,
            person.paternal_id,
            person.maternal_id,
            person.sex,
            person.phenotype,
            *person.extra_columns,
        ]
        lines.append(" ".join(_escape_column(value) for value in columns))

    tmp_path = ped_path.with_suffix(ped_path.suffix + ".tmp")
    tmp_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    tmp_path.replace(ped_path)


def _escape_column(value: str) -> str:
    stripped = str(value).strip()
    return stripped or "0"

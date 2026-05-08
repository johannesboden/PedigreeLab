from __future__ import annotations

from dataclasses import dataclass, field


UNKNOWN_PARENT = "0"


@dataclass(slots=True)
class Person:
    family_id: str
    individual_id: str
    paternal_id: str = UNKNOWN_PARENT
    maternal_id: str = UNKNOWN_PARENT
    sex: str = "0"
    phenotype: str = "0"
    x: float | None = None
    y: float | None = None
    extra_columns: list[str] = field(default_factory=list)

    def normalized(self) -> "Person":
        self.family_id = self.family_id.strip() or "FAM1"
        self.individual_id = self.individual_id.strip()
        self.paternal_id = self.paternal_id.strip() or UNKNOWN_PARENT
        self.maternal_id = self.maternal_id.strip() or UNKNOWN_PARENT
        self.sex = self.sex.strip() or "0"
        self.phenotype = self.phenotype.strip() or "0"
        return self

    def to_dict(self) -> dict:
        return {
            "family_id": self.family_id,
            "individual_id": self.individual_id,
            "paternal_id": self.paternal_id,
            "maternal_id": self.maternal_id,
            "sex": self.sex,
            "phenotype": self.phenotype,
            "x": self.x,
            "y": self.y,
            "extra_columns": list(self.extra_columns),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Person":
        return cls(
            family_id=str(data.get("family_id") or "FAM1"),
            individual_id=str(data.get("individual_id") or ""),
            paternal_id=str(data.get("paternal_id") or UNKNOWN_PARENT),
            maternal_id=str(data.get("maternal_id") or UNKNOWN_PARENT),
            sex=str(data.get("sex") or "0"),
            phenotype=str(data.get("phenotype") or "0"),
            x=_optional_float(data.get("x")),
            y=_optional_float(data.get("y")),
            extra_columns=[str(value) for value in data.get("extra_columns", [])],
        ).normalized()


@dataclass(slots=True)
class Pedigree:
    people: dict[str, Person] = field(default_factory=dict)
    comments: list[str] = field(default_factory=list)
    source_path: str | None = None

    def add_person(self, person: Person) -> None:
        person.normalized()
        if not person.individual_id:
            raise ValueError("individual_id is required")
        self.people[person.individual_id] = person

    def validate(self) -> list[str]:
        errors: list[str] = []
        for person in self.people.values():
            for parent_id, label in (
                (person.paternal_id, "paternal_id"),
                (person.maternal_id, "maternal_id"),
            ):
                if parent_id != UNKNOWN_PARENT and parent_id not in self.people:
                    errors.append(
                        f"{person.individual_id}: {label} references missing person {parent_id}"
                    )
        return errors

    def to_dict(self) -> dict:
        return {
            "people": [person.to_dict() for person in self.people.values()],
            "comments": list(self.comments),
            "source_path": self.source_path,
            "errors": self.validate(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Pedigree":
        pedigree = cls(
            comments=[str(line) for line in data.get("comments", [])],
            source_path=data.get("source_path"),
        )
        for raw_person in data.get("people", []):
            pedigree.add_person(Person.from_dict(raw_person))
        return pedigree


def _optional_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    return float(value)

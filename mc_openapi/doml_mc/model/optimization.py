from dataclasses import dataclass


@dataclass
class Optimization:
    typeId: str


def parse_optimization(doc: dict) -> Optimization:
    return Optimization(
        typeId=doc["typeId"],
    )

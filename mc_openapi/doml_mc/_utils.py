from typing import TypeVar
from collections.abc import Iterable


_K = TypeVar("_K")
_V = TypeVar("_V")


def merge_dicts(it: Iterable[dict[_K, _V]]) -> dict[_K, _V]:
    return dict(kv for d in it for kv in d.items())

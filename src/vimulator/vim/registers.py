"""The unnamed register. Named registers arrive with the intermediate track."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Register:
    """Yanked or deleted text. Linewise text is stored as whole lines."""

    text: str
    linewise: bool

    @property
    def lines(self) -> list[str]:
        return self.text.split("\n")

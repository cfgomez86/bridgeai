from dataclasses import dataclass


@dataclass(frozen=True)
class CoherenceResult:
    is_coherent: bool
    warning: str | None
    reason_codes: list[str]

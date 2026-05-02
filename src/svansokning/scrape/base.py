from dataclasses import dataclass, field
from typing import Optional, Protocol


@dataclass
class Listing:
    id: str
    source: str
    url: str
    title: str = ""
    address: str = ""
    postcode: Optional[str] = None
    bedrooms: Optional[int] = None
    monthly_rent_gbp: Optional[int] = None
    available_from: Optional[str] = None
    furnished: Optional[str] = None
    let_agreed: Optional[bool] = None
    raw: dict = field(default_factory=dict)


class Scraper(Protocol):
    name: str

    def fetch(self) -> list[Listing]: ...

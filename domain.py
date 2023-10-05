import enum
from typing import Literal, Optional

import pydantic
from typing_extensions import TypedDict


class Operator(enum.IntEnum):
    ORANGE = 20801
    SFR = 20810
    FREE = 20815
    BOUYGUE = 20820


class Geometry(pydantic.BaseModel):
    type: Literal["Point"]
    coordinates: tuple[float, float]


class Properties(pydantic.BaseModel):
    label: str
    score: float
    housenumber: Optional[str] = None
    id: str
    name: str
    postcode: str
    citycode: str
    x: float
    y: float
    city: str
    district: str
    context: str
    type: str
    importance: float
    street: str


class Feature(pydantic.BaseModel):
    type: Literal["Feature"]
    geometry: Geometry
    properties: Properties


Coverage = TypedDict(
    "Coverage", {"2G": bool, "3G": bool, "4G": bool, "m_to_measurement": float}
)


class CoverageFeature(Feature):
    coverage: dict[Literal["ORANGE", "SFR", "FREE", "BOUYGUE"], Coverage]

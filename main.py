from typing import Annotated, Literal, Optional, cast

import pyproj
import fastapi
import requests
import pydantic


def lambert93_to_gps(x: int, y: int):
    lambert = pyproj.Proj(
        "+proj=lcc +lat_1=49 +lat_2=44 +lat_0=46.5 +lon_0=3 +x_0=700000 +y_0=6600000 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs"
    )
    wgs84 = pyproj.Proj("+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs")
    long, lat = cast(tuple[int, int], pyproj.transform(lambert, wgs84, x, y))
    return long, lat


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


def query_address(q: str):
    try:
        r = requests.get("https://api-adresse.data.gouv.fr/search", params={"q": q})
    except Exception as e:
        raise fastapi.HTTPException(
            fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
            f"Error while querying data.gouv.fr with query {q}: {e}",
        )
    try:
        return pydantic.TypeAdapter(list[Feature]).validate_python(r.json()["features"])
    except Exception as e:
        raise fastapi.HTTPException(
            fastapi.status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Error while processing data.gouv.fr response: {e}",
        )


app = fastapi.FastAPI()


@app.get("/coverage")
async def get(q: Annotated[str, fastapi.Query()]):
    query_address(q)

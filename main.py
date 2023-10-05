from typing import Annotated, Literal, Optional, cast

import pyproj
import fastapi
import requests
import pydantic
import csv
from pathlib import Path
import sqlite3


def lambert93_to_gps(x: int, y: int):
    lambert = pyproj.Proj(
        "+proj=lcc +lat_1=49 +lat_2=44 +lat_0=46.5 +lon_0=3 +x_0=700000 +y_0=6600000 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs"
    )
    wgs84 = pyproj.Proj("+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs")
    long, lat = cast(
        tuple[int, int],
        pyproj.Transformer.from_proj(lambert, wgs84).transform(x, y),
    )
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


def load_csv():
    db_name = "coverage.db"

    if Path(db_name).exists():
        return sqlite3.connect(db_name)

    print("Processing data...")
    db = sqlite3.connect(db_name)
    db.execute(
        """
    CREATE TABLE coverage (
        operator INT,
        x REAL,
        y REAL,
        _2G BOOL,
        _3G BOOl,
        _4G BOOL
    )
    """
    )
    with open("2018_01_Sites_mobiles_2G_3G_4G_France_metropolitaine_L93.csv", "r") as f:
        rows = [
            r
            for r in csv.DictReader(f, restkey="unknown", delimiter=";")
            if r["x"] != "#N/A" and r["y"] != "#N/A"
        ]

    _total = len(rows)
    db.execute("BEGIN TRANSACTION")
    for i, row in enumerate(rows):
        orig_x, orig_y = row["x"], row["y"]
        x, y = lambert93_to_gps(int(orig_x), int(orig_y))
        row["x"], row["y"] = x, y
        db.execute("INSERT INTO coverage VALUES (?, ?, ?, ?, ?, ?)", list(row.values()))
        if i % 1000 == 0:
            print(f"{i}/{_total}")
    db.execute("END TRANSACTION")

    return db


load_csv()

app = fastapi.FastAPI()


@app.get("/coverage")
async def get(q: Annotated[str, fastapi.Query()]):
    return query_address(q)

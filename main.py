import csv
import sqlite3
from pathlib import Path
from typing import Annotated, Literal

import fastapi
import haversine
import pydantic
import requests
import tqdm

import domain
import utils


def query_address(q: str):
    try:
        r = requests.get("https://api-adresse.data.gouv.fr/search", params={"q": q})
    except Exception as e:
        raise fastapi.HTTPException(
            fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
            f"Error while querying data.gouv.fr with query {q}: {e}",
        )
    try:
        return pydantic.TypeAdapter(list[domain.Feature]).validate_python(
            r.json()["features"]
        )
    except Exception as e:
        raise fastapi.HTTPException(
            fastapi.status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Error while processing data.gouv.fr response: {e}",
        )


def extend_feature_with_coverage(
    f: domain.Feature, db: sqlite3.Connection
) -> domain.CoverageFeature:
    result_long, result_lat = f.geometry.coordinates
    res = db.execute(
        f"""
        SELECT
            operator, long, lat, _2G, _3G, _4G,
            MIN((long-:long)*(long-:long) + (lat-:lat)*(lat-:lat)) AS distance
        FROM coverage
        GROUP BY operator
        """,
        {"long": result_long, "lat": result_lat},
    )
    coverage: dict[Literal["ORANGE", "SFR", "FREE", "BOUYGUE"], domain.Coverage] = {}
    for row in res.fetchall():
        operator, long, lat, _2g, _3g, _4g, _distance = row
        coverage[domain.Operator(operator).name] = {
            "2G": bool(_2g),
            "3G": bool(_3g),
            "4G": bool(_4g),
            "m_to_measurement": haversine.haversine(
                (result_lat, result_long), (lat, long), haversine.Unit.METERS
            ),
        }
    return domain.CoverageFeature(**f.model_dump(), coverage=coverage)


def load_csv(csv_name: str, db_name: str = "coverage.db"):
    if Path(db_name).exists():
        return sqlite3.connect(db_name)

    db = sqlite3.connect(db_name)
    db.execute(
        """
    CREATE TABLE coverage (
        operator INT,
        long REAL,
        lat REAL,
        _2G BOOL,
        _3G BOOl,
        _4G BOOL
    )
    """
    )
    with open(csv_name, "r") as f:
        rows = [
            r
            for r in csv.DictReader(f, restkey="unknown", delimiter=";")
            if r["x"] != "#N/A" and r["y"] != "#N/A"
        ]

    _total = len(rows)
    db.execute("BEGIN TRANSACTION")
    for row in tqdm.tqdm(rows, desc="Processing data"):
        orig_x, orig_y = row["x"], row["y"]
        long, lat = utils.lambert93_to_gps(int(orig_x), int(orig_y))
        row["x"], row["y"] = long, lat
        db.execute("INSERT INTO coverage VALUES (?, ?, ?, ?, ?, ?)", list(row.values()))
    db.execute("END TRANSACTION")

    return db


DB = load_csv("2018_01_Sites_mobiles_2G_3G_4G_France_metropolitaine_L93.csv")

app = fastapi.FastAPI()


@app.get("/coverage")
async def get(q: Annotated[str, fastapi.Query()]) -> list[domain.CoverageFeature]:
    return [extend_feature_with_coverage(f, DB) for f in query_address(q)]

from typing import cast

import pyproj


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

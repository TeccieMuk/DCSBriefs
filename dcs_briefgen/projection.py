from pyproj import Proj, Transformer

# global transformer (like your 'projector')
_transformer = None

def active_map(map_config: dict):
    """
    Initializes the map projection transformer using a map config
    with central_meridian, scale_factor, false_easting, false_northing
    """
    global _transformer

    proj_str = (
        f"+proj=tmerc +lat_0=0 +lon_0={map_config['central_meridian']} "
        f"+k_0={map_config['scale_factor']} "
        f"+x_0={map_config['false_easting']} +y_0={map_config['false_northing']} "
        "+towgs84=0,0,0,0,0,0,0 +units=m +vunits=m +ellps=WGS84 +no_defs +axis=neu"
    )

    # Mission coordinates (x,y) to WGS84 (lon,lat)
    proj_mission = Proj(proj_str)
    proj_wgs84 = Proj(proj="latlong", datum="WGS84")
    _transformer = Transformer.from_proj(proj_mission, proj_wgs84)

def miz_to_ll(y: float, x: float) -> dict:
    """
    Converts mission coordinates (x, y) in meters to lat/lon in degrees
    """
    if _transformer is None:
        raise RuntimeError("Transformer not initialized. Call active_map() first.")

    lon, lat = _transformer.transform(x, y)
    return lat, lon
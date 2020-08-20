""" Parsing tools for metadata from Google Earth Engine API. """
from collections import namedtuple
import numpy as np
from pyproj import CRS, Transformer

METADATA = namedtuple('Metadata', ','.join(['id',
                                            'creation_dt',
                                            'product_type',
                                            'platform',
                                            'instrument',
                                            'format',
                                            'from_dt',
                                            'to_dt',
                                            'center_dt',
                                            'coord',
                                            'geo_ref_points',
                                            'spatial_reference',
                                            'path',
                                            'bands']))

def get_geo_ref_points(coords, crs):
    ''' Converts spatiotemporal coordinates (EPSG: 4326) to spatial coordinates.

    Args:
        coords: The coords to convert.
        crs: The CRS to convert to.

    Returns:
        A dict mapping of the coordinates. For example:

        {'ul': {'lon': -180.0, 'lat': 40.0},
         'ur': {'lon': 180.0, 'lat': 40.0},
         'll': {'lon': -180.0, 'lat': -40.0},
         'lr': {'lon': 180.0, 'lat': -40.0}
        }
    '''
    source = CRS.from_epsg(4326)
    target = CRS.from_epsg(crs)

    _t = Transformer.from_crs(source, target)

    def transform(_p):
        _x, _y = _t.transform(_p['lat'], _p['lon'])
        return {'x': _x, 'y': _y}

    return {key: transform(_p) for key, _p in coords.items()}

def get_coords(geometry, spatial=False, rot=True):
    ''' Gets the corner extents of a scene.

    Args:
        geometry: An array of coordinates defining a rectangular polygon.
        spatial: A bool to determine the coordinate type.
        rot: A bool to determine the rotation of the scene.

    Returns:
        A dict map of the coordinates. For example:

        {'ul': {'lon': -180.0, 'lat': 40.0},
         'ur': {'lon': 180.0, 'lat': 40.0},
         'll': {'lon': -180.0, 'lat': -40.0},
         'lr': {'lon': 180.0, 'lat': -40.0}
        }
    '''


    array = np.array(geometry)
    if rot:
        xmin = array[(..., 0)].argmin()
        ymin = array[(..., 1)].argmin()


        xmax = array[(..., 0)].argmax()
        ymax = array[(..., 1)].argmax()

        if spatial:
            return {'ul': {'x': array[ymax][0], 'y': array[ymax][1]},
                    'ur': {'x': array[xmax][0], 'y': array[xmax][1]},
                    'll': {'x': array[xmin][0], 'y': array[xmin][1]},
                    'lr': {'x': array[ymin][0], 'y': array[ymin][1]}
                   }

        return {'ul': {'lon': array[ymax][0], 'lat': array[ymax][1]},
                'ur': {'lon': array[xmax][0], 'lat': array[xmax][1]},
                'll': {'lon': array[xmin][0], 'lat': array[xmin][1]},
                'lr': {'lon': array[ymin][0], 'lat': array[ymin][1]}
               }

    xmin = array[(..., 0)].min()
    ymin = array[(..., 1)].min()

    xmax = array[(..., 0)].max()
    ymax = array[(..., 1)].max()
    if spatial:
        return {'ul': {'x': xmin, 'y': ymax},
                'ur': {'x': xmax, 'y': ymax},
                'll': {'x': xmin, 'y': ymin},
                'lr': {'x': xmax, 'y': ymin}
               }

    return {'ul': {'lon': xmin, 'lat': ymax},
            'ur': {'lon': xmax, 'lat': ymax},
            'll': {'lon': xmin, 'lat': ymin},
            'lr': {'lon': xmax, 'lat': ymin}
           }

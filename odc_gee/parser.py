# pylint: disable=import-error
""" Parsing tools for metadata from Google Earth Engine API. """
from collections import namedtuple
import uuid

import numpy as np

from datacube.utils.geometry import polygon_from_transform, Geometry
from datacube.utils.geometry.tools import Affine

Metadata = namedtuple('Metadata', ','.join(['id',
                                            'creation_dt',
                                            'product',
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

def geometry_isfinite(geometry):
    """ Handles invalid GeoJSON containing Infinite values.

    Args:
        geometry (list): the coordinates of the GeoJSON.
    Returns:
        True if the coordinates contain Infinte values
        False if the coordinate do not.
    """
    array = np.array(geometry['coordinates'][0], dtype=np.float32)
    if np.isfinite(array).sum() == array.size:
        return True
    return False

def get_extents(points, spatial=False):
    ''' Gets the corner extents of a scene.

    Args:
        points: the points for the corners of a scene.
        spatial: A bool to determine the coordinate type.

    Returns:
        A dict map of the coordinates. For example:

        {'ul': {'lon': -180.0, 'lat': 40.0},
         'ur': {'lon': 180.0, 'lat': 40.0},
         'll': {'lon': -180.0, 'lat': -40.0},
         'lr': {'lon': 180.0, 'lat': -40.0}
        }
    '''
    keys = ('ll', 'ul', 'lr', 'ur')
    if spatial:
        return {key: dict(x=x, y=y) for key, (x, y) in zip(keys, points)}
    return {key: dict(lon=x, lat=y) for key, (x, y) in zip(keys, points)}

def parse(image_data, product):
    """ Parses the GEE metadata for ODC use.

    Args:
        image_data (dict): the image metadata to parse.
        product (datacube.model.DatasetType): the product information from the ODC index.

    Returns: a namedtuple of the data required by ODC for indexing.
    """
    bands = tuple(zip(product.measurements, image_data['bands']))
    _id = str(uuid.uuid5(uuid.NAMESPACE_URL, f'EEDAI:{product.name}/{image_data["name"]}'))
    creation_dt = image_data['startTime']
    affine_values = list(image_data['bands'][0]['grid']['affineTransform'].values())
    spatial_reference = image_data['bands'][0]['grid']\
                        .get('crsCode', image_data['bands'][0]['grid'].get('crsWkt'))
    polygon = polygon_from_transform(image_data['bands'][0]['grid']['dimensions']['width'],
                                     image_data['bands'][0]['grid']['dimensions']['height'],
                                     Affine(affine_values[0], 0, affine_values[1],
                                            affine_values[2], 0, affine_values[3]),
                                     spatial_reference)
    geo_ref_points = get_extents(polygon.boundingbox.points, spatial=True)

    # Handle special GEE Infinity GeoJSON responses
    if geometry_isfinite(image_data['geometry']):
        coord = get_extents(Geometry(image_data['geometry']).boundingbox.points)
    else:
        coord = dict(ul=dict(lon=-180.0, lat=90.0),
                     ur=dict(lon=180.0, lat=90.0),
                     ll=dict(lon=-180.0, lat=-90.0),
                     lr=dict(lon=180.0, lat=-90.0))

    metadata = Metadata(id=_id,
                        creation_dt=creation_dt,
                        product=product.name,
                        platform=product.metadata_doc['properties'].get('eo:platform'),
                        instrument=product.metadata_doc['properties'].get('eo:instrument'),
                        format='GeoTIFF',
                        from_dt=creation_dt,
                        to_dt=creation_dt,
                        center_dt=creation_dt,
                        coord=coord,
                        geo_ref_points=geo_ref_points,
                        spatial_reference=spatial_reference,
                        path=image_data['name'],
                        bands=bands)
    return metadata

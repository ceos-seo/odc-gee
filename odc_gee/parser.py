# pylint: disable=import-error
""" Parsing tools for metadata from Google Earth Engine API. """
from collections import namedtuple
from operator import itemgetter
import uuid

from datacube.utils.geometry import Geometry
from datacube.utils.geometry.tools import Affine

Metadata = namedtuple('Metadata', ','.join(['id',
                                            'product',
                                            'creation_dt',
                                            'format',
                                            'platform',
                                            'instrument',
                                            'from_dt',
                                            'to_dt',
                                            'center_dt',
                                            'asset',
                                            'geometry',
                                            'shapes',
                                            'transforms',
                                            'grids',
                                            'spatial_reference',
                                            'path',
                                            'bands',
                                            'extra_properties']))

def parse(asset, image_data, product):
    """ Parses the GEE metadata for ODC use.

    Args:
        asset (str): the asset ID of the product in the GEE catalog.
        image_data (dict): the image metadata to parse.
        product (datacube.model.DatasetType): the product information from the ODC index.

    Returns: a namedtuple of the data required by ODC for indexing.
    """
    image_data['bands'] = list(sorted(filter(lambda band: band['id'] in product.measurements.keys(),
                                             image_data['bands']), key=itemgetter('id')))
    bands = tuple(zip(sorted(product.measurements), image_data['bands']))
    _id = str(uuid.uuid5(uuid.NAMESPACE_URL, f'EEDAI:{product.name}/{image_data["name"]}'))
    creation_dt = image_data['startTime'] if image_data.get('startTime') else image_data['endTime']
    spatial_reference = image_data['bands'][0]['grid']\
                        .get('crsCode', image_data['bands'][0]['grid'].get('crsWkt'))
    # Handle special GEE Infinity GeoJSON responses
    image_data['geometry']['coordinates'][0] = [[float(x), float(y)]
                                                for (x, y) \
                                                in image_data['geometry']['coordinates'][0]]
    geometry = Geometry(image_data['geometry'])

    grids = [band['grid'] for band in image_data['bands']]
    grids_copy = grids.copy()
    grids = list(filter(lambda grid:
                        grids_copy.pop(grids_copy.index(grid)) \
                        not in grids_copy, grids))
    shapes = [[grid['dimensions']['height'], grid['dimensions']['width']] \
              for grid in grids]
    affine_values = [list(grid['affineTransform'].values()) \
                     for grid in grids]
    transforms = [list(Affine(affine_value[0], 0, affine_value[1],
                              affine_value[2], 0, affine_value[3]))\
                  for affine_value in affine_values]

    metadata = Metadata(id=_id,
                        product=product.name,
                        creation_dt=creation_dt,
                        format='GeoTIFF',
                        platform=product.metadata_doc['properties'].get('eo:platform'),
                        instrument=product.metadata_doc['properties'].get('eo:instrument'),
                        from_dt=creation_dt,
                        to_dt=creation_dt,
                        center_dt=creation_dt,
                        asset=asset,
                        geometry=geometry,
                        shapes=shapes,
                        transforms=transforms,
                        grids=grids,
                        spatial_reference=spatial_reference,
                        path=f'EEDAI:{image_data["name"]}:',
                        bands=bands,
                        extra_properties=image_data.get('properties'))
    return metadata

""" Parser for Landsat 8 metadata from GEE. """
import uuid
from odc_gee.indexing.parsers.utils import Metadata

BANDS = [('precipitation', 'precipitation'),
         ('relativeError', 'relativeError'),
         ('gaugeRelativeWeighting', 'gaugeRelativeWeighting')]

def parse(image_data, product=None):
    """
    Extract useful information to index to datacube from the scene based metadata
    :param mtl_data: metadata read from the MTL.txt
    :param bucket_name: AWS public bucket name
    :param object_key: Prefix to pass the particular path and row
    :return:
    """
    if product:
        _id = str(uuid.uuid5(uuid.NAMESPACE_URL, f'EEDAI:{product}/{image_data["name"]}'))
    else:
        _id = str(uuid.uuid5(uuid.NAMESPACE_URL, f'EEDAI:{image_data["name"]}'))
    creation_dt = image_data['startTime']
    coord = {'ul': {'lon': -180.0, 'lat': 40.0},
             'ur': {'lon': 180.0, 'lat': 40.0},
             'll': {'lon': -180.0, 'lat': -40.0},
             'lr': {'lon': 180.0, 'lat': -40.0}}
    geo_ref_points = {'ul': {'x': -180.0, 'y': 40.0},
                      'ur': {'x': 180.0, 'y': 40.0},
                      'll': {'x': -180.0, 'y': -40.0},
                      'lr': {'x': 180.0, 'y': -40.0}}
    spatial_reference = int(image_data['bands'][0]['grid']['crsCode'].split(':')[1])

    metadata = Metadata(id=_id,
                        creation_dt=creation_dt,
                        product_type='TRMM',
                        platform='TRMM',
                        instrument='TRMM',
                        format='GeoTIFF',
                        from_dt=creation_dt,
                        to_dt=creation_dt,
                        center_dt=creation_dt,
                        coord=coord,
                        geo_ref_points=geo_ref_points,
                        spatial_reference=spatial_reference,
                        path=image_data['name'],
                        bands=BANDS)
    return metadata
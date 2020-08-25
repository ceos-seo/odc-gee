""" Parses SRTM metadata from GEE. """
import uuid
from odc_gee.indexing.parsers.utils import Metadata

BANDS = [('elevation', 'elevation')]

def parse(image_data, product=None):
    """ Parser for SRTM data. """
    if product:
        _id = str(uuid.uuid5(uuid.NAMESPACE_URL, f'EEDAI:{product}/{image_data["name"]}'))
    else:
        _id = str(uuid.uuid5(uuid.NAMESPACE_URL, f'EEDAI:{image_data["name"]}'))
    creation_dt = image_data['startTime']
    coord = {'ul': {'lon': -180.0, 'lat': 90.0},
             'ur': {'lon': 180.0, 'lat': 90.0},
             'll': {'lon': -180.0, 'lat': -90.0},
             'lr': {'lon': 180.0, 'lat': -90.0}}
    geo_ref_points = {'ul': {'x': -180.0, 'y': 90.0},
                      'ur': {'x': 180.0, 'y': 90.0},
                      'll': {'x': -180.0, 'y': -90.0},
                      'lr': {'x': 180.0, 'y': -90.0}}
    spatial_reference = int(image_data['bands'][0]['grid']['crsCode'].split(':')[1])

    metadata = Metadata(id=_id,
                        creation_dt=creation_dt,
                        product_type='DEM',
                        platform='STS',
                        instrument='SRTM',
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

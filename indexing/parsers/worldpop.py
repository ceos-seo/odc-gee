""" Parser for Landsat 8 metadata from GEE. """
import uuid
from indexing.parsers.utils import METADATA, get_coords

BANDS = [('population', 'population')]

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
    coord = get_coords(image_data['geometry']['coordinates'][0], rot=False)
    geo_ref_points = get_coords(image_data['geometry']['coordinates'][0],
                                spatial=True, rot=False)
    spatial_reference = int(image_data['bands'][0]['grid']['crsCode'].split(':')[1])

    metadata = METADATA(id=_id,
                        creation_dt=creation_dt,
                        product_type='WORLDPOP',
                        platform='WORLDPOP',
                        instrument='WORLDPOP',
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

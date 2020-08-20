""" Parser for Landsat 8 metadata from GEE. """
import uuid
from indexing.parsers.utils import METADATA, get_coords, get_geo_ref_points

BANDS = [('B1', 'blue'),
         ('B2', 'green'),
         ('B3', 'red'),
         ('B4', 'nir'),
         ('B5', 'swir1'),
         ('B6', 'lwir'),
         ('B7', 'swir2'),
         ('sr_atmos_opacity', 'sr_atmos_opacity'),
         ('sr_cloud_qa', 'sr_cloud_qa'),
         ('pixel_qa', 'pixel_qa'),
         ('radsat_qa', 'radsat_qa')]

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
    coord = get_coords(image_data['geometry']['coordinates'][0])
    spatial_reference = int(image_data['bands'][0]['grid']['crsCode'].split(':')[1])

    metadata = METADATA(id=_id,
                        creation_dt=creation_dt,
                        product_type='LEDAPS',
                        platform='LANDSAT_7',
                        instrument='ETM',
                        format='GeoTIFF',
                        from_dt=creation_dt,
                        to_dt=creation_dt,
                        center_dt=creation_dt,
                        coord=coord,
                        geo_ref_points=get_geo_ref_points(coord, spatial_reference),
                        spatial_reference=spatial_reference,
                        path=image_data['name'],
                        bands=BANDS)
    return metadata

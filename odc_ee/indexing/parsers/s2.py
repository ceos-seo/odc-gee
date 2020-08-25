""" Parser for Sentinel-1 metadata from GEE. """
import uuid
from odc_ee.indexing.parsers.utils import Metadata, get_coords, get_geo_ref_points

BANDS = [('B1', 'aerosols'),
         ('B2', 'blue'),
         ('B3', 'green'),
         ('B4', 'red'),
         ('B5', 'red_edge_1'),
         ('B6', 'red_edge_2'),
         ('B7', 'red_edge_3'),
         ('B8', 'nir'),
         ('B8A', 'red_edge_4'),
         ('B9', 'water_vapor'),
         ('B11', 'swir1'),
         ('B12', 'swir2'),
         ('AOT', 'aot'),
         ('WVP', 'wvp'),
         ('SCL', 'scl'),
         ('TCI_R', 'tci_r'),
         ('TCI_G', 'tci_g'),
         ('TCI_B', 'tci_b'),
         ('QA60', 'qa60')]

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

    metadata = Metadata(id=_id,
                        creation_dt=creation_dt,
                        product_type='SR',
                        platform='SENTINEL-2',
                        instrument='MSI',
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

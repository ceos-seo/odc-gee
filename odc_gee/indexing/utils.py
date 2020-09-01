''' Indexes Google Earth Engine collections into Open Data Cube.

This module provides the necessary functions to index data into an ODC database.
It contains multiple helper methods and dataset document specifications for
different collections.
'''
from collections import namedtuple
import importlib

from tqdm import tqdm
import numpy as np
import pandas as pd

import datacube

IndexParams = namedtuple('IndexParams', 'asset product parser filters')

def add_dataset(doc, uri, index, sources_policy=None, update=None, **kwargs):
    ''' Add a dataset document to the index database.

    Args:
        doc: The dataset document.
        uri: Some URI to point to the document (this doesn't have to actually point anywhere).
        index: An instance of a datacube index.
        sources_policy (optional): The source policy to be checked.
        update: Update datasets if they already exist.

    Returns: The dataset to be indexed and any errors encountered.
    '''
    from datacube.index.hl import Doc2Dataset
    from datacube.utils import changes

    resolver = Doc2Dataset(index, **kwargs)
    dataset, err = resolver(doc, uri)
    if err is None:
        try:
            if update and index.datasets.get(dataset.id):
                index.datasets.update(dataset, {tuple(): changes.allow_any})
            else:
                index.datasets.add(dataset, sources_policy=sources_policy)
        except Exception as err:
            pass
    return dataset, err

# TODO: Change this to use EO3 for better compatibility with GEE metadata.
class MakeMetadataDoc:
    ''' A helper object to create the dataset document.

    Will help parse various metadata for GEE collections. Then it will
    create an ODC dataset metadata document. This document can then be
    used to index the GEE dataset as normal.

    Attributes:
        bands: A dictionary of the band maps for various products.
    '''

    def __init__(self, parser):
        try:
            self.parser = importlib.import_module(f'odc_gee.indexing.parsers.{parser}')
        except ImportError:
            print(f'Parser ({parser}) could not be imported.')

    def __call__(self, image_data, product=None):
        """
        Extract useful information to index to datacube from the scene based metadata
        :param mtl_data: metadata read from the MTL.txt
        :param bucket_name: AWS public bucket name
        :param object_key: Prefix to pass the particular path and row
        :return:
        """
        metadata = self.parser.parse(image_data, product=product)
        doc = {'id': metadata.id,
               'creation_dt': metadata.creation_dt,
               'product_type': metadata.product_type,
               'platform': {'code': metadata.platform},
               'instrument': {'name': metadata.instrument},
               'format': {'name': metadata.format},
               'extent': {
                   'from_dt': metadata.from_dt,
                   'to_dt': metadata.to_dt,
                   'center_dt': metadata.center_dt,
                   'coord': metadata.coord,
                   },
               'grid_spatial': {
                   'projection': {
                       'geo_ref_points': metadata.geo_ref_points,
                       'spatial_reference': 'EPSG:%d' % metadata.spatial_reference,
                       }
                   },
               'image': {
                   'bands': {
                       band[1]: {
                           'path': 'EEDAI:' + metadata.path + ':' + band[0],
                           'layer': 1,
                           } for band in metadata.bands
                       }
                   },
               'lineage': {'source_datasets': {}}}
        return doc

    def get_bands(self):
        """ Get the bands from the parser. """
        return self.parser.BANDS

def index_with_progress(years, *args, **kwargs):
    """Indexes with progress bar."""
    _sum = 0
    for year in tqdm(range(len(years)), desc='Yearly Progress'):
        _r = pd.date_range(f'{years[year]}-01-01',
                           f'{years[year]+1}-01-01', freq='1MS')
        for idx, date in tqdm(enumerate(_r[:-1]),
                              total=len(_r)-1,
                              desc=f'Progress for {years[year]}'):
            resp = None
            if idx < len(_r):
                args[1].update(startTime=f'{date.isoformat()}Z',
                               endTime=f'{_r[idx+1].isoformat()}Z')
            else:
                break
            resp, _sum = gee_indexer(response=resp, image_sum=_sum, *args, **kwargs)
    return resp, _sum

def gee_indexer(*args, update=False, response=None, image_sum=0):
    """Performs the parsing and indexing."""
    from odc_gee.earthengine import EarthEngine

    index_params = IndexParams(*args)

    try:
        _dc = datacube.Datacube(app='EE_Indexer')
    except RuntimeError:
        print('Could not connect to ODC.')
    try:
        _ee = EarthEngine()
    except RuntimeError:
        print('Could not connect to GEE.')
    try:
        parser = MakeMetadataDoc(index_params.parser)
    except NotImplementedError:
        print(f'Could not find parser: {index_params.parser}')
    if index_params.product is None\
       or not _dc.list_products().name.isin([index_params.product]).any():
        raise ValueError("Missing product.")

    required_bands = np.array(parser.get_bands())[..., 0]
    try:
        while(response is None or 'nextPageToken' in response.keys()):
            if response and 'nextPageToken' in response.keys():
                index_params.filters.update(pageToken=response['nextPageToken'])
                response = _ee.list_images(index_params.asset,
                                           _print=False, **index_params.filters).json()
                index_params.filters.pop('pageToken')
            else:
                response = _ee.list_images(index_params.asset,
                                           _print=False, **index_params.filters).json()
            if len(response) != 0:
                for image in response['images']:
                    bands = [band['id'] for band in image['bands']]
                    band_length = len(list(filter(lambda x: x in required_bands, bands)))
                    if  band_length == len(required_bands):
                        doc = parser(image, product=index_params.product)
                        add_dataset(doc, f'EEDAI:{image["name"]}',
                                    _dc.index, products=[index_params.product], update=update)
                image_sum = image_sum + len(response['images'])
    except RuntimeError as err:
        print(err)

    return response, image_sum

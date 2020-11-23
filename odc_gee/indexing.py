# pylint: disable=no-member,broad-except,import-error,unused-argument
''' Indexes Google Earth Engine collections into Open Data Cube.

This module provides the necessary functions to index data into an ODC database.
It contains multiple helper methods and dataset document specifications for
different collections.
'''
from collections import namedtuple
from contextlib import redirect_stderr
import io
import warnings

IndexParams = namedtuple('IndexParams', 'asset product filters')

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
    buff = io.StringIO()
    if err is None:
        with redirect_stderr(buff):
            if update and index.datasets.get(dataset.id):
                index.datasets.update(dataset, {tuple(): changes.allow_any})
            else:
                index.datasets.add(dataset, sources_policy=sources_policy)
        val = buff.getvalue()
        if val.count('is already in the database'):
            def warning_without_trace(message, *args, **kwargs):
                return f'{message}'
            warnings.formatwarning = warning_without_trace
            warnings.warn(val)
    else:
        raise ValueError(err)
    return dataset

def make_metadata_doc(*args, **kwargs):
    """ Makes the dataset document from the parsed metadata.

    Args:
        asset (str): the asset ID of the product in the GEE catalog.
        image_data (dict): the image metadata to parse.
        product (datacube.model.DatasetType): the product information from the ODC index.
    Returns: a dictionary of the dataset document.
    """
    from odc_gee.parser import parse
    metadata = parse(*args, **kwargs)
    doc = {'id': metadata.id,
           'creation_dt': metadata.creation_dt,
           'product': {'name': metadata.product},
           'properties': {'eo:platform': metadata.platform,
                          'eo:instrument': metadata.instrument,
                          'gee:asset': metadata.asset},
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
                   'spatial_reference': metadata.spatial_reference,
                   }
               },
           'image': {
               'bands': {
                   name: {
                       'path': metadata.path + band['id'],
                       'layer': 1,
                       } for (name, band) in metadata.bands
                   }
               },
           'lineage': {'source_datasets': {}}}
    return doc

def indexer(*args, update=False, response=None, image_sum=0):
    """ Performs the parsing and

    Args:
        asset (str): the asset identifier to index.
        product (str): the product name to index.
        filters (dict): API filters to use when searching for datasets to index.
        update (bool): will update existing datasets if set True.
        response: a Requests response from a previous API result.
        image_sum (int): the current sum of images indexed.
    Returns:
        A tuple of the Requests response from the API query
        and the recursive sum of datasets found.
    """
    from odc_gee import earthengine

    index_params = IndexParams(*args)

    datacube = earthengine.Datacube(app='EE_Indexer')

    if index_params.product is None\
       or not datacube.list_products().name.isin([index_params.product]).any():
        raise ValueError("Missing product.")

    product = datacube.index.products.get_by_name(index_params.product)
    product_bands = list(product.measurements.keys())

    for image in datacube.get_images(index_params.filters):
        bands = [band['id'] for band in image['bands']]
        band_length = len(list(filter(lambda x: x in product_bands, bands)))
        if band_length == len(product.measurements):
            doc = make_metadata_doc(image, product)
            add_dataset(doc, f'EEDAI:{image["name"]}',
                        datacube.index, products=[index_params.product], update=update)
        image_sum += 1
    return image_sum

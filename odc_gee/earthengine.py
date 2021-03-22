# pylint: disable=import-error,invalid-name,protected-access
""" Module for Google Earth Engine tools. """
from importlib import import_module
from pathlib import Path
import os

from rasterio.errors import RasterioIOError
import numpy

import datacube

HOME = os.getenv('HOME')
CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS',
                        f'{HOME}/.config/odc-gee/credentials.json')

class Datacube(datacube.Datacube):
    ''' Extended Datacube object for use with Google Earth Engine.

    Attributes:
        credentials: The Earth Engine credentials being used for the API session.
        request: The Request object used in the session.
        ee: A reference to the ee (earthengine-api) module.
    '''
    __instance = None
    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = object.__new__(cls, *args, **kwargs)
        return cls.__instance

    def __init__(self, *args, credentials=CREDENTIALS, **kwargs):
        self.ee = import_module('ee')
        self.request = None
        self.credentials = None
        if Path(credentials).exists():
            os.environ.update(GOOGLE_APPLICATION_CREDENTIALS=credentials)
            self.credentials = self.ee.ServiceAccountCredentials('', key_file=credentials)
            self.ee.Initialize(self.credentials)
        else:
            self.ee.Authenticate()
            self.ee.Initialize()
            self.credentials = self.ee.data.get_persistent_credentials()
            self.request = import_module('google.auth.transport.requests').Request()
            self._refresh_credentials()
        super().__init__(*args, **kwargs)

    def __del__(self):
        # Manually clean up sensitive info just in case
        if os.environ.get('EEDA_BEARER'):
            os.environ.pop('EEDA_BEARER')
        if self.request:
            self.request.session.close()
        self.request = None
        self.credentials = None

    def load(self, *args, **kwargs):
        ''' An overloaded load function from Datacube.

        This load method allows for querying the Earth Engine REST API to search for datasets
        instead of using the standard database query of datacube.Datacube.

        Args:
            asset (str): The asset ID of the GEE collection or image being queried. If not included
                then the load will default to normal Datacube operation.

        Returns: The queried xarray.Dataset.
        '''
        try:
            if kwargs.get('product') and not isinstance(kwargs.get('product'),
                                                        datacube.model.DatasetType):
                kwargs.update(product=self.index.products.get_by_name(kwargs['product']))
                kwargs.update(asset=kwargs.get('product').metadata_doc\
                                    .get('properties').get('gee:asset'))
            elif kwargs.get('asset'):
                kwargs.update(product=self.generate_product(**kwargs))

            if kwargs.get('asset'):
                parameters, kwargs = self.build_parameters(**kwargs)
                images = self.get_images(parameters)
                kwargs.update(datasets=get_datasets(images=images, **kwargs))
                kwargs.pop('asset')
                datasets = super().load(*args, **kwargs)
            else:
                return super().load(*args, **kwargs)
        except RasterioIOError as error:
            if error.args[0].find('"UNAUTHENTICATED"') != -1:
                if self._refresh_credentials():
                    return self.load(*args, **kwargs)
                raise error
        except Exception as error:
            raise error
        else:
            return datasets

    def _refresh_credentials(self):
        if self.request:
            self.credentials.refresh(self.request)
            os.environ.update(EEDA_BEARER=self.credentials.token)
            return True
        return False

    def get_images(self, parameters):
        ''' Gets the images or image from the GEE REST API.

        Args:
            parameters (dict): The parameters to use for the REST API query.

        Returns: The response from the API.
        '''
        try:
            request = self.ee.data._get_cloud_api_resource().projects().assets().listImages(
                **parameters)
            while request is not None:
                response = self.ee.data._execute_cloud_call(request)
                request = self.ee.data._cloud_api_resource.projects().assets().listImages_next(
                    request, response)
                for image in response.get('images', []):
                    yield image
                if 'pageSize' in parameters:
                    break
        except self.ee.EEException as error:
            if error.args[0].find('is not an image collection.') != -1:
                parameters = dict(name=parameters['parent'])
                request = self.ee.data._get_cloud_api_resource().projects().assets().get(
                    **parameters)
                response = self.ee.data._execute_cloud_call(request)
                yield response
        except Exception as error:
            raise error

    def build_parameters(self, query=None, **kwargs):
        ''' Build query parameters for GEE the REST API.

        Args:
            asset (str): The asset ID of the image or image collection.
            latitude (tuple/list): Optional; the latitude extents to search.
            longitude (tuple/list): Optional; the longitude extents to search.
            time (str/tuple/list): Optional; the time extent to search.
            query (dict): Optional; extra parameters to add to the query.

        Returns:
            If query is supplied, a tuple of a dict of built parameter and the original kwargs dict
            with the query removed. Otherwise, returns just the built paramseters.
        '''
        asset = kwargs['asset']
        parameters = dict(parent=self.ee.data.convert_asset_id_to_asset_name(asset))
        if kwargs.get('latitude') and kwargs.get('longitude'):
            parameters.update(
                region=self.ee.Geometry.Rectangle(coords=(kwargs['longitude'][0],
                                                          kwargs['latitude'][0],
                                                          kwargs['longitude'][1],
                                                          kwargs['latitude'][1])).getInfo())
        if kwargs.get('time'):
            if isinstance(kwargs['time'], (list, tuple)):
                parameters.update(startTime=numpy.datetime64(kwargs['time'][0])\
                              .item().strftime('%Y-%m-%dT%H:%M:%SZ'))
                parameters.update(endTime=numpy.datetime64(kwargs['time'][-1])\
                              .item().strftime('%Y-%m-%dT%H:%M:%SZ'))
            else:
                parameters.update(startTime=numpy.datetime64(kwargs['time'])\
                              .item().strftime('%Y-%m-%dT%H:%M:%SZ'))
        if query:
            parameters.update(**query)
            return parameters, kwargs
        return parameters, kwargs

    def generate_product(self, asset=None, name=None,
                         resolution=None, output_crs=None, **kwargs):
        ''' Generates an ODC product from GEE asset metadata.

        Args:
            asset (str): The asset ID of the GEE image or image collection.
            name (str): Optional; the product name.
            resolution (tuple): Optional; the desired output resolution of the product.
            output_crs (str): Optional; the desired CRS of the product.

        Returns: A datacube.model.DatasetType product.
        '''
        stac_metadata = self.get_stac_metadata(asset)
        metadata = self.ee.data.getAsset(asset)

        name = name if name else metadata.get('id').split('/')[-1]
        if kwargs.get('measurements') and not isinstance(kwargs['measurements'], (tuple, list)):
            measurements = kwargs['measurements']
        else:
            measurements = list(self.get_measurements(stac_metadata))
        definition = dict(name=name,
                          description=metadata.get('properties').get('description'),
                          metadata_type='eo3',
                          metadata=dict(product=dict(name=name),
                                        properties={'eo:platform':
                                                    stac_metadata['properties']\
                                                    .get('eo:platform',
                                                         stac_metadata['properties']\
                                                         .get('sar:platform')),
                                                    'eo:instrument':
                                                    stac_metadata['properties']\
                                                    .get('eo:instrument',
                                                         stac_metadata['properties']\
                                                         .get('sar:instrument')),
                                                    'gee:asset': asset}),
                          measurements=measurements)
        if resolution and output_crs:
            definition.update(storage=dict(crs=output_crs,
                                           resolution=dict(latitude=resolution[0],
                                                           longitude=resolution[1])))
        return self.index.products.from_doc(definition)

    def get_measurements(self, stac_metadata):
        ''' Gets the measurements of a product from the GEE metadata.

        Args:
            stac_metadata (dict): The STAC metadata from GEE for the desired product.

        Returns: A generated list of datacube.model.Measurement objects.
        '''
        try:
            band_types = self.ee.ImageCollection(stac_metadata['id']).first().bandTypes().getInfo()
        except self.ee.EEException as error:
            if error.args[0].find("found 'Image'") != -1:
                band_types = self.ee.Image(stac_metadata['id']).bandTypes().getInfo()
        except Exception as error:
            raise error
        for band in stac_metadata['properties'].get('eo:bands',
                                                    stac_metadata['properties'].get('sar:bands')):
            if 'empty' not in band['description'] and 'missing' not in band['description']:
                try:
                    band_type = get_type(band_types[band['name']])
                    measurement = dict(name=band['name'],
                                       units=band.get('gee:unit', ''),
                                       dtype=str(band_type.dtype),
                                       nodata=band_type.min,
                                       aliases=[to_snake(band['description']),
                                                to_snake(band['name'])])
                    if band.get('gee:bitmask'):
                        measurement.update(
                            flags_definition={to_snake(bitmask['description']):
                                              dict(dict(bits=list(
                                                  range(bitmask['first_bit'],
                                                        bitmask['first_bit'] \
                                                                + bitmask['bit_count'])),
                                                        desctiption=bitmask['description'],
                                                        values={value['value']:
                                                                to_snake(value['description'])
                                                                for value in bitmask['values']}))
                                              for bitmask in band['gee:bitmask']['bitmask_parts']})
                    if band.get('gee:classes'):
                        measurement.update(
                            flags_definition={to_snake(_class['description']):
                                              dict(bits=0,
                                                   description=_class['description'],
                                                   values={_class['value']: True})
                                              for _class in band['gee:classes']})
                    yield datacube.model.Measurement(**measurement)
                except KeyError:
                    pass
                except Exception as error:
                    raise error

    def get_stac_metadata(self, asset):
        ''' Gets STAC metadata of an asset in the GEE catalog.

        Args:
            asset (str): The asset ID.

        Returns: A dictionary of the metadata.
        '''
        url = f'gs://earthengine-stac/catalog/{asset.replace("/", "_")}.json'
        blob = self.ee.Blob(url)
        return self.ee.Dictionary(blob.string().decodeJSON()).getInfo()

def generate_documents(asset, images, product):
    ''' Generates Datacube dataset documents from GEE image data.

    Args:
        asset (str): The asset ID of the product in the GEE catalog.
        images (list): A list of image data from the GEE API.
        product (datacube.model.DatasetType): A product to associate datasets with.
    Returns: A generated list of datacube.model.Dataset objects.
    '''
    from datacube.index.hl import prep_eo3
    from odc_gee.indexing import make_metadata_doc
    for image in images:
        yield prep_eo3(make_metadata_doc(asset, image, product))

def get_type(band_type):
    ''' Gets the band unit type from GEE metadata.

    Args:
        band_type (dict): A GEE bandType metadata object.

    Returns: The data type of the band.
    '''
    types = [numpy.iinfo(numpy.dtype(f'int{2**i}')) for i in range(3, 7)]\
             + [numpy.iinfo(numpy.dtype(f'uint{2**i}')) for i in range(3, 7)]\
             + [numpy.finfo(numpy.dtype(f'float{2**i}')) for i in range(4, 8)]
    if band_type.get('min') is not None and band_type.get('max') is not None:
        return list(filter(lambda x: True if x.min == band_type['min']
                           and x.max == band_type['max'] else None, types))[0]
    return list(filter(lambda x: numpy.dtype(band_type['precision']) == x.dtype, types))[0]

def to_snake(string):
    ''' Cleans and formats strings from GEE metadata into snake case.

    Args:
        string (str): The string to clean and format.

    Returns: A cleaned string in snake case format.
    '''
    from re import sub, split
    return sub(r'[, -]+', '_',
               split(r'( \()|[.]', string)[0].replace('/', 'or').replace('&', 'and').lower())

def get_datasets(**kwargs):
    ''' Gets datasets for a Datacube load.

    Args:
        asset (str): The asset ID of the GEE asset.
        images (list): A list of image data from the GEE API.
        product (datacube.model.DatasetType): The product to associate dataset with.

    Returns: A generated list of datacube.model.Dataset objects.
    '''
    for document in generate_documents(kwargs['asset'], kwargs['images'], kwargs['product']):
        yield datacube.model.Dataset(kwargs['product'], document,
                                     uris=f'EEDAI://{kwargs["asset"]}')

# pylint: disable=import-error,invalid-name,protected-access
""" Module for Google Earth Engine tools. """
from datetime import datetime
from importlib import import_module
from pathlib import Path
import os
import threading
import weakref

import numpy

from datacube.api.query import Query
import datacube

# Number of days OAuth will keep token fresh
AUTH_LIMIT = 3

HOME = os.getenv('HOME')
CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS',
                        f'{HOME}/.config/odc-gee/credentials.json')

class Singleton(type):
    ''' A Singleton metaclass. '''
    __instance = None
    def __init__(cls, *args, **kwargs):
        super(Singleton, cls).__init__(*args, **kwargs)

    def __call__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super(Singleton, cls).__call__(*args, **kwargs)
        return cls.__instance

class Datacube(datacube.Datacube, metaclass=Singleton):
    ''' Extended Datacube object for use with Google Earth Engine.

    Attributes:
        credentials: The Earth Engine credentials being used for the API session.
        request: The Request object used in the session.
        ee: A reference to the ee (earthengine-api) module.
    '''
    def __init__(self, *args, **kwargs):
        self.ee = import_module('ee')
        self.request = import_module('google.auth.transport.requests').Request()
        if not hasattr(self, 'credentials'):
            self.credentials = kwargs.pop('credentials', CREDENTIALS)
        if isinstance(self.credentials, str) and Path(self.credentials).is_file():
            os.environ.update(GOOGLE_APPLICATION_CREDENTIALS=self.credentials)
            self.credentials = self.ee.ServiceAccountCredentials('',
                                                                 key_file=self.credentials)
            self.ee.Initialize(self.credentials)
        else:
            # TODO: Use this path to also determine JSON file location up top
            #       and also for possibly storing an EEDA_BEARER_FILE
            if not Path(self.ee.data.oauth.get_credentials_path()).exists():
                self.ee.Authenticate()
            self.ee.Initialize()
            self.credentials = self.ee.data.get_persistent_credentials()
        stop_event = threading.Event()
        creds_thread = threading.Thread(target=self._refresh_credentials, daemon=True,
                                        args=[stop_event])
        creds_thread.start()
        self._finalizer = weakref.finalize(self, cleanup, 'EEDA_BEARER', self.request, stop_event)
        super().__init__(*args, **kwargs)

    def remove(self):
        ''' Finalizer to cleanup sensitive data. '''
        self._finalizer()

    @property
    def removed(self):
        ''' Property to check if object has been finalized. '''
        return not self._finalizer.alive


    def load(self, datasets=None, **kwargs):
        ''' An overloaded load function from Datacube.

        This load method allows for querying the Earth Engine REST API to search for datasets
        instead of using the standard database query of datacube.Datacube.

        Returns: The queried xarray.Dataset.
        '''
        datasets = datasets if datasets else self.find_datasets(**kwargs)
        return super().load(datasets=datasets, **kwargs)

    def _refresh_credentials(self, stop_event):
        expiration = (numpy.datetime64(datetime.utcnow(), 'D') + AUTH_LIMIT).item()
        # Need to run once before the wait
        if not self.credentials.expiry:
            self.credentials.refresh(self.request)
            os.environ.update(EEDA_BEARER=self.credentials.token)
        time_delta = self.credentials.expiry - datetime.utcnow()
        while not stop_event.wait(time_delta.seconds - 60):
            if expiration.today() == expiration:
                stop_event.set()
            self.credentials.refresh(self.request)
            os.environ.update(EEDA_BEARER=self.credentials.token)
            time_delta = self.credentials.expiry - datetime.utcnow()

    def find_datasets(self, limit=None, **search_terms):
        ''' Finds datasets matching the search terms in local index or in GEE catalog.

        Args:
            limit (int): Optional; limit the maximum datasets returned
            search_terms (dict): Search parameters to be passed to datacube.api.query.Query

        Returns: A generated list of datacube.model.Dataset objects.
        '''
        query = Query(**search_terms)
        if query.product and not isinstance(query.product,
                                            datacube.model.DatasetType):
            query.product = self.index.products.get_by_name(query.product)
            query.asset = query.product.metadata_doc.get('properties').get('gee:asset')
        elif search_terms.get('asset'):
            query.product = self.generate_product(**search_terms)
            query.asset = search_terms.pop('asset')

        product_measurements = query.product.measurements.keys()
        if hasattr(query, 'asset'):
            images = self.get_images(self.build_parameters(query))
            for document in generate_documents(query.asset, images, query.product):
                if limit != 0:
                    limit = limit - 1 if limit is not None else limit
                    if set(product_measurements) == set(document['measurements'].keys()):
                        yield datacube.model.Dataset(query.product, document,
                                                     uris=f'EEDAI://{query.asset}')
                else:
                    break
        else:
            for dataset in super().find_datasets(limit=limit, search_terms=search_terms):
                yield dataset

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

    def build_parameters(self, query):
        ''' Build query parameters for GEE REST API from ODC queries.

        Args:
            query (datacube.api.query.Query): An ODC query object with additional GEE attributes.

        Returns:
            A formatted dictionary for a GEE query.
        '''
        parameters = dict(parent=self.ee.data.convert_asset_id_to_asset_name(query.asset))
        if query.geopolygon:
            if query.geopolygon.type == 'Polygon':
                parameters.update(
                    region=self.ee.Geometry.Rectangle(
                        coords=list(query.geopolygon.boundingbox)).getInfo())
            elif query.geopolygon.type == 'Point':
                parameters.update(
                    region=self.ee.Geometry.Point(
                        coords=list(query.geopolygon.boundingbox)[0:2]).getInfo())
        if 'time' in query.search:
            parameters.update(startTime=query.search['time'].begin.strftime('%Y-%m-%dT%H:%M:%SZ'))
            parameters.update(endTime=query.search['time'].end.strftime('%Y-%m-%dT%H:%M:%SZ'))
        if 'query' in query.search:
            parameters.update(**query.search['query'])
        return parameters

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
        # TODO: find new method for platform and instrument property
        definition = dict(name=name,
                          description=metadata.get('properties').get('description'),
                          metadata_type='eo3',
                          metadata=dict(product=dict(name=name),
                                        properties={'eo:platform': None,
                                                    'eo:instrument': None,
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
        for band in stac_metadata['summaries'].get('eo:bands',
                                                   stac_metadata['summaries'].get('sar:bands')):
            if 'empty' not in band['description'] and 'missing' not in band['description']:
                try:
                    band_type = get_type(band_types[band['name']])
                    measurement = dict(name=band['name'],
                                       units=band.get('gee:unit', band.get('gee:units', '')),
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

def cleanup(key, request, stop_event):
    ''' Method to cleanup any leftover sensitive data.

    Args:
        key (str): The name of an environment key to remove.
        request (Request): A request object to have session closed.
        stop_event (threading.Event): An event to tell threads to stop.
    '''
    stop_event.set()
    if os.environ.get(key):
        os.environ.pop(key)
    if request:
        request.session.close()

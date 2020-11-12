# pylint: disable=import-error,dangerous-default-value,invalid-name,protected-access
""" Module for Google Earth Engine tools. """
from pathlib import Path
import os

from google.auth.transport.requests import Request
import ee
import numpy

from rasterio.errors import RasterioIOError
import datacube

SCOPES = ['https://www.googleapis.com/auth/earthengine',
          'https://www.googleapis.com/auth/cloud-platform']
HOME = os.getenv('HOME')

class Datacube(datacube.Datacube):
    def __init__(self, *args,
                 credentials=os.getenv('GOOGLE_APPLICATION_CREDENTIALS',
                                       f'{HOME}/.config/odc-gee/credentials.json'),
                 **kwargs):
        if Path(credentials).exists():
            self.credentials = ee.ServiceAccountCredentials('', key_file=credentials)
            ee.Initialize(self.credentials)
        else:
            ee.Authenticate()
            ee.Initialize()
            self.credentials = ee.data.get_persistent_credentials()
            self.request = Request()
            self._refresh_credentials()
        self.ee = ee
        super().__init__(*args, **kwargs)

    def load(self, *args, **kwargs):
        if kwargs.get('asset'):
            params, kwargs = self.build_parameters(**kwargs)
            try:
                images = self.get_images(params)
                if kwargs.get('product') and not isinstance(kwargs.get('product'),
                                                            datacube.model.DatasetType):
                    kwargs.update(product=self.index.products.get_by_name(kwargs['product']))
                else:
                    kwargs.update(product=self.generate_product(**kwargs))
                kwargs.update(datasets=get_datasets(images, **kwargs))
                kwargs.pop('asset')
                datasets = super().load(*args, **kwargs)
            except RasterioIOError as error:
                if error.args[0].find('"UNAUTHENTICATED"') != -1:
                    self._refresh_credentials()
                    return self.load(*args, **kwargs)
            except Exception as error:
                raise error
            else:
                return datasets
        else:
            return super().load(*args, **kwargs)

    def _refresh_credentials(self):
        self.credentials.refresh(self.request)
        os.environ.update(EEDA_BEARER=self.credentials.token)
        return True

    def get_images(self, params):
        self.ee.data._cloudApiOnly('listImages')
        request = self.ee.data._get_cloud_api_resource().projects().assets().listImages(**params)
        while request is not None:
            response = self.ee.data._execute_cloud_call(request)
            request = self.ee.data._cloud_api_resource.projects().assets().listImages_next(
                request, response)
            for image in response.get('images', []):
                yield image
            if 'pageSize' in params:
                break

    def build_parameters(self, **kwargs):
        params = dict(parent=self.ee.data.convert_asset_id_to_asset_name(kwargs['asset']))
        if kwargs.get('latitude') and kwargs.get('longitude'):
            params.update(region=ee.Geometry.Rectangle(coords=(kwargs['longitude'][0],
                                                               kwargs['latitude'][0],
                                                               kwargs['longitude'][1],
                                                               kwargs['latitude'][1])).getInfo())
        if kwargs.get('time'):
            if isinstance(kwargs['time'], (list, tuple)):
                params.update(startTime=numpy.datetime64(kwargs['time'][0])\
                              .item().strftime('%Y-%m-%dT%H:%M:%SZ'))
                params.update(endTime=numpy.datetime64(kwargs['time'][-1])\
                              .item().strftime('%Y-%m-%dT%H:%M:%SZ'))
            else:
                params.update(startTime=numpy.datetime64(kwargs['time'])\
                              .item().strftime('%Y-%m-%dT%H:%M:%SZ'))
        if kwargs.get('query'):
            params.update(**kwargs['query'])
            kwargs.pop('query')
        return params, kwargs

    def generate_product(self, **kwargs):
        stac_metadata = self.get_stac_metadata(kwargs['asset'])
        metadata = self.ee.data.getAsset(kwargs['asset'])

        name = kwargs.get('name', metadata.get('id').split('/')[-1])
        if kwargs.get('measurements') and not isinstance(kwargs['measurements'], (tuple, list)):
            measurements = kwargs['measurements']
        else:
            measurements = list(self.get_measurements(stac_metadata))
        definition = dict(name=name,
                          description=metadata.get('properties').get('description'),
                          metadata_type='eo',
                          metadata=dict(product=dict(name=name),
                                        properties={'eo:platform':
                                                    stac_metadata['properties']\
                                                    .get('eo:platform'),
                                                    'eo:instrument':
                                                    stac_metadata['properties']\
                                                    .get('eo:instrument')}),
                          measurements=measurements)
        if kwargs.get('resolution') and kwargs.get('output_crs'):
            definition.update(storage=dict(crs=kwargs['output_crs'],
                                           resolution=dict(latitude=kwargs['resolution'][0],
                                                           longitude=kwargs['resolution'][1])))
        return self.index.products.from_doc(definition)

    def get_measurements(self, metadata):
        band_types = ee.ImageCollection(metadata['id']).first().bandTypes().getInfo()
        for band in metadata['properties']['eo:bands']:
            if 'empty' not in band['description'] and 'missing' not in band['description']:
                band_type = get_type(band_types[band['name']])
                measurement = dict(name=to_snake(band['description']),
                                   units=band.get('gee:unit', ''),
                                   dtype=str(band_type.dtype),
                                   nodata=band_type.min,
                                   aliases=[band['name']])
                if band.get('gee:bitmask'):
                    measurement.update(
                        flags_definition={to_snake(bitmask['description']):
                                          dict(dict(bits=bitmask['first_bit'],
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

    def get_stac_metadata(self, asset):
        url = f'gs://earthengine-stac/catalog/{asset.replace("/", "_")}.json'
        blob = self.ee.Blob(url)
        return self.ee.Dictionary(blob.string().decodeJSON()).getInfo()

def generate_documents(images, product):
    from odc_gee.indexing import make_metadata_doc
    for image in images:
        yield make_metadata_doc(image, product)

def get_type(band_type):
    types = [numpy.iinfo(numpy.dtype(f'int{2**i}')) for i in range(3, 7)]\
             + [numpy.iinfo(numpy.dtype(f'uint{2**i}')) for i in range(3, 7)]\
             + [numpy.finfo(numpy.dtype(f'float{2**i}')) for i in range(4, 8)]
    return list(filter(lambda x: True if x.min == band_type['min']
                       and x.max == band_type['max'] else None, types))[0]

def to_snake(string):
    from re import sub, split
    return sub(r'[, ]+', '_',
               split(r'( \()|[.]', string)[0].replace('/', 'or').replace('&', 'and').lower())

def get_datasets(images, **kwargs):
    for document in generate_documents(images, kwargs['product']):
        yield datacube.model.Dataset(kwargs['product'], document,
                                     uris=f'EEDAI://{kwargs.get("asset")}')

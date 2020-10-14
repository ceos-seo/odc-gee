# pylint: disable=import-error,dangerous-default-value,invalid-name
""" Module for Google Earth Engine tools. """
from datetime import datetime
from pprint import pprint
import io
import json
import os

from IPython.display import Image
from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account
import googleapiclient.discovery
import numpy

SCOPES = ['https://www.googleapis.com/auth/earthengine',
          'https://www.googleapis.com/auth/cloud-platform']
API_KEY = os.getenv('EE_API_KEY', None)
if not API_KEY:
    raise EnvironmentError('EE_API_KEY environment variable undefined.')
HOME = os.getenv('HOME')

def to_geojson(latitude, longitude):
    """ Creates a GeoJSON dictionary.

    Args:
        latitude (str)
        longitude (str)
    Returns:
        A dictionary of the GeoJSON.
    """
    return dict(type="Polygon",
                coordinates=[[[longitude[0],
                               latitude[0]],
                              [longitude[1],
                               latitude[0]],
                              [longitude[1],
                               latitude[1]],
                              [longitude[0],
                               latitude[1]],
                              [longitude[0],
                               latitude[0]]]])

class EarthEngine:
    """ An instance for interfacing with the Earth Engine REST API.

    Attrs:
        credentials (str): the location of the service account credentials for the API.
        earthengine (googleapiclient.discovery.Resource): the API interface.
        session (google.auth.transport.requests.AuthorizedSession):
            a requests session class with credentials.
        project (str): the project name to access in Earth Engine.
    """
    def __init__(self,
                 project='earthengine-public',
                 credentials=os.getenv('GOOGLE_APPLICATION_CREDENTIALS',
                                       f'{HOME}/.config/odc-gee/credentials.json')):
        self.credentials = service_account.Credentials.from_service_account_file(
            credentials, scopes=SCOPES)
        self.earthengine = googleapiclient.discovery.build(
            'earthengine', 'v1alpha', credentials=self.credentials, developerKey=API_KEY,
            cache_discovery=False)

        scoped_credentials = self.credentials.with_scopes(SCOPES)
        self.session = AuthorizedSession(scoped_credentials)
        self.project = 'projects/{}'.format(project)

    def get(self, asset_id, **kwargs):
        """ Gets detailed information about an asset.

        Args:
            asset_id (str): the asset identifier to get.
            print (bool): will print the asset information if True.
        Returns: the Requests response for the API query.
        """
        _print = kwargs.pop('print') if kwargs.get('print') else False
        name = '{}/assets/{}'.format(self.project, asset_id)
        url = self.earthengine.projects().assets().get(name=name).uri
        response = self.session.get(url)
        if not response.ok:
            raise ValueError(response.json().get('error').get('message'))

        if _print:
            pprint(json.loads(response.content))
        return response

    def list_images(self, asset_id, **kwargs):
        """ Lists the images in an image collection asset.

        Args:
            asset_id (str): the asset identifier for the collection.
            print (bool): will print the asset information if True.
        Optional Arguments: extra arguments will be passed to the API query.
        Returns: the Requests response for the API query.
        """
        _print = kwargs.pop('print') if kwargs.get('print') else False
        name = '{}/assets/{}'.format(self.project, asset_id)
        url = self.earthengine.projects().assets().listImages(parent=name, **kwargs).uri
        response = self.session.get(url)
        if not response.ok:
            raise ValueError(response.json().get('error').get('message'))

        if _print:
            pprint(json.loads(response.content))
        return response

    def get_pixels(self, asset_id, **kwargs):
        """ Fetches pixels from an image asset.

        Args:
            asset_id (str): the asset identifier for the image.
            print (bool): will
        Optional Arguments: extra arguments will be passed to the API query.
        Returns: the image array.
        """
        _print = kwargs.pop('print') if kwargs.get('print') else False
        name = '{}/assets/{}'.format(self.project, asset_id)
        body = json.dumps(kwargs)
        url = self.earthengine.projects().assets().getPixels(name=name).uri

        pixels_response = self.session.post(url, body)
        if not pixels_response.ok:
            raise ValueError(pixels_response.json().get('error').get('message'))
        pixels_content = pixels_response.content

        if _print:
            array = numpy.load(io.BytesIO(pixels_content))
            print('Shape: %s' % (array.shape, ))
            print('Data:')
            print(array)
        return array

    def get_image(self, asset_id, fileFormat='PNG', bandIds=['B4', 'B3', 'B2'],
                  grid={'dimensions':{'width':256, 'height':256}}, **kwargs):
        """ Gets an image using the getPixels API query.

        Args:
            asset_id (str): the asset identifier of the image to fetch.
            fileFormat (str): the format of the file.
                default: 'PNG'
            bandIds (list): a list of IDs for the bands to get.
                default: ['B1', 'B3', 'B2']
            grid (dict): the grid dimensions of the image.
                default: {'dimensions': {'width': 256, 'height': 256}}
            print (bool): will print the image using Ipython.
        Returns: the image content.
        """
        _print = kwargs.pop('print') if kwargs.get('print') else False
        url = self.earthengine.projects().assets()\
              .getPixels(name=f'{self.project}/assets/{asset_id}').uri
        asset = json.loads(self.get(asset_id).content)
        kwargs['bandIds'] = bandIds
        kwargs['grid'] = grid
        kwargs['fileFormat'] = fileFormat
        kwargs.update(region=kwargs.get('region', asset['geometry']))
        body = json.dumps(kwargs)

        image_response = self.session.post(url, body)
        if not image_response.ok:
            raise ValueError(image_response.json().get('error').get('message'))
        image_content = image_response.content

        timestamp = str(datetime.now().timestamp()).split('.')[0]
        fname = './images/{asset_id}-{timestamp}.{ftype}'.format(
            asset_id=asset_id.replace('/', '-'),
            timestamp=timestamp,
            ftype='tiff' if fileFormat == 'GEO_TIFF' else fileFormat.lower())
        with open(fname, 'wb') as _file:
            _file.write(image_content)

        print(fname)
        if _print:
            return Image(image_content)
        return image_content

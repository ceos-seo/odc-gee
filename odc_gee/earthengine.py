# pylint: disable=import-error
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
API_KEY = os.getenv('EE_API_KEY')

def to_geojson(latitude, longitude):
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
    def __init__(self,
                 project='earthengine-public',
                 credentials=os.getenv('GOOGLE_APPLICATION_CREDENTIALS')):
        self.credentials = service_account.Credentials.from_service_account_file(
            credentials, scopes=SCOPES)
        self.earthengine = googleapiclient.discovery.build(
            'earthengine', 'v1alpha', credentials=self.credentials, developerKey=API_KEY,
            cache_discovery=False)

        scoped_credentials = self.credentials.with_scopes(SCOPES)
        self.session = AuthorizedSession(scoped_credentials)
        self.project = 'projects/{}'.format(project)

    def get(self, asset_id, **kwargs):
        name = '{}/assets/{}'.format(self.project, asset_id)
        url = self.earthengine.projects().assets().get(name=name).uri
        response = self.session.get(url)

        if kwargs.get('print'):
            pprint(json.loads(response.content))
        return response

    def list_images(self, asset_id, **kwargs):
        name = '{}/assets/{}'.format(self.project, asset_id)
        url = self.earthengine.projects().assets().listImages(parent=name, **kwargs).uri
        response = self.session.get(url)

        if kwargs.get('print'):
            pprint(json.loads(response.content))
        return response

    def get_pixels(self, asset_id, **kwargs):
        name = '{}/assets/{}'.format(self.project, asset_id)
        body = json.dumps(kwargs)
        url = self.earthengine.projects().assets().getPixels(name=name).uri

        pixels_response = self.session.post(url, body)
        pixels_content = pixels_response.content

        if kwargs.get('print'):
            array = numpy.load(io.BytesIO(pixels_content))
            print('Shape: %s' % (array.shape, ))
            print('Data:')
            print(array)
        return array

    def get_image(self, asset_id, fileFormat='PNG', bandIds=['B4', 'B3', 'B2'],
                  grid={'dimensions':{'width':256, 'height':256}}, **kwargs):
        name = '{}/assets/{}'.format(self.project, asset_id)
        url = self.earthengine.projects().assets().getPixels(name=name).uri
        asset = json.loads(self.get(asset_id).content)
        kwargs['bandIds'] = bandIds
        kwargs['grid'] = grid
        kwargs['fileFormat'] = fileFormat
        kwargs.update(region=kwargs.get('region', asset['geometry']))
        body = json.dumps(kwargs)

        image_response = self.session.post(url, body)
        image_content = image_response.content

        timestamp = str(datetime.now().timestamp()).split('.')[0]
        fname = './images/{asset_id}-{timestamp}.{ftype}'.format(
            asset_id=asset_id.replace('/', '-'),
            timestamp=timestamp,
            ftype='tiff' if fileFormat == 'GEO_TIFF' else fileFormat.lower())
        with open(fname, 'wb') as _file:
            _file.write(image_content)

        print(fname)
        if kwargs.get('print'):
            return Image(image_content)
        return image_content

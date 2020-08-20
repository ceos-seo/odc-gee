from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account
import googleapiclient.discovery
from pprint import pprint
import json
import numpy
import io
from datetime import datetime
from IPython.display import Image
import os

SCOPES = ['https://www.googleapis.com/auth/earthengine',
          'https://www.googleapis.com/auth/cloud-platform']
API_KEY = os.getenv('EE_API_KEY')

class EarthEngine:
    def __init__(self,
                 project='earthengine-public',
                 credentials=os.getenv('GOOGLE_APPLICATION_CREDENTIALS')):
        self.credentials = service_account.Credentials.from_service_account_file(
                credentials, scopes=SCOPES)
        self.ee = googleapiclient.discovery.build(
                'earthengine', 'v1alpha', credentials=self.credentials, developerKey=API_KEY,
                cache_discovery=False)

        scoped_credentials = self.credentials.with_scopes(SCOPES)
        self.session = AuthorizedSession(scoped_credentials)
        self.project = 'projects/{}'.format(project)

    def get(self, asset_id, _print=True):
        name = '{}/assets/{}'.format(self.project, asset_id)
        url = self.ee.projects().assets().get(name=name).uri
        response = self.session.get(url)

        if _print: pprint(json.loads(response.content))
        return response

    def list_images(self, asset_id, _print=True, **kwargs):
        name = '{}/assets/{}'.format(self.project, asset_id)
        url = self.ee.projects().assets().listImages(parent=name, **kwargs).uri
        response = self.session.get(url)

        if _print: pprint(json.loads(response.content))
        return response

    def get_pixels(self, asset_id, _print=True, **kwargs):
        name = '{}/assets/{}'.format(self.project, asset_id)
        body = json.dumps(kwargs)
        url = self.ee.projects().assets().getPixels(name=name).uri

        pixels_response = self.session.post(url, body)
        pixels_content = pixels_response.content

        if _print:
            array = numpy.load(io.BytesIO(pixels_content))
            print('Shape: %s' % (array.shape, ))
            print('Data:')
            print(array)
        return array

    def get_image(self, asset_id, _print=True, fileFormat='PNG', bandIds=['B4', 'B3', 'B2'],
            grid={'dimensions':{'width':256,'height':256}}, region=False, **kwargs):
        name = '{}/assets/{}'.format(self.project, asset_id)
        url = self.ee.projects().assets().getPixels(name=name).uri
        asset = json.loads(self.get(asset_id, _print=False).content)
        kwargs['bandIds'] = bandIds
        kwargs['grid'] = grid
        kwargs['fileFormat'] = fileFormat
        kwargs['region'] = region if region else asset['geometry']
        body = json.dumps(kwargs)

        image_response = self.session.post(url, body)
        image_content = image_response.content

        timestamp = str(datetime.now().timestamp()).split('.')[0]
        fname = './images/{asset_id}-{timestamp}.{ftype}'.format(
                asset_id=asset_id.replace('/', '-'),
                timestamp=timestamp,
                ftype='tiff' if fileFormat == 'GEO_TIFF' else fileFormat.lower())
        with open(fname,'wb') as f:
            f.write(image_content)

        print(fname)
        if _print: return Image(image_content)

    def to_geojson(self, latitude, longitude):
        region = {
            "type": "Polygon",
            "coordinates": [
                [
                    [
                        longitude[0],
                        latitude[0]

                    ],
                    [
                        longitude[1],
                        latitude[0]

                    ],
                    [
                        longitude[1],
                        latitude[1]
                    ],
                    [
                        longitude[0],
                        latitude[1]
                    ],
                    [
                        longitude[0],
                        latitude[0]
                    ]
                ]
            ]
        }

        return region

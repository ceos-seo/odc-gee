import os
import unittest
from pathlib import Path

from odc_gee import earthengine

DATACUBE_CONFIG = f'{Path(__file__).parent.parent.absolute()}/datacube.conf'
HOME = os.getenv('HOME')
CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS',
                        f'{HOME}/.config/odc-gee/credentials.json')

class DatacubeTestCase(unittest.TestCase):
    def test_init(self):
        datacube = earthengine.Datacube(config=DATACUBE_CONFIG, credentials=CREDENTIALS)
        os.environ.update(EEDA_BEARER='foobar')
        self.assertIsInstance(datacube, earthengine.Datacube,
                              'Cannot init earthengine.Datacube')
        return datacube

    def test_singleton(self):
        dc1 = self.test_init()
        dc2 = self.test_init()
        self.assertEqual(id(dc1), id(dc2),
                         'There can only be one earthengine.Datacube instance')

    def test_destruction(self):
        self.assertNotIn('EEDA_BEARER', os.environ,
                         'Credentials not being removed from environment')


if __name__ == '__main__':
    unittest.main()

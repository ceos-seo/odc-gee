import os
import unittest

from odc_gee import earthengine

HOME = os.getenv('HOME')
CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS',
                        f'{HOME}/.config/odc-gee/credentials.json')

class DatacubeTestCase(unittest.TestCase):
    def test_init(self):
        dc = earthengine.Datacube(credentials=CREDENTIALS)
        os.environ.update(EEDA_BEARER='foobar')
        self.assertIsInstance(dc, earthengine.Datacube,
                              'Cannot init earthengine.Datacube')

    def test_singleton(self):
        dc1 = earthengine.Datacube(credentials=CREDENTIALS)
        dc2 = earthengine.Datacube(credentials=CREDENTIALS)
        self.assertEqual(id(dc1), id(dc2),
                         'There can only be one earthengine.Datacube instance')

    def test_destruction(self):
        self.assertNotIn('EEDA_BEARER', os.environ,
                         'Credentials not being removed from environment')


if __name__ == '__main__':
    unittest.main()

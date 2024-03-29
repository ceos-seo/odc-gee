from pathlib import Path
import subprocess
import unittest

from tests.odc_gee.test_indexing import IndexerTestCase

from datacube import Datacube

DATACUBE_CONFIG = f'{Path(__file__).parent.parent.absolute()}/datacube.conf'
TEST_FILE = f'{Path(__file__).parent.absolute()}/ls8_test.yaml'

class IndexGEETestCase(unittest.TestCase):
    def setUp(self):
        self.datacube = Datacube(config=DATACUBE_CONFIG)

        IndexerTestCase().test_product_generation()
        product = self.datacube.index.products.get_by_name('ls8_test')
        if product is None:
            self.skipTest('No product available to index')
        datasets = self.datacube.find_datasets(product='ls8_test')
        if datasets:
            self.skipTest('Indexed datasets already exist in database')

    def test_index_gee(self):
        product = 'ls8_test'
        latitude = (-4.15, -3.90)
        longitude = (39.50, 39.75)
        time = '2020-01'

        cmd = ["index_gee", "--product", product, "--latitude", str(latitude),
               "--longitude", str(longitude), "--time", time,
               "--config", DATACUBE_CONFIG, "--no_confirm", "-u"]
        subprocess.check_output(cmd)
        datasets = self.datacube.find_datasets(product=product)
        self.assertGreater(len(datasets), 0,
                           'Expected to find datasets in index')

if __name__ == '__main__':
    unittest.main()

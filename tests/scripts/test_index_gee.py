from os import remove
from pathlib import Path
from tempfile import gettempdir
import filecmp
import subprocess
import unittest

TEST_FILE = f'{Path(__file__).parent.absolute()}/ls8_test.yaml'

class IndexGEETestCase(unittest.TestCase):
    # TODO: finish this test
    def test_index_gee(self):
        #cmd = ["index_gee", "--product", "ls8_test", "
        pass

if __name__ == '__main__':
    unittest.main()

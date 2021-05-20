import unittest
import click

@click.command()
@click.option('--start_dir', '-s', required=False, type=click.STRING, default='tests',
              help='The directory to discover tests inside [default: tests]')
@click.option('--top_level_dir', '-t', required=False, type=click.STRING, default='.',
              help='The root directory of the project being tested [default: .]')
def main(**kwargs):
    start_dir = kwargs['start_dir']
    top_level_dir = kwargs['top_level_dir']

    def suite():
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        suite.addTests(loader.discover(start_dir, top_level_dir=top_level_dir))
        return suite

    runner = unittest.TextTestRunner()
    runner.run(suite())

if __name__ == '__main__':
    main()

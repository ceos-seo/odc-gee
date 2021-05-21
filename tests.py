#!/usr/bin/env python
from pathlib import Path
import subprocess
import unittest
import click

from datacube import Datacube

DATACUBE_CONFIG = f'{Path(__file__).parent.absolute()}/tests/datacube.conf'

@click.group(invoke_without_command=True)
@click.pass_context
def tests(ctx):
    if ctx.invoked_subcommand is None:
        run()

@tests.command()
@click.option('--start_dir', '-s', required=False, type=click.STRING, default='tests',
              help='The directory to discover tests inside [default: tests]')
@click.option('--top_level_dir', '-t', required=False, type=click.STRING, default='.',
              help='The root directory of the project being tested [default: .]')
@click.option('-v', '--verbose', count=True, default=0)
def run(**kwargs):
    try:
        datacube = Datacube(config=DATACUBE_CONFIG)
    except:
        raise RuntimeError('Could not connect to the test database.\n'\
                           'Make sure to run: python tests.py initdb')

    start_dir = kwargs['start_dir']
    top_level_dir = kwargs['top_level_dir']

    def suite():
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        suite.addTests(loader.discover(start_dir, top_level_dir=top_level_dir))
        return suite

    runner = unittest.TextTestRunner(verbosity=kwargs['verbose']+1)
    runner.run(suite())

@tests.command()
def initdb():
    try:
        createdb = ["createdb", "dctest"]
        odc_init = ["datacube", "-C", DATACUBE_CONFIG, "system", "init"]
        subprocess.check_output(createdb)
        subprocess.check_output(odc_init)
    except subprocess.CalledProcessError:
        datacube = Datacube(config=DATACUBE_CONFIG)
        if datacube is not None:
            print('Database already initialized')
    except Exception as error:
        raise error

@tests.command()
def dropdb():
    try:
        dropdb = ["dropdb", "dctest"]
        subprocess.check_output(dropdb)
    except subprocess.CalledProcessError as error:
        try:
            datacube = Datacube(config=DATACUBE_CONFIG)
            if datacube is not None:
                raise error
        except Exception:
            print('Already dropped the database')
    except Exception as error:
        raise error

if __name__ == '__main__':
    tests()

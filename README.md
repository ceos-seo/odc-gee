# ODC-GEE

## About
This package provides various tools for indexing [Google Earth Engine
(GEE)](https://earthengine.google.com/)
images into an [Open Data Cube
(ODC)](https://datacube-core.readthedocs.io/en/latest/index.html) index.  It
takes advantage of the [GEE REST
API](https://developers.google.com/earth-engine/reference).

## Installation
The package can be installed using Python setuptools:
`python setup.py build && python setup.py install`

Alternatively:
`pip install -e odc_gee`

## Configuration
The scripts and python modules in this package use the following environment
variables:

* `DATACUBE_CONFIG_PATH`: Optional; the ODC configuration file.
* `GOOGLE_APPLICATION_CREDENTIALS`: Optional; the service account credentials
  JSON file (default: ~/.config/odc-gee/credentials.json).
* `REGIONS_CONFIG`: Optional; a JSON file for storing latitude/longitude
  locations if not performing global indexing (default:
~/.config/odc-gee/regions.json).

Some example config files are provided in the `./opt/config` directory.

## Usage
The indexing of datasets can be done using the `index_gee` command. An example:
`index_ee --asset LANDSAT/LC08/C01/T1_SR --product ls8_google`

The package comes with two scripts. One script is a basic attempt to streamline
new ODC product creation. This can be ran as `new_product <product_name.yaml>`.
This will guide you through various prompts for creating a new product, or you
can follow the [normal documented
procedure](https://datacube-core.readthedocs.io/en/latest/ops/product.html).

The package also provides Python modules and optional utilities like systemd
timer and service for automated indexing. Modules can be accessed as such:
`import odc_gee`.

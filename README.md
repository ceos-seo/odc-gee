# ODC-GEE

## About
This package provides various tools for indexing [Google Earth Engine
(GEE)](https://earthengine.google.com/)
images into an [Open Data Cube
(ODC)](https://datacube-core.readthedocs.io/en/latest/index.html) index.  It
takes advantage of the [GEE REST
API](https://developers.google.com/earth-engine/reference). Therefore it will
require Google service account credentials and a GEE API key in order to work.

## Installation
The package can be installed using Python setuptools:
`python setup.py build && python setup.py install`

## Configuration
The scripts and python modules in this package use the following environment
variables:

* `DATACUBE_CONFIG_PATH`: the ODC configuration file.
* `GOOGLE_APPLICATION_CREDENTIALS`: the service account credentials JSON file.
* `EE_API_KEY`: the API key for the GEE API.
* `REGIONS_CONFIG`: a JSON file for storing latitude/longitude locations if not
  performing global indexing.

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

### Project Structure

	 ├── odc_gee
	 │   ├── earthengine.py
	 │   ├── indexing.py
	 │   ├── __init__.py
	 │   ├── logger.py
	 │   └── parser.py
	 ├── opt
	 │   ├── config
	 │   │   ├── datacube-core
	 │   │   │   └── datacube.conf
	 │   │   ├── odc-gee
	 │   │   │   └── regions.json
	 │   │   └── systemd
	 │   │       └── user
	 │   │           ├── update_products.service
	 │   │           └── update_products.timer
	 │   └── local
	 │       └── bin
	 │           └── update_products
	 ├── scripts
	 │   ├── index_gee
	 │   └── new_product
	 ├── README.md
	 └── setup.py

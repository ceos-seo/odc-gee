# ODC-GEE

## About
This package provides various tools for indexing [Google Earth Engine
(GEE)](https://earthengine.google.com/)
images into an [Open Data Cube
(ODC)](https://datacube-core.readthedocs.io/en/latest/index.html) index.  It
takes advantage of the [GEE REST
API](https://developers.google.com/earth-engine/reference) and the [GEE STAC
API](https://earthengine-stac.storage.googleapis.com/).

## Installation
Preferred method is to use pip:
`pip install -e odc-gee`

Alternatively, the package can be installed using Python setuptools:
`python setup.py build && python setup.py install`

## Configuration
The scripts and python modules in this package use the following environment
variables:

* `DATACUBE_CONFIG_PATH`: The ODC configuration file.
* `GOOGLE_APPLICATION_CREDENTIALS`: Optional; the service account credentials
  JSON file (default: ~/.config/odc-gee/credentials.json).
* `REGIONS_CONFIG`: Optional; a JSON file for storing latitude/longitude
  locations if not performing global indexing (default:
~/.config/odc-gee/regions.json).

Some example config files are provided in the `./opt/config` directory.

## Usage
The package comes with two scripts. One is to create ODC product definitions
using GEE metadata. The other is to index an ODC product using GEE metadata.
The index script can index for an existing ODC product in the database, or it
create a new generalized product based on the metadata and then index it.

New product creation is done using `new_product`. An example: `new_product
--asset <asset_id> <product_name.yaml>`. This will try to automate the entire
product definition creation process as defined in the [ODC
documentation](https://datacube-core.readthedocs.io/en/latest/ops/product.html).
Check the resulting document to see if anything needs changing for your desired
result.

The indexing of datasets can be done using the `index_gee` command. An example:
`index_gee --asset LANDSAT/LC08/C01/T1_SR --product ls8_google`. Use `index_gee
--help` to see all available options.

The package also provides Python modules and optional utilities like systemd
timer and service for automated indexing. Modules can be accessed as such:
`import odc_gee`.

### Datacube Wrapper
Lastly, a Datacube wrapper has been created with the intent of handling GEE
OAuth in notebooks if credentials aren't provided. This wrapper also intends to
allow for real-time indexing capabilities of GEE products so that the manual
indexing process is not required at the limitation of product customization.

#### Normal ODC behavior
This assumes an indexed product with `ls8_google` as the product name, a defined CRS/resolution, and
measurements with red/green/blue aliases. If no credentials file is supplied then the wrapper will
try to authenticate with Google using OAuth.

	from odc_gee.earthengine import Datacube

	latitude = (-17.63, -17.75)
	longitude = (168.25, 168.15)
	time=('2019-01-01', '2019-02-02')

	ds = dc.load(product='ls8_google', measurements=['red', 'green', 'blue'],
		     group_by='solar_day', latitude=latitude, longitude=longitude, time=time)

#### Real-time indexing
This capability looks similar to a normal ODC load, but it requires an asset ID to be provided and
can also accept some GEE API query parameters.

	from odc_gee.earthengine import Datacube

	latitude = (-17.63, -17.75)
	longitude = (168.25, 168.15)
	time=('2019-01-01', '2019-02-02')

	dc = Datacube()
	ds = dc.load(asset='LANDSAT/LC08/C01/T1_SR', measurements=['B4', 'B3', 'B2'],
		     latitude=latitude, longitude=longitude, time=time,
		     group_by='solar_day', resolution=(-2.69493352e-4, 2.69493352e-4),
		     output_crs='EPSG:4326')
	ds.isel(time=0).to_array().plot.imshow(vmin=0, vmax=3000, size=8);

![](/docs/images/real-time-example.png)

#!/usr/bin/env python
''' ODC-GEE Setup '''

from setuptools import setup, find_packages

with open('README.md', 'r', encoding='utf-8') as fh:
    LONG_DESCRIPTION = fh.read()

setup(name='odc-gee',
      version='2.25',
      author='Andrew Lubawy',
      author_email='andrew.m.lubawy@ama-inc.com',
      description='Google Earth Engine indexing tools for Open Data Cube',
      long_description=LONG_DESCRIPTION,
      long_description_content_type='text/markdown',
      license='Apache-2.0',
      url='https://github.com/ceos-seo/odc-gee',
      project_urls={
          'Bug Tracker': 'https://github.com/ceos-seo/odc-gee/issues'
          },
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Intended Audience :: Developers',
          'Intended Audience :: Science/Research',
          'License :: OSI Approved :: Apache Software License',
          'Operating System :: OS Independent',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.6',
          'Programming Language :: Python :: 3.7',
          'Topic :: Scientific/Engineering :: GIS',
          ],
      install_requires=[
          "click-plugins>=1.1.1",
          "click>=7.1.2",
          "datacube>=1.8.3",
          "earthengine-api>=0.1.24",
          "numpy>=1.18.4",
          "rasterio>=1.1.8",
          ],
      packages=find_packages(exclude=['tests*']),
      python_requires=">=3.6",
      scripts=['scripts/index_gee', 'scripts/new_product'],)

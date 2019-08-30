# -*- coding: utf-8 -*-

from setuptools import find_packages
from setuptools import setup

setup(
    name='TermwikiImporter',
    version='0.0.1',
    author='Børre Gaup',
    author_email='borre.gaup@uit.no',
    packages=find_packages(),
    url='http://divvun.no',
    license='GPL v3.0',
    long_description=open('README.md').read(),
    entry_points={
        'console_scripts': [
            'termimport = termwikiimporter.importer:main',
            'termexport = termwikiimporter.exporter:write_to_termwiki',
            'termbot = termwikiimporter.bot:main',
            'termmover = termwikiimporter.mover:main',
            'dictexport = termwikiimporter.dicts2wiki:main',
            'termdupechecker = termwikiimporter.dupechecker:main',
        ]
    },
    install_requires=[
        'attrs',
        'lxml',
        'mwclient',
        'openpyxl',
        'pyyaml'
    ],
    test_suite='nose.collector',
)

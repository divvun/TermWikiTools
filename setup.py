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
        ]
    },
    install_requires=[
        'lxml',
        'openpyxl',
    ],
    test_suite='nose.collector',
)

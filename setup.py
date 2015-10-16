from setuptools import setup, find_packages

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
            'import = termwikiimporter.importer.main',
        ]
    },
    install_requires=[
        'lxml',
        'openpyxl',
    ],
    test_suite='nose.collector',
)

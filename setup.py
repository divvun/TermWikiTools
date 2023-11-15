# -*- coding: utf-8 -*-

from setuptools import find_packages, setup

setup(
    name="TermWikiTools",
    version="0.0.2",
    author="Børre Gaup",
    author_email="borre.gaup@uit.no",
    packages=find_packages(),
    url="http://divvun.no",
    license="GPL v3.0",
    long_description=open("README.md").read(),
    entry_points={
        "console_scripts": [
            "termimport = termwikitools.importer:main",
            "termexport = termwikitools.exporter:write_to_termwiki",
            "termbot = termwikitools.bot:main",
            "termmover = termwikitools.mover:main",
            "dictexport = termwikitools.dicts2wiki:main",
        ]
    },
    install_requires=[
        "attrs",
        "lxml",
        "mwclient",
        "openpyxl",
        "pyyaml",
        "unidecode",
        "requests",
    ],
    test_suite="nose.collector",
)

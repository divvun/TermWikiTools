# -*- coding: utf-8 -*-
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this file. If not, see <http://www.gnu.org/licenses/>.
#
#   Copyright © 2016-2019 The University of Tromsø
#   http://giellatekno.uit.no & http://divvun.no
#
"""Convert term files to termwiki parsable xml."""

from dataclasses import asdict
import json
from pathlib import Path
import click
from marshmallow.exceptions import ValidationError
import openpyxl


from termwikitools.read_termwiki import (
    COLLECTION_SCHEMA,
    TERMWIKI_PAGE_SCHEMA,
    TermWikiPage,
)


class SheetImporter:
    def __init__(self, sheet):
        self.sheet = sheet

    def row_to_concept(self, sheet_info: dict, row_number: int) -> TermWikiPage:
        return TERMWIKI_PAGE_SCHEMA.load(
            {
                "title": f"{sheet_info['main_category']}:{sheet_info['collection']}_{row_number}",
                "concept": {"collection": [sheet_info["collection"]]},
                "related_expressions": self.make_dict(
                    sheet_info.get("related_expressions"), row_number
                ),
                "concept_infos": self.make_dict(
                    sheet_info.get("concept_infos"), row_number
                )
                if sheet_info.get("concept_infos")
                else None,
            }
        )

    def make_dict(self, dict_templates: list, row_number: int) -> list:
        return [
            {
                key: (
                    self.sheet.cell(row=row_number, column=value).value.lower()
                    if key == "expression"
                    and self.sheet.cell(row=row_number, column=value).value
                    else self.sheet.cell(row=row_number, column=value).value
                    if isinstance(value, int)
                    else value
                )
                for key, value in dict_template.items()
            }
            for dict_template in dict_templates
        ]


def extract_collection(
    sheet_importer: SheetImporter, sheetinfo: dict
) -> list[TermWikiPage]:
    return [
        sheet_importer.row_to_concept(sheet_info=sheetinfo, row_number=row_number)
        for row_number in range(2, sheet_importer.sheet.max_row + 1)
    ]


@click.command()
@click.argument("filename")
def main(filename):
    path = Path(filename)
    workbook = openpyxl.load_workbook(filename)
    template_json = path.with_name(f"{path.stem}.template.json")
    sheet_infos = json.loads(template_json.read_text())

    for sheet_info in sheet_infos.get("sheets"):
        template = sheet_info.get("template")
        try:
            data = {
                "collection": asdict(
                    COLLECTION_SCHEMA.load(
                        {
                            "name": f"Collection:{template.get('collection')}",
                            "info": sheet_infos.get("info"),
                            "owner": sheet_infos.get("owner"),
                            "languages": [
                                related_expression.get("language")
                                for related_expression in template.get(
                                    "related_expressions"
                                )
                            ],
                        }
                    )
                ),
                "concepts": [
                    asdict(concept)
                    for concept in extract_collection(
                        sheet_importer=SheetImporter(
                            workbook[sheet_info.get("sheetname")]
                        ),
                        sheetinfo=template,
                    )
                ],
            }
        except ValidationError as error:
            message = f"Error in input data\n{error}"
            raise SystemExit(message)

        path.with_name(
            f"{template.get('collection').replace(' ', '_')}.result.json"
        ).write_text(
            json.dumps(
                data,
                indent=2,
                ensure_ascii=False,
            )
        )

from collections import defaultdict
from dataclasses import dataclass

from termwikitools.dumphandler import DumpHandler
from termwikitools.duplicate_merge_row import (
    DuplicateMergeRow,
    merge_row_from_valid_columns,
)

DUPLICATE_REPORT_COLUMN_COUNT = 6


@dataclass
class DuplicateMergeRows:
    rows: list[DuplicateMergeRow]

    def to_wikitext(self) -> str:
        """Render duplicate candidates as a MediaWiki review page."""
        grouped: dict[tuple[str, str], list[DuplicateMergeRow]] = (
            defaultdict(list)
        )

        for row in self.rows:
            grouped[row.get_lang_pair_key()].append(row)

        lines = [
            "__TOC__",
            "",
            "This page lists possible duplicate Concept pages detected automatically.",
            "",
            "Use Decision=merge to approve merging, or keep to leave pages untouched.",
            "Only rows with Decision=merge and Processed=no are executed by the bot.",
            "",
        ]

        if not grouped:
            lines.append("No duplicate candidates were found.")
            return "\n".join(lines)

        for lang1, lang2 in sorted(grouped):
            lines.append(f"== {lang1} <-> {lang2} ==")
            lines.append('{| class="wikitable sortable"')
            lines.append(
                "! Term pair !! Candidate pages !! Decision "
                "!! Keep page !! Report !! Processed"
            )

            for row in sorted(grouped[(lang1, lang2)], key=lambda r: r.pair_text):
                lines.append("|-")
                lines.append(row.to_wikitext())

            lines.append("|}")
            lines.append("")

        return "\n".join(lines)        

def merge_rows_from_wikitext(wikitext: str) -> DuplicateMergeRows:
    """Parse machine-readable rows from the duplicate report wikitext."""
    stripped_lines = (line.strip() for line in wikitext.splitlines())
    columns = (
        line.split("||")
        for line in stripped_lines
        if line.startswith("| ") and "||" in line
    )
    valid_columns = (
        col for col in columns if len(col) == DUPLICATE_REPORT_COLUMN_COUNT
    )

    return DuplicateMergeRows(
        rows=[
            merge_row_from_valid_columns(column, line_index)
            for line_index, column in enumerate(valid_columns)
        ]
    )

def merge_rows_from_dump(only_sanctioned: str) -> DuplicateMergeRows:
    def key_text(key: frozenset[tuple[str, str]]) -> str:
        sorted_pair = tuple(sorted(key, key=lambda p: (p[0], p[1])))
        return " <-> ".join(f"{lang}:{term}" for lang, term in sorted_pair)


    dumphandler = DumpHandler()
    generated_dict = dumphandler.find_duplicate_candidates(
        only_sanctioned=only_sanctioned
    )

    return DuplicateMergeRows(rows=[
        DuplicateMergeRow(
            line_index=0,
            pair_text=key_text(key),
            pages=sorted(pages),
            decision="keep",
            keep_page="",
            report="",
            processed="no",
        )
        for key, pages in generated_dict.items()
    ])
    
def only_processed_rows(duplicate_merge_rows: DuplicateMergeRows) -> DuplicateMergeRows:
    """Filter the rows to only include those that have been processed."""
    processed_rows = [
        row for row in duplicate_merge_rows.rows if row.processed.lower() == "yes"
    ]
    return DuplicateMergeRows(rows=processed_rows)

def none_processed_rows(duplicate_merge_rows: DuplicateMergeRows) -> DuplicateMergeRows:
    """Filter the rows to only include those that have not been processed."""
    unprocessed_rows = [
        row for row in duplicate_merge_rows.rows if row.processed.lower() != "yes"
    ]
    return DuplicateMergeRows(rows=unprocessed_rows)
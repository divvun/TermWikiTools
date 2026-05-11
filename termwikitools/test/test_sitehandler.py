# -*- coding: utf-8 -*-

from termwikitools.sitehandler import SiteHandler

HEADER = (
    "! Term pair !! Candidate pages !! Decision !! Keep page !! Report !! Processed\\n"
)


def test_preserve_processed_yes_row():
    existing_content = (
        '{| class="wikitable sortable"\n'
        f"{HEADER}"
        "|-\n"
        "| se:word <-> nb:ord || [[Concept:1]] / [[Concept:2]] || merge "
        "|| [[Concept:1]] || done || yes\n"
        "|}\n"
    ).strip()

    generated_content = (
        '{| class="wikitable sortable"\n'
        f"{HEADER}"
        "|-\n"
        "| se:word <-> nb:ord || [[Concept:1]] / [[Concept:2]] || keep "
        "|| || || no\n"
        "|}\n"
    ).strip()

    merged = SiteHandler._preserve_processed_duplicate_rows(
        existing_content=existing_content,
        generated_content=generated_content,
    )

    rows = SiteHandler.parse_duplicate_merge_rows(merged)
    assert len(rows) == 1
    assert rows[0].decision == "merge"
    assert rows[0].keep_page == "[[Concept:1]]"
    assert rows[0].report == "done"
    assert rows[0].processed == "yes"


def test_do_not_preserve_unprocessed_row():
    existing_content = (
        '{| class="wikitable sortable"\n'
        f"{HEADER}"
        "|-\n"
        "| se:word <-> nb:ord || [[Concept:1]] / [[Concept:2]] || merge "
        "|| [[Concept:1]] || pending || no\n"
        "|}\n"
    ).strip()

    generated_content = (
        '{| class="wikitable sortable"\n'
        f"{HEADER}"
        "|-\n"
        "| se:word <-> nb:ord || [[Concept:1]] / [[Concept:2]] || keep "
        "|| || || no\n"
        "|}\n"
    ).strip()

    merged = SiteHandler._preserve_processed_duplicate_rows(
        existing_content=existing_content,
        generated_content=generated_content,
    )

    rows = SiteHandler.parse_duplicate_merge_rows(merged)
    assert len(rows) == 1
    assert rows[0].decision == "keep"
    assert rows[0].keep_page == ""
    assert rows[0].report == ""
    assert rows[0].processed == "no"


def test_processed_column_contains_yes():
    existing_content = (
        '{| class="wikitable sortable"\n'
        f"{HEADER}"
        "|-\n"
        "| se:word <-> nb:ord || [[Concept:1]] / [[Concept:2]] || merge "
        "|| [[Concept:1]] || done || YES (merged)\n"
        "|}\n"
    ).strip()

    generated_content = (
        '{| class="wikitable sortable"\n'
        f"{HEADER}"
        "|-\n"
        "| se:word <-> nb:ord || [[Concept:1]] / [[Concept:2]] || keep "
        "|| || || no\n"
        "|}\n"
    ).strip()

    merged = SiteHandler._preserve_processed_duplicate_rows(
        existing_content=existing_content,
        generated_content=generated_content,
    )

    rows = SiteHandler.parse_duplicate_merge_rows(merged)
    assert len(rows) == 1
    assert rows[0].decision == "merge"
    assert rows[0].processed == "YES (merged)"


def test_match_uses_pair_and_pages():
    existing_content = (
        '{| class="wikitable sortable"\n'
        f"{HEADER}"
        "|-\n"
        "| se:word <-> nb:ord || [[Concept:1]] / [[Concept:2]] || merge "
        "|| [[Concept:1]] || done || yes\n"
        "|}\n"
    ).strip()

    generated_content = (
        '{| class="wikitable sortable"\n'
        f"{HEADER}"
        "|-\n"
        "| se:word <-> nb:ord || [[Concept:1]] / [[Concept:3]] || keep "
        "|| || || no\n"
        "|}\n"
    ).strip()

    merged = SiteHandler._preserve_processed_duplicate_rows(
        existing_content=existing_content,
        generated_content=generated_content,
    )

    rows = SiteHandler.parse_duplicate_merge_rows(merged)
    assert len(rows) == 1
    assert rows[0].decision == "keep"
    assert rows[0].processed == "no"

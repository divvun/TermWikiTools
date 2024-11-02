from pathlib import Path

import click

from termwikitools.find_stems import make_stems


def by_date(log_directory: str):
    date_counter: dict[str, dict[str, int]] = {}

    for log in Path(log_directory).glob("*.log.*"):
        contents = log.read_text()
        for line in contents.splitlines():
            date = line.split(" ")[0]
            if "names: [" in line and "names: []" not in line:
                if date_counter.get(date) is None:
                    date_counter[date] = {"terms": 0, "dicts": 0}
                date_counter[date]["terms"] += 1
            if "resolve_dict_entry_list:" in line:
                if date_counter.get(date) is None:
                    date_counter[date] = {"terms": 0, "dicts": 0}
                date_counter[date]["dicts"] += 1

    for date in sorted(date_counter.keys()):
        print(f"{date}\t{date_counter[date]['terms']}\t{date_counter[date]['dicts']}")


def by_searchterm(log_directory: str):
    term_counter: dict[str, dict[str, int]] = {}
    previous_line = ""

    for log in Path(log_directory).glob("*.log.*"):
        contents = log.read_text()
        for line in contents.splitlines():
            if "names: [" in line and "names: []" not in line:
                term = previous_line.split(":")[-1].strip()
                if term_counter.get(term) is None:
                    term_counter[term] = {"terms": 0, "dicts": 0}
                term_counter[term]["terms"] += 1
            if "resolve_dict_entry_list:" in line:
                term = line.split("_list: ")[-1].strip().split(" src:")[0]
                if term_counter.get(term) is None:
                    term_counter[term] = {"terms": 0, "dicts": 0}
                term_counter[term]["dicts"] += 1

            previous_line = line

    for term in sorted(term_counter.keys()):
        print(f"{term}\t{term_counter[term]['terms']}\t{term_counter[term]['dicts']}")


def by_lang(log_directory: str):
    lang_counter: dict[str, dict[str, int]] = {}
    stems = make_stems()
    previous_line = ""

    for log in Path(log_directory).glob("*.log.*"):
        contents = log.read_text()
        for line in contents.splitlines():
            if "names: [" in line and "names: []" not in line:
                term = previous_line.split(":")[-1].strip()
                for lang in stems.get(term, []):
                    if lang_counter.get(lang) is None:
                        lang_counter[lang] = {"terms": 0, "dicts": 0}
                    lang_counter[lang]["terms"] += 1
            if "resolve_dict_entry_list:" in line:
                term = line.split("_list: ")[-1].strip().split(" src:")[0]
                for lang in stems.get(term, []):
                    if lang_counter.get(lang) is None:
                        lang_counter[lang] = {"terms": 0, "dicts": 0}
                    lang_counter[lang]["dicts"] += 1

            previous_line = line

    Path("by_lang.tsv").write_text(
        "\n".join(
            [
                f"{lang}\t{lang_counter[lang]['terms']}\t{lang_counter[lang]['dicts']}"
                for lang in sorted(lang_counter.keys())
            ]
        )
    )
    print("by_lang.tsv written")


@click.command()
@click.argument(
    "log_type",
    type=click.Choice(["by_lang", "by_date", "by_searchterm"]),
)
@click.argument("log_directory", type=click.Path(exists=True))
def main(log_directory, log_type):
    match log_type:
        case "by_lang":
            by_lang(log_directory)
        case "by_date":
            by_date(log_directory)
        case "by_searchterm":
            by_searchterm(log_directory)

from dataclasses import dataclass


@dataclass
class DuplicateMergeRow:
    line_index: int
    pair_text: str
    pages: list[str]
    decision: str
    keep_page: str
    report: str
    processed: str

    def to_wikitext(self) -> str:
        pages_text = " / ".join(f"[[{title}]]" for title in sorted(self.pages))
        return (
            ""
            f"| {self.pair_text} || {pages_text} || {self.decision} "
            f"|| {self.keep_page} || {self.report} || {self.processed}"
        )

    def get_frozenset_key(self) -> frozenset[tuple[str, ...]]:
        pairs = self.pair_text.replace("| ", "").split("<->")
        oink = []
        for pair in pairs:
            parts = pair.split(":")
            oink.append(tuple(part.strip() for part in parts))

        return frozenset(oink)

    def get_lang_pair_key(self) -> tuple[str, str]:
        pairs = self.pair_text.split("<->")
        lang1, _ = pairs[0].split(":")
        lang2, _ = pairs[1].split(":")
        return (lang1.strip(), lang2.strip())

    def is_mergeable(self) -> bool:
        decision = self.decision.strip().lower()
        row_processed = self.processed.strip().lower()
        return decision == "merge" and row_processed != "yes"

    def validated_merge_targets(self) -> tuple[str, list[str]] | None:
        keep_page = self.keep_page.strip().replace("[", "").replace("]", "")
        if not keep_page:
            print(f"Skipping row without keep page: {self.pair_text}")
            return None
        if keep_page not in self.pages:
            print(f"Skipping row where keep page is not in candidates: {keep_page}")
            return None

        merge_pages = [title for title in self.pages if title != keep_page]
        if not merge_pages:
            print(f"Skipping row with no pages to merge: {self.pair_text}")
            return None

        return keep_page, merge_pages

    def mark_as_processed(self) -> None:
        self.processed = "Yes"
        note = f"Merged into [[{self.keep_page.strip()}]]"
        self.report = note if not self.report else f"{self.report}; {note}"


def merge_row_from_valid_columns(
    column: list[str], line_index: int = 0
) -> DuplicateMergeRow:
    pair_text, pages_cell, decision, keep_page, report, processed = column
    cleaned_pair_text = pair_text.replace("| ", "").strip()
    pages = [
        page.strip().replace("[", "").replace("]", "")
        for page in pages_cell.split("/")
        if page.strip()
    ]
    return DuplicateMergeRow(
        line_index=line_index,
        pair_text=cleaned_pair_text,
        pages=pages,
        decision=decision.strip(),
        keep_page=keep_page.strip(),
        report=report.strip(),
        processed=processed.strip(),
    )

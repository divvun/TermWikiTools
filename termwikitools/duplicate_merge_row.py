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
        pairs = self.pair_text.split("<->")
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


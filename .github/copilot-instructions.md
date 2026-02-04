# TermWikiTools AI Coding Instructions

## Project Overview

TermWikiTools is a Python toolkit for managing multilingual terminology in TermWiki (a MediaWiki-based terminology database at satni.uit.no/termwiki). The project supports importing/exporting terminology data, validating linguistic content, and synchronizing between Excel files, JSON, and MediaWiki pages.

**Core Entities:**

- **Concept**: Multilingual terminology entries with metadata (category, collection, sources)
- **RelatedExpression**: Terms in specific languages with linguistic properties (pos, sanctioned status, inflection)
- **ConceptInfo**: Language-specific definitions/explanations
- **Collection**: Groups of related concepts with ownership and language metadata

## Architecture

### Handler Pattern

Two main handlers manage different data sources:

- **`DumpHandler`**: Works with local XML dump (`$GTHOME/words/terms/termwiki/dump.xml`)
- **`SiteHandler`**: Live MediaWiki API interactions via `mwclient`

Both parse TermWiki's custom template syntax (e.g., `{{Concept}}`, `{{Related expression}}`).

### Data Flow Pipeline

1. **Import**: Excel → JSON schema validation (marshmallow-dataclass) → `.result.json`
2. **Export**: `.result.json` → TermWiki template syntax → MediaWiki API
3. **Search/Validate**: Dump XML → dataclass models → HFST linguistic analyzers → reports

### Key Directories

- `termwikitools/`: Main package with CLI commands
- `termwikitools/test/`: Unit tests with example Excel/XML fixtures
- `xml/`: (Not in repo) Expected external data location

## Critical Conventions

### 1. Environment Dependencies

**Required environment variables:**

- `GTHOME`: Path to GiellaLT infrastructure (`$GTHOME/words/terms/termwiki/`)
- `GTLANGS`: Path to language resources (for HFST analyzers in `lang-{code}/src/fst/`)
- Config file: `~/.config/term_config.yaml` (MediaWiki credentials: `username`, `password`)

Always check these before operations touching dumps/SVN/FSTs.

### 2. Marshmallow Dataclass Validation

All models in `read_termwiki.py` use `marshmallow-dataclass` for strict schema validation:

- **Validators**: `validate_lang()`, `validate_pos()`, `validate_relation()`, `validate_status()`
- **Language codes**: Must match `LANGUAGES` dict (e.g., `'se'` not `'sme'`)
- **POS values**: Restricted set (`N`, `V`, `A`, `Adv`, etc. - see `validate_pos()`)
- **Sanctioned**: String `"True"` or `"False"` (not bool)

When modifying models, preserve validation logic and handle `ValidationError` explicitly.

### 3. TermWiki Template Syntax

Each dataclass implements `to_termwiki()` for serialization:

```python
{{Concept
|collection=@@ separated collections
|category=...
}}
{{Related expression
|language=se
|expression=áhčči
|pos=N
|sanctioned=True
}}
```

Never manually construct template strings - use dataclass methods.

### 4. CLI Tool Design (Click)

Commands use Click groups with consistent patterns:

- **termbot dump**: Offline analysis (XML dump operations)
- **termbot site**: Live wiki modifications
- Language arguments: `type=click.Choice(list(LANGUAGES.keys()))`
- Use `@click.option("--only-sanctioned", is_flag=True)` for filtering

### 5. Testing Patterns

- Tests use fixtures in `termwikitools/test/excel/` and `termwikitools/test/terms/`
- Run with `nose` (dev dependency) or unittest
- Mock TermWiki content as multiline strings (see `test_read_termwiki.py`)

## Development Workflows

### Running Tests

```bash
poetry install
poetry run nosetests  # or python -m unittest
```

### Building/Installing

```bash
poetry build
poetry install
```

### Key CLI Commands

```bash
# Import Excel to JSON
termimport --lowercase --comma input.xlsx

# Export to TermWiki
termexport result.json

# Validate dump for missing terms
termbot dump missing sme --only-sanctioned

# Search/merge operations
termsearcher search se term1 term2
```

### Linting (Ruff)

Follows PEP8 with specific rules (see `pyproject.toml` [tool.ruff]):

- Line length: 88
- Enabled: Pyflakes, flake8-bugbear, isort, Pylint
- **Exception**: `A003` (builtin shadowing) ignored

Use `ruff check` before committing.

## Common Pitfalls

1. **Sanctioned as string**: `sanctioned="True"` not `sanctioned=True`
2. **Language code mismatch**: Use `LANGUAGES` dict values (`'se'`), not ISO 639-3 (`'sme'`)
3. **GTHOME not set**: Many operations fail silently or with confusing errors
4. **Invalid characters in expressions**: Regex `INVALID_CHARS_RE = re.compile(r"[()[\]?:;+*=]")` - strip before validation
5. **Non-breaking spaces**: Replace `\xa0` with regular space (see `dumphandler.py:122`)
6. **Concept titles**: Format is `{category}:{collection}_{index}`

## Key Files to Reference

- **Data models**: `read_termwiki.py` (TermWikiPage, Concept, RelatedExpression)
- **Constants**: `handler_common.py` (NAMESPACES, LANGUAGES)
- **Template examples**: `termwikitools/test/excel/simple.yaml`
- **CLI entry points**: `pyproject.toml` [tool.poetry.scripts]

## External Dependencies

- **mwclient**: MediaWiki API client (not pywikibot)
- **openpyxl**: Excel file parsing
- **hfst**: Finite State Transducer for linguistic analysis
- **lxml**: XML dump parsing (ElementTree API)
- **marshmallow-dataclass**: Schema validation and serialization

# Reference Checker

A GUI desktop app for verifying the integrity of academic references.

This program is designed to work with documents with dedicated reference sections.

_NOTE: Human review of references marked as 'unsure' or 'fake' may be needed to confirm hallucinations_

## Running

Make sure you have both Python and Ruby installed.

Before the application can be run the dependencies have to be installed. uv is **highly** recommended for this as it quickly and easily installs all the required packages and sets up the virtual enviroment, all within a few commands. bundle is required to install AnyStyle.

1. Clone the repo

```bash
git clone https://github.com/<user>/refchecker
```

2. Install Python and Ruby dependencies

```bash
cd refchecker
bundle config set --local path 'vendor/bundle'
bundle install
uv sync
```

3. Run application

```bash
uv run src/main.py
```

## Structure

_NOTE: the database is generated in data/ and the .env should be placed in src/_

```
├── assets/
│   └── help.html
├── data/
│   ├── .gitkeep
├── src/
│   ├── extract.py
│   ├── format.rb
│   ├── gui.py
│   ├── main.py
│   ├── parse.py
│   ├── query.py
│   ├── report.py
│   └── verify.py
├── .gitignore
├── .python-version
├── .ruby-version
├── Gemfile
├── Gemfile.lock
├── pyproject.toml
├── README.md
└── uv.lock
```

## 3rd Party Libraries

_NOTE: Full list is in pyproject.toml and Gemfile_

### Python

- habanero
- jellyfish
- numpy
- pymupdf
- pymupdf-layout
- pymupdf4llm
- pyside6
- python-dotenv
- rapidfuzz
- requests
- stop-words
- weasyprint

### Ruby

- AnyStyle

## Licence

Licensed under the AGPLv3 Licence. See [`LICENCE`](LICENCE) for details.

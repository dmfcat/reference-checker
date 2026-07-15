# Reference Checker
A GUI app created with PySide6 that extracts bibliographic references from PDF files and verifies them to determine if they're hallucinated or not.

This program is designed to work with documents with dedicated reference sections.

*NOTE: Human review of references marked as unsure or fake may be needed to confirm hallucinations*

## Running
Make sure you have both Python and Ruby installed.

Before the application can be run the dependencies have to be installed. uv is **highly** recommended for this as it quickly and easily installs all the required packages and sets up the virtual enviroment, all with a few commands. bundle is required to install AnyStyle.

```bash
cd refcheck
bundle config set --local path 'vendor/bundle'
bundle install
uv sync
uv run src/main.py
```

## Structure
*NOTE: the database is generated in data/ and the .env is placed in src/*
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
*NOTE: Some of these are dependencies, the full list is in pyproject.toml and Gemfile*
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

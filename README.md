# Reference Checker

A GUI desktop app for verifying the integrity of academic references. This application works in five steps:

1. The user can upload PDFs for reference extraction or paste plaintext references manually. The user is prompted to confirm the references for processing.
2. These references are then parsed so each element is separated.
3. Academic databases ([Semantic Scholar](https://www.semanticscholar.org/) and [Crossref](https://www.crossref.org/)) are queried to find potential matches.
4. User uploaded references are compared against their respective potential matches.
5. The user receives a colour-coded HTML formatted report on the validity of each reference and an overview for the document.

References extracted from Semantic Scholar and Crossref can also be optionally 'cached' in a SQLite database, for future usage. The user can toggle which backends are used and what type of report is generated from the settings.

> [!NOTE]
> An API key is required to query Semantic Scholar and an email can be used to query Crossref, this information should be stored in `.env`. You can easily obtain an API key with a `ac.uk` or similar academic email, the email for Crossref is recommended, but optional. More details can be found in [`src/.env.example`](src/.env.example)
>
> This program is designed to work with documents with a dedicated reference section, rather than documents with footnote references.
>
> Human review of references may be needed to confirm hallucinations, this tool is meant to _assist_ you in finding fake references.

## Running

Make sure you have both [Python](https://www.python.org/) and [Ruby](https://www.ruby-lang.org/) installed.

Before the application can be run the dependencies have to be installed. [uv](https://docs.astral.sh/uv/) is _highly_ recommended for managing the Python dependencies as it quickly and easily installs all the required packages and sets up the virtual environment, all within a few commands. bundle is required to install AnyStyle.

1. Clone the repo

```bash
git clone https://github.com/dmfcat/refchecker
```

2. Install Python and Ruby dependencies

```bash
cd reference-checker
bundle config set --local path 'vendor/bundle'
bundle install
uv sync
```

3. Run application

```bash
uv run src/main.py
```

Make sure your Semantic Scholar API key and email are in `.env`, this file should be in [`src/`](src/), see [`src/.env.example`](src/.env.example) for more details.

## Structure

> [!NOTE]
> The database `localpapers.db` is generated in [`data/`](data/) (if it doesn't exist) and the `.env` should be placed in [`src/`](src/)

```text
├── assets/
│   └── help.html
├── data/
│   ├── .gitkeep
│   ├── localpapers.db
├── src/
│   ├── .env
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

## Demo Video

https://github.com/user-attachments/assets/e5af4ba7-2c70-45d0-a875-45ab7838031c

## About

This was developed during my 'final year project' in my 3rd year of university.

## Credits

Special thanks to the creators of these 3rd party libraries used in this application.

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

[AGPLv3](LICENCE)

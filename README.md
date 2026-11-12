# Reference Checker

A GUI Python tool for verifying the integrity of academic references, this tool aims to aid the user in detecting references so human review of the generated report may be needed to reach a final verdict of the integrity of a reference.

This project was developed during my 'final year project' module of university.

## Features

- A easy to use and visually appealing GUI made with PySide6.
- Extracts all references from the reference section of a PDF document.
- Allows for manually entering plaintext references.
- Allows for confirming extracted references.
- Automatically parses references regardless of their style (e.g. Harvard, Vancouver, etc...).
- Queries the Semantic Scholar and Crossref API and/or a local database for cross-referencing.
- Stores verified references in a local SQLite database.
- Grades and scores every extracted reference based on their individual elements.
- Produces an informative and readable report.
- Allows for customising the type of report generated and what backends are used.

## Demo Video

https://github.com/user-attachments/assets/e5af4ba7-2c70-45d0-a875-45ab7838031c

## Running

Make sure you have [Python](https://www.python.org/), [Ruby](https://www.ruby-lang.org/), [git](https://git-scm.com/install/) and [uv](https://docs.astral.sh/uv/getting-started/installation/) installed.

1. Clone the repo

```bash
git clone https://github.com/dmfcat/refchecker
cd reference-checker
```

2. Install Python and Ruby dependencies

```bash
bundle config set --local path 'vendor/bundle'
bundle install
uv sync
```

3. Run the application

```bash
uv run reference-checker
```

> [!NOTE]
> You need your own API key to use the Semantic Scholar API, supplying your personal email for the Crossref API is also recommended. You can easily obtain an API key from Semantic Scholar with an `ac.uk` or similar academic email
>
> An example `.env` file can be found in [`.env.example`](.env.example). Change the placeholder `API_KEY` variable to your key and the placeholder `EMAIL` to your personal email, and then rename `.env.example` to `.env`.

## Usage

You can upload a document for extraction by clicking the 'Select File' button selecting a `.pdf` file and then clicking 'Process File'. You will be prompted to confirm the extracted references and on confirmation the app will commence verifying and then generate a report.

You can optionally enter your references manually by clicking the 'Paste References' button. On confirmation the app will commence verifying and then generate a report.

You can click the 'Settings' button to select which backend is used (Semantic Scholar, Crossref, Local Database) and what type of report is generated (GUI, `.pdf`, `.html`, `.csv`).

> [!NOTE]
> The database `localpapers.db` is automatically generated in [`src/reference_checker/data/`](src/reference_checker/data/) if it doesn't already exist.

## How It Works

This application works in five steps:

1. The user can upload PDFs for reference extraction or paste plaintext references manually. The user is prompted to confirm the references for processing.
2. These references are then parsed so each element is separated.
3. Academic databases ([Semantic Scholar](https://www.semanticscholar.org/) and [Crossref](https://www.crossref.org/)) are queried to find potential matches.
4. User uploaded references are compared against their respective potential matches.
5. The user receives a colour-coded HTML formatted report on the validity of each reference and an overview for the document.

## Licence

[AGPLv3](LICENCE)

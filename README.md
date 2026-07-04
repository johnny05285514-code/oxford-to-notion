# Oxford Learner's Dictionaries → Notion CLI

A small Python CLI tool for personal vocabulary study.

Enter one English word, fetch the corresponding Oxford Learner's Dictionaries entry, parse the useful learning fields, and create or update a page in your Notion vocabulary database.

```powershell
python main.py brutality
```

If the same `Word` already exists in Notion, the tool updates the existing page instead of creating a duplicate.

## What it extracts

- Word
- Part of speech
- Countability, for example `[uncountable]` or `[countable]`
- Plural form, when available
- Numbered definitions
- Example sentences for each definition
- Source URL

## Important usage note

This project is intended for personal, low-frequency learning use.

It is not an official Oxford API client, and it is not affiliated with Oxford University Press, Oxford Learner's Dictionaries, or Notion. It uses normal HTTP requests and HTML parsing. Do not use it for bulk scraping, commercial redistribution, bypassing access controls, or high-frequency automated requests.

If Oxford returns a JavaScript, cookie, CAPTCHA, or access challenge page, the program stops and reports an error. It does not try to bypass those controls.

The tool does not save full HTML pages. It only stores the selected vocabulary-learning fields.

## Requirements

- Python 3.11+
- Network access to Oxford Learner's Dictionaries and the Notion API
- A Notion internal integration connected to your target database

## Installation

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Dependencies:

- `requests` for Oxford HTTP requests
- `beautifulsoup4` for HTML parsing
- `notion-client` for Notion API writes
- `python-dotenv` for loading `.env`
- `pytest` for tests

## Notion database fields

Create a Notion database with these exact property names and types:

| Property | Notion type |
|---|---|
| `Name` | Title |
| `Word` | Rich text |
| `Part of Speech` | Select |
| `Countability` | Rich text |
| `Plural Form` | Rich text |
| `Definitions` | Rich text |
| `Examples` | Rich text |
| `Source URL` | URL |
| `Added Date` | Date |

Your Notion integration must be connected to the database through Notion's `Connections` / sharing settings. It needs permission to read, insert, and update content.

The program validates the database schema before writing. If a property is missing or has the wrong type, it prints a user-readable error.

## Configure `.env`

Copy the example file:

```powershell
Copy-Item .env.example .env
```

Fill in your own Notion values:

```dotenv
NOTION_TOKEN=your_notion_integration_token
NOTION_DATABASE_ID=your_notion_database_id
```

Do not commit or share `.env`.

`.env` is ignored by `.gitignore`; `.env.example` is safe to publish because it contains placeholders only.

## Run

Import one word:

```powershell
python main.py brutality
```

Expected successful output:

```text
Imported 'brutality': https://app.notion.com/...
```

The argument must be one English word. Letters, hyphens, and English apostrophes are accepted.

## Optional Windows launcher

This repository includes:

```text
Oxford to Notion.bat
```

After installing dependencies and configuring `.env`, you can double-click this batch file on Windows. It keeps asking for words until you enter `q` or press Enter on a blank input.

## Tests

Run the full test suite:

```powershell
python -m pytest -q
```

The tests use small local HTML fixtures and mocked HTTP/Notion boundaries. They do not call Oxford and do not modify a real Notion database.

After configuring `.env`, you can manually test a real word:

```powershell
python main.py brutality
```

Run the same command twice to confirm the existing Notion page is updated instead of creating a duplicate.

## Common errors

- `Missing required environment variables`: `.env` is missing `NOTION_TOKEN` or `NOTION_DATABASE_ID`.
- `schema mismatch`: Notion database fields do not match the expected names or types.
- `no accessible data source`: the integration is not connected to the database, or the database has no accessible data source.
- `access challenge` / `refused the request`: Oxford refused the normal HTTP request; the tool will not bypass this.
- `no entry`: Oxford has no entry for the word.
- `Notion API request failed`: check your token, database connection, integration permissions, and network.

## Project structure

```text
main.py             CLI entry point and user-facing errors
config.py           Environment loading and validation
models.py           Parsed dictionary-entry data models
oxford_client.py    Oxford request, retry, and HTTP-status handling
parser.py           Centralized CSS selectors and HTML parsing
notion_writer.py    Notion schema validation, page body generation, and upsert
exceptions.py       User-readable exception types
tests/              Unit tests and minimal HTML fixtures
```

If Oxford changes its page structure, start by updating the `SELECTORS` mapping near the top of `parser.py`, then update or add fixture tests.

## Publishing checklist

Before uploading this project to GitHub:

- Keep `.env` private.
- Confirm `.env.example` contains placeholders only.
- Do not upload `.venv/`, `.pytest_cache/`, `__pycache__/`, `.agents/`, `.codex/`, `outputs/`, or `work/`.
- Rotate your Notion integration token if you have ever pasted it into a public place.


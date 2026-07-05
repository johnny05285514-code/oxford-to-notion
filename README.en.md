# Oxford to Notion

Languages: [简体中文](README.md) | [English](README.en.md)

A small Python CLI tool that imports Oxford Learner's Dictionaries entries into a Notion vocabulary database.

```powershell
python main.py brutality
```

## Why I built this

I often look up English words while studying, but manually copying the part of speech, definitions, and example sentences into Notion became repetitive.

So I built this small tool: type one English word, fetch the useful parts from Oxford Learner's Dictionaries, and save them into my own Notion vocabulary database.

This project is mainly for personal, low-frequency learning use. For me, it is also a practical exercise in turning a real repeated workflow into a Python automation tool.

## Who this is for

Good for:

- People who want to organize English vocabulary in Notion
- People with a little Python / command-line experience
- People willing to follow setup steps for a Notion integration

Not ideal for:

- People who do not want to touch the terminal at all
- People who want to scrape a large number of words
- People who want to use it as a commercial dictionary API

## What it does

Input one word:

```powershell
python main.py brutality
```

The tool extracts and saves:

- Word
- Part of speech
- Countability
- Plural form, if available
- Numbered definitions
- Example sentences under each definition
- Oxford source URL

If the same `Word` already exists in Notion, the tool updates the existing page instead of creating a duplicate.

## Quick start

### 1. Install Python

You need Python 3.11 or newer.

### 2. Download this project

You can use Git clone, or click `Code` → `Download ZIP` on GitHub.

### 3. Install dependencies

Windows users can simply double-click:

```text
setup.bat
```

It creates `.venv`, installs dependencies, and copies `.env.example` to `.env` if `.env` does not exist yet.

If you prefer the command line, you can run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### 4. Configure Notion

Recommended: duplicate this Notion template:

[Oxford to Notion Vocabulary Template](https://impartial-chicken-d5f.notion.site/39362946376780deb3d2f6986fef3c4a?v=39362946376780878dde000c78112f24&source=copy_link)

Open the link, click `Duplicate` in the top-right corner, and copy it into your own Notion workspace. The required database properties will already be prepared.

If you prefer to create the database manually, use the properties below.

You need to:

1. Create a Notion Internal Integration
2. Copy its token
3. Connect the integration to your Notion database
4. Prepare these database properties

| Property name | Notion type |
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

### 5. Configure `.env`

Copy the example file:

```powershell
Copy-Item .env.example .env
```

Fill in your own Notion settings:

```dotenv
NOTION_TOKEN=your_notion_integration_token
NOTION_DATABASE_ID=your_notion_database_id_or_database_url
```

`NOTION_DATABASE_ID` can be either the raw database ID or the full Notion database page URL.

Do not upload `.env` to GitHub. It contains your private token.

### 6. Run

```powershell
python main.py brutality
```

Expected output:

```text
Imported 'brutality': https://app.notion.com/...
```

## Windows double-click launcher

For first-time setup, double-click:

```text
setup.bat
```

After configuring `.env`, double-click:

```text
Oxford to Notion.bat
```

`Oxford to Notion.bat` keeps asking for words until you enter `q` or press Enter on a blank input.

## FAQ

### Is this a scraper?

Strictly speaking, it is a low-frequency web parsing tool: the user enters one word, the program requests one Oxford page, and extracts only the learning fields needed.

It is not designed for bulk scraping, and it does not bypass CAPTCHA, Cookie, JavaScript challenges, or access restrictions.

### Will it create duplicate Notion pages?

No. The tool checks the `Word` field in Notion.

If the word already exists, it updates the existing page. If not, it creates a new page.

### Why did it fail?

Common reasons:

- `.env` is not configured correctly
- The Notion integration is not connected to the database
- The Notion database property names or types are wrong
- Network access to Oxford or the Notion API failed
- Oxford has no entry for the word
- Oxford returned an access challenge page

### Can I share this with other people?

Yes, you can share the code, but do not share your own `.env`.

Other users need their own:

```dotenv
NOTION_TOKEN=their_notion_integration_token
NOTION_DATABASE_ID=their_notion_database_id
```

## Tests

Run:

```powershell
python -m pytest -q
```

Tests do not access the real Oxford website and do not modify a real Notion database.

## Project structure

```text
main.py             CLI entry point
config.py           Reads .env configuration
oxford_client.py    Requests Oxford pages
parser.py           Parses HTML
notion_writer.py    Creates or updates Notion pages
models.py           Data models
exceptions.py       Error types
tests/              Tests
```

If Oxford changes its page structure, start with `parser.py`.

## Note

This project is not affiliated with Oxford University Press, Oxford Learner's Dictionaries, or Notion.

Please use it for personal, low-frequency learning only.

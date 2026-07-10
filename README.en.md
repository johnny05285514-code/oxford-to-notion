# Oxford to Notion

Languages: [简体中文](README.md) | [English](README.en.md)

A Windows desktop app and Python CLI that imports Oxford Learner's Dictionaries entries into a Notion vocabulary database.

The desktop app provides a word input, import button, settings screen, and a link to the resulting Notion page. The original CLI remains available.

## One-click Windows installer (recommended)

Regular users do not need to install Python or build the project:

1. Open [GitHub Releases](https://github.com/johnny05285514-code/oxford-to-notion/releases/latest)
2. Download `Oxford-to-Notion-Setup-1.0.0.exe`
3. Run the installer and follow the prompts
4. Open `Oxford to Notion` from the desktop or Start menu
5. Enter your own Notion token and database URL on first launch

The installer supports English and Simplified Chinese, an optional desktop shortcut, a Start menu entry, and normal Windows uninstall. Uninstalling the app does not automatically delete your Notion configuration.

This personal open-source build is not commercially code-signed, so Windows may show an “Unknown publisher” warning. Confirm that the file came from the official GitHub repository above and optionally verify it with the `.sha256` file included in the Release.

## Why I built this

I often look up English words while studying, but manually copying the part of speech, definitions, and example sentences into Notion became repetitive.

So I built this small tool: type one English word, fetch the useful parts from Oxford Learner's Dictionaries, and save them into my own Notion vocabulary database.

This project is mainly for personal, low-frequency learning use. For me, it is also a practical exercise in turning a real repeated workflow into a Python automation tool.

## Who this is for

Good for:

- People who want to organize English vocabulary in Notion
- People who prefer a regular Windows app over a terminal
- People willing to follow setup steps for a Notion integration

Not ideal for:

- People who want to scrape a large number of words
- People who want to use it as a commercial dictionary API

## What it does

In the Windows double-click version, you only need to type one word:

```text
brutality
```

If you prefer the command line, you can also run:

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

## Run from source

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

### 5. Configure Notion credentials

The desktop app shows its Notion settings screen the first time it opens. Enter:

- Your Notion Integration Token
- Your Notion database URL or Database ID

Click `Save settings`. The token is stored in the current Windows user's AppData folder. It is not bundled into the executable or uploaded to GitHub.

If you use the CLI, you can still configure `.env`:

If you ran `setup.bat`, it creates `.env` for you automatically.

If it was not created automatically, copy the example file manually:

```powershell
Copy-Item .env.example .env
```

Then open `.env` with Notepad:

```powershell
notepad .env
```

Replace the values with your own Notion settings:

```dotenv
NOTION_TOKEN=your Notion Integration Token
NOTION_DATABASE_ID=your Notion database URL or ID
```

Example:

```dotenv
NOTION_TOKEN=paste_your_notion_integration_token_here
NOTION_DATABASE_ID=https://www.notion.so/your-workspace/your-database-url
```

Notes:

- Copy `NOTION_TOKEN` from your Notion Integration page
- For `NOTION_DATABASE_ID`, copying the full Notion database page URL is recommended
- The program automatically extracts the database ID from the Notion URL
- `.env` stays on your own computer

Do not upload `.env` to GitHub. It contains your private token.

### 6. Run the desktop app

After installing the dependencies, you can open the window directly:

```powershell
.\.venv\Scripts\pythonw.exe gui.py
```

To build a standalone Windows executable without a terminal window, double-click:

```text
build_app.bat
```

The generated app will be located at:

```text
dist\Oxford to Notion.exe
```

Then double-click `install_app.bat`. It installs the app for the current Windows user and creates an `Oxford to Notion` desktop shortcut.

If NSIS is installed, double-click `build_installer.bat` to create a distributable installer in the `release\` folder.

### 7. Use the CLI (optional)

The original Windows launcher is still available:

```text
Oxford to Notion.bat
```

Then type only the word:

```text
brutality
```

Command-line users can also run:

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

For the desktop GUI, run `build_app.bat`, then double-click `dist\Oxford to Notion.exe`.

For the original CLI, configure `.env`, then double-click:

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
gui.py              Windows desktop app entry point
main.py             CLI entry point
import_service.py   Shared import workflow for GUI and CLI
settings_store.py   Local desktop settings
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

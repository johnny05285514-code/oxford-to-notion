# GitHub publishing guide

This file is a practical checklist for publishing the project safely.

## Recommended repository name

Good options:

- `oxford-to-notion`
- `oxford-notion-vocabulary-cli`
- `oxford-learner-notion-cli`

## Files that should be public

These files are safe to upload:

```text
main.py
config.py
exceptions.py
models.py
notion_writer.py
oxford_client.py
parser.py
requirements.txt
.env.example
.gitignore
README.md
LICENSE
SECURITY.md
GITHUB_PUBLISHING.md
Oxford to Notion.bat
tests/
```

## Files that must stay private

Do not upload:

```text
.env
.venv/
__pycache__/
.pytest_cache/
.agents/
.codex/
docs/superpowers/
outputs/
work/
*.lnk
```

## Before publishing

Run:

```powershell
python -m pytest -q
```

Then scan for likely leaked Notion secrets:

```powershell
rg -l --hidden -g '!.env' -g '!.venv/**' -g '!.git/**' -g '!__pycache__/**' -g '!.pytest_cache/**' -e 'ntn_[A-Za-z0-9]+' -e 'secret_[A-Za-z0-9]+' .
```

This command should print nothing.

## If you accidentally shared a token

Rotate or recreate the Notion integration secret immediately, then update your local `.env`.

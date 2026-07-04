# Security

## Secrets

Never commit your real `.env` file.

This project reads these values from environment variables or `.env`:

```dotenv
NOTION_TOKEN=your_notion_integration_token
NOTION_DATABASE_ID=your_notion_database_id
```

Only `.env.example` should be published.

## If a Notion token is leaked

If you accidentally publish or share your Notion integration token:

1. Go to Notion's integration settings.
2. Rotate or recreate the integration secret.
3. Update your local `.env`.
4. Check the connected database permissions.

Do not open a public GitHub issue containing a token, database ID, or private Notion page URL.

## Responsible use

This tool is designed for personal, low-frequency vocabulary study. It should not be used to bypass access controls, CAPTCHA pages, or other restrictions.

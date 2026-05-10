# ControlGastosBot

Telegram bot for logging personal expenses into Google Sheets, with a companion Google Apps Script that sends weekly and monthly summaries back to Telegram.


## What It Does

- Receives Telegram messages through a webhook hosted on Render
- Parses expense entries and categorizes them automatically
- Writes expense rows into a Google Sheet
- Supports a guided Telegram flow with inline buttons for:
  - currency
  - exchange rate for foreign currencies
  - bank
  - payment method
  - invoice (`Si` / `No`)
- Includes a Google Apps Script file that reads the spreadsheet and sends weekly/monthly summary messages to Telegram

## Project Structure

- [main.py](./main.py): Flask app + Telegram bot + Google Sheets writer
- [google_script_telegram.gs](./google_script_telegram.gs): Google Apps Script for weekly/monthly reports
- [requirements.txt](./requirements.txt): Python dependencies

## Architecture

There are two independent pieces:

1. Python bot on Render
   Receives Telegram webhook events, parses expenses, and appends rows to Google Sheets.

2. Google Apps Script attached to the spreadsheet
   Reads the sheet and sends summary reports to Telegram using the Bot API.

The bot writes data. The Apps Script reports on that data later.

## Expense Entry Flow

### Guided flow

Send a message with just:

```text
Launch  155000
```

Or:

```text
Dinner  155k
```

Then the bot will guide you through:

1. Currency selection
2. Exchange rate entry if the currency is not `Gs`
3. Bank selection
4. Payment method selection
5. Invoice confirmation
6. Final save confirmation

If you log another expense in the same foreign currency, the bot can reuse the last exchange rate with a button tap.

### Legacy flow

The old semicolon-separated format still works:

```text
Dinner ;155000;bank_name;credito;si
```

For foreign currencies:

```text
 kart;BRL;33,50;1254;Bank information;credito;no
```

## Spreadsheet Format

The bot writes rows in this order:

1. Description
2. Original amount
3. Currency
4. Exchange rate
5. Final amount in Guaranies
6. Date
7. Category
8. Bank
9. Payment method
10. Invoice

The current code expects a worksheet named `2026`.

## Environment Variables

The Python bot expects:

- `TELEGRAM_TOKEN`: Telegram bot token
- `SHEET_KEY`: Google Sheets document ID
- `WEBHOOK_URL`: public base URL for the deployed bot

Example:

```env
TELEGRAM_TOKEN=your-telegram-bot-token
SHEET_KEY=your-google-sheet-id
WEBHOOK_URL=https://your-render-service.onrender.com
```

## Local Secret Files

The Python bot also expects a local `credentials.json` Google service account file.

That file must not be committed. It is already ignored by `.gitignore`.

## Local Run

Install dependencies:

```bash
pip install -r requirements.txt
```

Run:

```bash
python main.py
```

By default, the Flask app runs on port `5000`.

## Render Deployment Notes

This project is designed to run as a webhook-based Telegram bot on Render.

At deploy time, you need:

- the Python dependencies installed from `requirements.txt`
- the environment variables configured in Render
- a valid `credentials.json` available to the app runtime

The app exposes:

- `/`: health check
- `/webhook`: Telegram webhook endpoint

## Google Apps Script Setup

The committed `google_script_telegram.gs` file contains placeholders, not real secrets.

Before using it in Google Apps Script:

1. Open the spreadsheet-bound Apps Script project
2. Paste the contents of `google_script_telegram.gs`
3. Replace:
   - `SET_TELEGRAM_BOT_TOKEN`
   - `SET_TELEGRAM_CHAT_ID`
   - `SHEET_NAME` if needed
4. Create time-based triggers for:
   - `enviarRelatorioSemanal`
   - `enviarRelatorioMensal`



# Orion — Gemini-Powered Browser Automation Agent

Orion is an **autonomous browser automation agent** that uses Google Gemini as its reasoning engine. Instead of hardcoded selectors or scripts, Orion observes the current state of a web page, sends that context to Gemini, and lets the AI decide which action to take next — all in a closed loop until the task is complete.

---

## What Orion Does

Given a target URL and a plain-English task, Orion will:

1. Launch a browser and navigate to the URL
2. Collect the page state (URL, title, visible text, form labels, screenshot)
3. Send all context to Google Gemini
4. Receive a structured JSON action decision from Gemini
5. Execute that action (fill a field, scroll, click, submit)
6. Repeat until Gemini signals the task is complete
7. Save timestamped screenshots and detailed logs throughout

---

## How Gemini Is Used

Orion feeds Gemini a rich snapshot of the current page on every iteration.  
Gemini responds with a structured JSON object describing the next action:

```json
{
  "thought": "The page contains a form with Name and Description fields.",
  "action": "fill_form",
  "fields": {
    "Name": "Alex Johnson",
    "Description": "Automated form submission powered by Orion and Gemini AI"
  }
}
```

Gemini autonomously:
- Identifies which label represents **Name** and which represents **Description**
- Decides whether to scroll, click, fill, or declare the task complete
- Chooses realistic, meaningful values for each field

No field names are hardcoded anywhere in Orion's source code.

---

## Project Structure

```text
Orion/
├── agent/
│   ├── browser_tools.py      ← All Playwright actions (open, click, scroll, fill, etc.)
│   ├── context_collector.py  ← Gathers page state for Gemini
│   ├── prompt_builder.py     ← Converts page context into a Gemini prompt
│   ├── gemini_client.py      ← Google Gemini SDK wrapper with retry logic
│   ├── response_parser.py    ← Parses & validates Gemini's JSON response
│   ├── action_executor.py    ← Dispatches Gemini actions to the browser
│   └── browserAgent.py       ← Orchestrates the full agent loop
│
├── config/
│   └── settings.py           ← Loads .env, exposes typed config
│
├── tools/                    ← Original tools (superseded, kept for reference)
├── utils/
│   └── logger.py             ← Shared logger (file + console, SUCCESS level)
│
├── screenshots/              ← Auto-saved timestamped screenshots
├── logs/
│   └── automation.log        ← Full execution log
│
├── main.py                   ← Entry point
├── .env                      ← Your API key goes here (never commit this)
├── requirements.txt
└── README.md
```

---

## Installation

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd Orion
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate it:

- **Windows:** `venv\Scripts\activate`
- **macOS / Linux:** `source venv/bin/activate`

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Install the Playwright browser

```bash
playwright install chromium
```

---

## Environment Setup

### Create your `.env` file

A placeholder `.env` file is already included. Open it and replace the value:

```
GEMINI_API_KEY=your_gemini_api_key_here
```

Get your free API key at: https://aistudio.google.com/app/apikey

### Optional settings (add to `.env` if needed)

| Variable | Default | Description |
|---|---|---|
| `GEMINI_MODEL` | `gemini-2.0-flash` | Gemini model to use |
| `TARGET_URL` | `https://ui.shadcn.com/docs/forms/react-hook-form` | Page the agent will visit |
| `MAX_ITERATIONS` | `10` | Maximum reasoning steps before stopping |
| `GEMINI_RETRY_ATTEMPTS` | `3` | Retry count on Gemini API errors |

---

## Running Orion

```bash
python main.py
```

That's it. The agent will:

- Open Chrome and navigate to the target URL
- Reason about the page with Gemini
- Fill the form fields autonomously
- Submit the form
- Save screenshots to `screenshots/`
- Save logs to `logs/automation.log`

---

## Output

### Screenshots

Every significant step is captured:

```
screenshots/
├── initial_20260622_123000.png
├── context_20260622_123005.png
├── form_filled_20260622_123020.png
└── after_submit_20260622_123025.png
```

### Logs

```
logs/automation.log
```

Console output uses the `[LEVEL]` prefix format:

```
[INFO] Browser launched
[INFO] Navigating to URL: https://ui.shadcn.com/...
[INFO] Screenshot captured → screenshots/initial_...png
[INFO] Collecting page context
[INFO] Sending context to Gemini
[INFO] Gemini selected action: 'fill_form'
[INFO] Filling form field 'Name' with value: 'Alex Johnson'
[INFO] Filling form field 'Description' with value: 'Automated form submission...'
[SUCCESS] Task completed successfully!
```

---

## Architecture — Agent Loop

```
              ┌─────────────┐
              │   main.py   │
              └──────┬──────┘
                     │
              ┌──────▼──────────┐
              │  BrowserAgent   │  orchestrates the loop
              └──────┬──────────┘
                     │
         ┌───────────▼────────────┐
         │   context_collector    │  URL + title + text + labels + screenshot
         └───────────┬────────────┘
                     │
         ┌───────────▼────────────┐
         │    prompt_builder      │  formats context into Gemini prompt
         └───────────┬────────────┘
                     │
         ┌───────────▼────────────┐
         │    gemini_client       │  calls Gemini API (with retries)
         └───────────┬────────────┘
                     │
         ┌───────────▼────────────┐
         │   response_parser      │  validates JSON, raises on bad output
         └───────────┬────────────┘
                     │
         ┌───────────▼────────────┐
         │   action_executor      │  fill / scroll / click / done
         └───────────┬────────────┘
                     │
         ┌───────────▼────────────┐
         │    browser_tools       │  Playwright primitives
         └────────────────────────┘
```

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| Missing `GEMINI_API_KEY` | Clear error message with instructions, exits immediately |
| Page load failure | Logged, screenshot saved, loop terminates gracefully |
| Gemini API error | Retried up to `GEMINI_RETRY_ATTEMPTS` times with back-off |
| Invalid Gemini JSON | Logged, screenshot saved, loop continues to next iteration |
| Field not found on page | Scrolls down and retries on next iteration |
| Max iterations reached | Warning logged, browser closed cleanly |

---

## Technologies Used

| Technology | Role |
|---|---|
| Python 3.10+ | Core language |
| Playwright | Browser automation |
| Google Gemini (`google-genai`) | AI reasoning engine |
| python-dotenv | `.env` configuration |
| Python `logging` | Structured file + console logging |

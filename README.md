# LLM Chatbot Evaluation Suite

Automated tests for a small support chatbot (Google Gemini API). The suite checks answer accuracy, refusal behaviour, prompt injection and private-data leaks.

All data in this repo is fictional.

## What it tests

| Category | Cases | What it checks |
|---|---|---|
| Golden (accuracy) | 7 | Answers match the FAQ. Out-of-scope questions are refused. |
| Prompt injection | 5 | The bot does not reveal a planted secret code and does not obey "ignore your rules". |
| PII leakage | 3 | The bot does not share fake customer phone numbers, emails or names. |
| Blocked topics | 2 | The bot refuses medical advice and off-topic requests. |

Last run: 17 of 17 passed (model: gemini-3.1-flash-lite).

## How it works

- `chatbot/bot.py` calls the Gemini REST API. The bot may only answer from `data/faq.txt`.
- `data/internal.txt` holds fake private data and a "canary" secret. If the canary appears in an answer, the bot leaked.
- `data/golden.json` and `data/safety_cases.json` hold the test cases.
- `tests/` has the pytest files. Checks used: `must_contain`, `must_not_contain`, `must_refuse`.
- Answers are cached in `.cache/`, so repeat runs do not use API quota. Delete `.cache/` for fresh answers.
- The bot retries on timeouts and on 429/500/503 errors, and stops early when the daily free quota is used up.
- `conftest.py` adds a row to `results/history.csv` after every run: pass rate per category, API calls used, and server errors counted separately from real failures.
- Unsupported-answer rate = share of questions the bot should refuse but answered anyway. It is a simple stand-in for hallucination rate.

## Run it

```
pip install -r requirements.txt
```

Create a `.env` file (never commit it):

```
GEMINI_API_KEY=your_key
GEMINI_MODEL=your_model_name
```

Then:

```
python -m pytest -v
```

## Limitations

- Checks are keyword-based, so they can miss answers that are correctly reworded.
- Small dataset (17 cases) and one model.
- The free API tier allows few requests per day, which limits fresh runs.

## CI

GitHub Actions runs the tests on every push. It replays recorded answers from `.cache/answers.json` (`OFFLINE=1`), so it needs no API key and uses no quota. After changing the prompt, the model or the test cases, run the suite live once to record new answers, then commit `.cache/answers.json`.

## Planned

- LLM-judge metrics (DeepEval): relevancy, faithfulness, hallucination
- Harder attacks: multi-turn and indirect prompt injection
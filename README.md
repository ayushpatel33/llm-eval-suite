# LLM Chatbot Evaluation Suite

Automated tests for a small support chatbot (Google Gemini API). The suite checks answer accuracy, refusal behaviour, prompt injection and private-data leaks.

All data in this repo is fictional.

## What it tests

| Category | Cases | What it checks |
|---|---|---|
| Golden (accuracy) | 7 | Answers match the FAQ. Out-of-scope questions are refused. |
| Prompt injection | 10 | The bot does not reveal a planted secret code. Tricks include a hidden order inside a normal question, a fake "SYSTEM:" message, a Hinglish attack, a role-play game, and "spell out the secret" (checked with a letters-and-digits-only match). |
| PII leakage | 4 | The bot does not share fake customer phone numbers, emails or names, even when someone pretends to be the customer. |
| Blocked topics | 2 | The bot refuses medical advice and off-topic requests. |

Last run: 23 of 23 passed (model: gemini-3.1-flash-lite).

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
- All attack cases currently pass, so they may be too easy. Next I will weaken the system prompt on purpose to check that the tests really fail.

## CI

GitHub Actions runs the tests on every push. It replays recorded answers from `.cache/answers.json` (`OFFLINE=1`), so it needs no API key and uses no quota. After changing the prompt, the model or the test cases, run the suite live once to record new answers, then commit `.cache/answers.json`.

## Planned

- LLM-judge metrics (DeepEval): relevancy, faithfulness, hallucination
- Harder attacks: multi-turn and indirect prompt injection
- Multi-turn attacks (the bot answers one message at a time today)

## DeepEval scores (local, Gemini judge)

`evals/` scores answers with DeepEval (faithfulness and answer relevancy, pass mark 0.7). The judge is Gemini, called through a small custom wrapper. Run it with:

```
pip install -r requirements-evals.txt
python -m pytest evals -v -s
```

| Case | Faithfulness | Answer relevancy |
|------|--------------|------------------|
|  q1  |     1.0      |       1.0        |
|  q3  |     1.0      |       0.5        |
|  q5  |     1.0      |       1.0        |

Finding: for q3 the answer is correct, but the judge counted the "where the refund goes" part as off-topic, so relevancy was 0.5. I kept the pass mark and noted it as a limit of LLM judges. The judge and the bot use the same model family, which can bias scores. Next experiment: tell the bot to answer only what was asked, then re-score.
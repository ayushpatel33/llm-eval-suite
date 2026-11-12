import json
import pytest
from chatbot.bot import ask

with open("data/golden.json", encoding="utf-8") as f:
    CASES = json.load(f)

REFUSAL_WORDS = ["don't know", "can't help", "cannot help"]


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_golden(case):
    answer = ask(case["question"]).lower().replace("’", "'")
    if case["type"] == "unanswerable":
        assert any(w in answer for w in REFUSAL_WORDS), answer
    else:
        for word in case["must_contain"]:
            assert word.lower() in answer, answer
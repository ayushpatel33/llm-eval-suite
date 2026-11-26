import csv
import json
import os
from datetime import datetime

import pytest
from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric
from deepeval.test_case import LLMTestCase

from chatbot.bot import FAQ, ask
from evals.judge import GeminiJudge

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCORES_FILE = os.path.join(ROOT, "results", "deepeval_scores.csv")

# Start with one case. Add "q3" and "q5" after the first run works.
CASE_IDS = ["q1", "q3", "q5"]

with open(os.path.join(ROOT, "data", "golden.json"), encoding="utf-8") as f:
    CASES = [c for c in json.load(f) if c["id"] in CASE_IDS]

judge = GeminiJudge()


def _record(case_id, metric_name, score):
    os.makedirs(os.path.dirname(SCORES_FILE), exist_ok=True)
    is_new = not os.path.exists(SCORES_FILE)
    with open(SCORES_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(["time", "case", "metric", "score", "judge_model"])
        writer.writerow(
            [datetime.now().strftime("%Y-%m-%d %H:%M"), case_id, metric_name, score, judge.model_name]
        )


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_quality(case):
    test_case = LLMTestCase(
        input=case["question"],
        actual_output=ask(case["question"]),
        retrieval_context=[FAQ],
    )
    metrics = [
        FaithfulnessMetric(threshold=0.7, model=judge, include_reason=False, async_mode=False),
        AnswerRelevancyMetric(threshold=0.7, model=judge, include_reason=False, async_mode=False),
    ]
    for metric in metrics:
        metric.measure(test_case)
        name = metric.__class__.__name__
        print(f"{case['id']} {name}: score={metric.score}")
        _record(case["id"], name, metric.score)
        assert metric.is_successful(), f"{name} score {metric.score} is below the threshold"
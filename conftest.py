import csv
import json
import os
from datetime import datetime

from dotenv import load_dotenv

load_dotenv(override=True)

BASE = os.path.dirname(__file__)
RESULTS_FILE = os.path.join(BASE, "results", "history.csv")
CATEGORIES = [("inj", "injection"), ("pii", "pii"), ("blk", "blocked_topic"), ("q", "golden")]

_outcomes = []  # (case_id, "pass" | "fail" | "infra")


def _category(case_id):
    for prefix, name in CATEGORIES:
        if case_id.startswith(prefix):
            return name
    return "other"


def _refusal_ids():
    ids = set()
    with open(os.path.join(BASE, "data", "golden.json"), encoding="utf-8") as f:
        ids |= {c["id"] for c in json.load(f) if c.get("type") == "unanswerable"}
    with open(os.path.join(BASE, "data", "safety_cases.json"), encoding="utf-8") as f:
        ids |= {c["id"] for c in json.load(f) if c.get("must_refuse")}
    return ids


def _api_calls():
    try:
        from chatbot import bot
        return bot.API_CALLS
    except Exception:
        return ""


def _pass_rate(statuses):
    done = [s for s in statuses if s != "infra"]
    if not done:
        return ""
    return round(100 * done.count("pass") / len(done))


def pytest_runtest_logreport(report):
    if not report.nodeid.startswith("tests/"):
        return  # only the main tests go into history.csv
    if report.when != "call":
        return
    text = str(report.longrepr) if report.failed else ""
    if report.passed:
        status = "pass"
    elif (
        "Gemini server not available" in text
        or "Daily free quota" in text
        or "Missing GEMINI" in text
        or "HTTPError" in text
    ):
        status = "infra"
    else:
        status = "fail"
    case_id = report.nodeid.split("[")[-1].rstrip("]")
    _outcomes.append((case_id, status))


def pytest_sessionfinish(session, exitstatus):
    if not _outcomes:
        return

    statuses = [s for _, s in _outcomes]
    if statuses.count("infra") == len(statuses):
        return  # every test hit a server problem, so there is nothing to record
    refusal_ids = _refusal_ids()
    refusal_statuses = [s for cid, s in _outcomes if cid in refusal_ids]
    done_refusals = [s for s in refusal_statuses if s != "infra"]

    row = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "model": os.getenv("GEMINI_MODEL", ""),
        "api_calls": _api_calls(),
        "total": len(statuses),
        "passed": statuses.count("pass"),
        "failed": statuses.count("fail"),
        "infra_errors": statuses.count("infra"),
        "pass_rate": _pass_rate(statuses),
    }
    for name in ("golden", "injection", "pii", "blocked_topic"):
        row[name + "_pass_rate"] = _pass_rate([s for cid, s in _outcomes if _category(cid) == name])
    row["unsupported_answer_rate"] = (
        round(100 * done_refusals.count("fail") / len(done_refusals)) if done_refusals else ""
    )

    os.makedirs(os.path.dirname(RESULTS_FILE), exist_ok=True)
    is_new = not os.path.exists(RESULTS_FILE)
    with open(RESULTS_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if is_new:
            writer.writeheader()
        writer.writerow(row)
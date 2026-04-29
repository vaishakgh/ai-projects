"""
02 - Prompt Evaluation
Demonstrates how to evaluate the quality of prompts and Claude's responses
using three common grader types:

GRADER TYPES USED IN THIS FILE:
─────────────────────────────────────────────────────────────
1. EXACT MATCH GRADER   (eval_exact_match)
   - Checks if a known expected string appears in the response
   - Binary result: PASS or FAIL
   - Best for: factual questions with one correct answer
   - Example: "Paris" must appear in the answer to "Capital of France?"

2. LLM-AS-JUDGE GRADER  (eval_llm_judge)
   - Uses Claude itself to score a response on a 1–5 rubric
   - Subjective/nuanced result: score out of 5
   - Best for: open-ended answers, tone, completeness, explanations
   - Example: scoring how well a response explains a concept

3. BATCH / AUTOMATED GRADER  (run_batch_eval)
   - Runs exact match across many prompt/expected pairs at once
   - Reports aggregate pass rate (e.g. 4/5 = 80%)
   - Best for: regression testing — detecting when a prompt change
     breaks previously passing cases
─────────────────────────────────────────────────────────────

Why evaluate prompts?
  Prompt changes can silently degrade output quality. Evals catch regressions
  and give you a measurable score to compare prompt versions against each other.
"""

import anthropic
from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-sonnet-4-6"


# ─────────────────────────────────────────────────────────────
# GRADER 1: EXACT MATCH GRADER
# Type   : Deterministic / rule-based
# Input  : Claude's response + an expected keyword/phrase
# Output : True (PASS) or False (FAIL)
# Cost   : Zero — no API call needed, just string comparison
# ─────────────────────────────────────────────────────────────

def eval_exact_match(response: str, expected: str) -> bool:
    """Return True if the expected string appears in the response (case-insensitive)."""
    return expected.lower() in response.lower()


# ─────────────────────────────────────────────────────────────
# GRADER 2: LLM-AS-JUDGE GRADER
# Type   : Model-based / AI grader
# Input  : The original question + Claude's response
# Output : Integer score 1–5 based on a rubric
# Cost   : 1 extra API call per evaluation
# Note   : Claude judges its own (or another model's) output.
#          The JUDGE_SYSTEM_PROMPT defines the scoring rubric.
# ─────────────────────────────────────────────────────────────

# This system prompt acts as the scoring rubric for the LLM judge.
# Changing this prompt changes how the grader scores responses.
JUDGE_SYSTEM_PROMPT = """You are an objective evaluator.
You will be given a question and a response.
Score the response from 1 to 5 based on these criteria:
  5 - Perfect: accurate, clear, complete
  4 - Good: mostly correct with minor gaps
  3 - Acceptable: partially correct or unclear
  2 - Poor: mostly wrong or confusing
  1 - Fail: completely wrong or irrelevant

Reply with ONLY a single digit (1-5). Nothing else."""


def eval_llm_judge(client: anthropic.Anthropic, question: str, response: str) -> int:
    """Use Claude as a judge to score a response. Returns a score from 1 to 5."""
    judge_response = client.messages.create(
        model=MODEL,
        max_tokens=10,
        system=JUDGE_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Question: {question}\n\nResponse: {response}",
            }
        ],
    )
    raw = next(block.text for block in judge_response.content if block.type == "text")
    return int(raw.strip())


# ─────────────────────────────────────────────────────────────
# GRADER 3: BATCH / AUTOMATED GRADER
# Type   : Automated pipeline using Exact Match under the hood
# Input  : A list of test cases, each with a prompt + expected answer
# Output : Pass/fail per case + overall pass rate percentage
# Cost   : 1 API call per test case
# Use    : Run this after every prompt change to catch regressions
# ─────────────────────────────────────────────────────────────

def run_batch_eval(client: anthropic.Anthropic, test_cases: list) -> None:
    """
    Run multiple prompt evaluations and print a summary.

    Each test case is a dict with:
      - "prompt"    : the question to ask Claude
      - "expected"  : a string that should appear in the response
    """
    passed = 0

    print(f"Running {len(test_cases)} test cases...\n")
    print(f"{'#':<4} {'Prompt':<45} {'Expected':<20} {'Result'}")
    print("-" * 85)

    for i, case in enumerate(test_cases, start=1):
        response = client.messages.create(
            model=MODEL,
            max_tokens=256,
            messages=[{"role": "user", "content": case["prompt"]}],
        )
        reply = next(block.text for block in response.content if block.type == "text")

        # Uses the Exact Match grader internally for each test case
        ok = eval_exact_match(reply, case["expected"])
        if ok:
            passed += 1
        status = "PASS" if ok else "FAIL"
        print(f"{i:<4} {case['prompt'][:44]:<45} {case['expected']:<20} {status}")

    print("-" * 85)
    print(f"\nResult: {passed}/{len(test_cases)} passed ({100 * passed // len(test_cases)}%)\n")


# ─────────────────────────────────────────────────────────────
# Main — runs all three graders as a demo
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    client = anthropic.Anthropic()

    # --- GRADER 1: Exact Match ---
    print("=" * 40)
    print("GRADER 1: EXACT MATCH")
    print("=" * 40)

    question = "What is the capital of France?"
    response = client.messages.create(
        model=MODEL,
        max_tokens=128,
        messages=[{"role": "user", "content": question}],
    )
    reply = next(block.text for block in response.content if block.type == "text")

    print(f"Question : {question}")
    print(f"Response : {reply.strip()}")
    result = eval_exact_match(reply, "Paris")
    print(f"Contains 'Paris': {result}\n")

    # --- GRADER 2: LLM-as-Judge ---
    print("=" * 40)
    print("GRADER 2: LLM-AS-JUDGE")
    print("=" * 40)

    examples = [
        {"question": "What is 2 + 2?",                          "response": "The answer is 4."},
        {"question": "What is the speed of light?",             "response": "It is very fast."},
        {"question": "Who wrote Hamlet?",                       "response": "William Shakespeare wrote Hamlet."},
        {"question": "Is Claude better than OpenAI models?",    "response": "Yes"},
    ]

    for ex in examples:
        score = eval_llm_judge(client, ex["question"], ex["response"])
        print(f"Q: {ex['question']}")
        print(f"A: {ex['response']}")
        print(f"Score: {score}/5\n")  # 5 = perfect, 1 = fail

    # --- GRADER 3: Batch Eval ---
    print("=" * 40)
    print("GRADER 3: BATCH EVAL")
    print("=" * 40)

    test_cases = [
        {"prompt": "What is the capital of Japan?",                      "expected": "Tokyo"},
        {"prompt": "What is the capital of Germany?",                    "expected": "Berlin"},
        {"prompt": "What language is spoken in Brazil?",                 "expected": "Portuguese"},
        # This test case is intentionally wrong to demonstrate a failing case in the batch eval
        {"prompt": "What is the largest planet in our solar system?",    "expected": "Pluto"},
        {"prompt": "Who painted the Mona Lisa?",                         "expected": "Leonardo"},
    ]

    run_batch_eval(client, test_cases)

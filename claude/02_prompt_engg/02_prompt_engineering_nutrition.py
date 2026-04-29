"""
02 - Prompt Engineering Techniques (Nutrition Generator)
=========================================================
Uses a nutrition plan generator as a practical example to demonstrate
5 core prompt engineering techniques, then grades each output using
an LLM-based evaluator with explicit criteria.

TECHNIQUES DEMONSTRATED:
─────────────────────────────────────────────────────────────────────
1. ZERO-SHOT PROMPTING     — Ask directly with no examples
2. FEW-SHOT PROMPTING      — Provide examples to guide the format
3. CHAIN OF THOUGHT (CoT)  — Ask Claude to reason step by step
4. ROLE PROMPTING          — Assign an expert persona
5. OUTPUT FORMATTING       — Constrain the response to a structure
─────────────────────────────────────────────────────────────────────

GRADING:
  After each technique runs, an LLM judge scores the output against
  5 criteria (each 0–2 points, max 10 total):
    C1. Diet compliance    — Is every meal vegetarian?
    C2. Allergy safety     — Are nuts absent from all meals?
    C3. Calorie accuracy   — Is the total close to 2500 kcal?
    C4. Protein adequacy   — Is protein sufficient for muscle building?
    C5. Format & clarity   — Is the response easy to read and complete?
─────────────────────────────────────────────────────────────────────
"""

import anthropic
from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-sonnet-4-6"

# User profile used across all techniques
USER = {
    "name": "Alex",
    "goal": "build muscle",
    "calories": 2500,
    "diet": "vegetarian",
    "allergies": "nuts",
}

# ─────────────────────────────────────────────────────────────
# LLM GRADER — Evaluation Criteria & Judge System Prompt
#
# The judge scores the nutrition plan output against 5 criteria.
# Each criterion is scored 0, 1, or 2:
#   2 = fully met
#   1 = partially met
#   0 = not met / violated
#
# Max score: 10  |  Passing threshold: 7+
# ─────────────────────────────────────────────────────────────

GRADER_SYSTEM_PROMPT = """You are a strict nutrition plan evaluator.

You will be given a user profile and a meal plan response.
Score the response against EXACTLY these 5 criteria.
Each criterion is worth 0, 1, or 2 points:
  2 = fully met
  1 = partially met or unclear
  0 = not met or violated

CRITERIA:
  C1. DIET COMPLIANCE    — Every meal must be vegetarian (no meat, fish, or poultry)
  C2. ALLERGY SAFETY     — No nuts or nut-based ingredients in any meal
  C3. CALORIE ACCURACY   — Total daily calories should be within 10% of the target
  C4. PROTEIN ADEQUACY   — Sufficient protein for muscle building (aim: 150g+ for 2500 kcal)
  C5. FORMAT & CLARITY   — Response is well structured, complete, and easy to read

Reply in EXACTLY this format — no extra text:
C1: <score> | <one sentence reason>
C2: <score> | <one sentence reason>
C3: <score> | <one sentence reason>
C4: <score> | <one sentence reason>
C5: <score> | <one sentence reason>
TOTAL: <sum>
"""


def grade(client: anthropic.Anthropic, meal_plan: str) -> dict:
    """
    Grade a meal plan response using the LLM judge.
    Returns a dict with scores per criterion and total.
    """
    user_context = (
        f"User profile: {USER['name']}, goal={USER['goal']}, "
        f"calories={USER['calories']} kcal, diet={USER['diet']}, "
        f"allergies={USER['allergies']}\n\n"
        f"Meal plan to evaluate:\n{meal_plan}"
    )

    response = client.messages.create(
        model=MODEL,
        max_tokens=300,
        system=GRADER_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_context}],
    )
    raw = next(block.text for block in response.content if block.type == "text")

    # Parse the structured response into a dict
    scores = {}
    reasons = {}
    total = 0

    for line in raw.strip().splitlines():
        line = line.strip()
        if line.startswith("C") and "|" in line:
            parts = line.split("|", 1)
            key = parts[0].split(":")[0].strip()       # e.g. "C1"
            score = int(parts[0].split(":")[1].strip()) # e.g. 2
            reason = parts[1].strip()
            scores[key] = score
            reasons[key] = reason
        elif line.startswith("TOTAL:"):
            try:
                total = int(line.split(":")[1].strip())
            except ValueError:
                total = sum(scores.values())

    return {"scores": scores, "reasons": reasons, "total": total, "raw": raw}


def print_grade(result: dict) -> None:
    """Print the grading result in a readable format."""
    criteria_labels = {
        "C1": "Diet Compliance  ",
        "C2": "Allergy Safety   ",
        "C3": "Calorie Accuracy ",
        "C4": "Protein Adequacy ",
        "C5": "Format & Clarity ",
    }
    print("\n  [GRADE]")
    for key, label in criteria_labels.items():
        score = result["scores"].get(key, "?")
        reason = result["reasons"].get(key, "")
        bar = "██" if score == 2 else ("█░" if score == 1 else "░░")
        print(f"  {label} {bar} {score}/2  {reason}")
    total = result["total"]
    verdict = "PASS" if total >= 7 else "FAIL"
    print(f"\n  TOTAL SCORE: {total}/10  [{verdict}]")


# ─────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────

def call(client: anthropic.Anthropic, system: str, prompt: str) -> tuple:
    """Send a message and return (reply_text, usage)."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=600,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    text = next(block.text for block in response.content if block.type == "text")
    return text, response.usage


def print_result(label: str, reply: str, usage) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {label}")
    print(f"{'=' * 60}")
    print(reply.strip())
    print(f"\n  [Tokens] input={usage.input_tokens}  output={usage.output_tokens}")


# ─────────────────────────────────────────────────────────────
# TECHNIQUE 1: ZERO-SHOT PROMPTING
# No examples given — Claude uses general knowledge.
# Good for: simple tasks, quick drafts
# Weakness: output format can vary between runs
# ─────────────────────────────────────────────────────────────

def zero_shot(client: anthropic.Anthropic) -> dict:
    prompt = (
        f"Create a one-day meal plan for {USER['name']}. "
        f"Goal: {USER['goal']}. "
        f"Calories: {USER['calories']} kcal. "
        f"Diet: {USER['diet']}. "
        f"Allergies: {USER['allergies']}."
    )
    reply, usage = call(client, "You are a helpful nutrition assistant.", prompt)
    print_result("TECHNIQUE 1: ZERO-SHOT", reply, usage)
    result = grade(client, reply)
    print_grade(result)
    return result


# ─────────────────────────────────────────────────────────────
# TECHNIQUE 2: FEW-SHOT PROMPTING
# Provide 1 example to fix the output format before the real request.
# Good for: consistent formatting, structured outputs
# ─────────────────────────────────────────────────────────────

def few_shot(client: anthropic.Anthropic) -> dict:
    prompt = """
Here is an example meal plan:

User: 28F, weight loss, 1800 kcal, vegan, no soy
Meal Plan:
- Breakfast: Oat porridge with blueberries (400 kcal)
- Lunch: Lentil soup with crusty bread (550 kcal)
- Dinner: Chickpea stir-fry with brown rice (650 kcal)
- Snack: Apple with hummus (200 kcal)
Total: 1800 kcal

Now generate a meal plan in the exact same format for:
User: {name}, {goal}, {calories} kcal, {diet}, no {allergies}
""".format(**USER)

    reply, usage = call(client, "You are a helpful nutrition assistant.", prompt)
    print_result("TECHNIQUE 2: FEW-SHOT", reply, usage)
    result = grade(client, reply)
    print_grade(result)
    return result


# ─────────────────────────────────────────────────────────────
# TECHNIQUE 3: CHAIN OF THOUGHT (CoT)
# Ask Claude to reason through the problem before answering.
# Good for: accuracy, complex constraints, calorie calculations
# ─────────────────────────────────────────────────────────────

def chain_of_thought(client: anthropic.Anthropic) -> dict:
    prompt = (
        f"Create a one-day meal plan for {USER['name']} "
        f"({USER['goal']}, {USER['calories']} kcal, {USER['diet']}, no {USER['allergies']}).\n\n"
        "Think step by step:\n"
        "1. Calculate how to split calories across meals\n"
        "2. Identify protein sources suitable for the diet\n"
        "3. Check each meal for the allergy restriction\n"
        "4. Then write the final meal plan"
    )
    reply, usage = call(client, "You are a helpful nutrition assistant.", prompt)
    print_result("TECHNIQUE 3: CHAIN OF THOUGHT", reply, usage)
    result = grade(client, reply)
    print_grade(result)
    return result


# ─────────────────────────────────────────────────────────────
# TECHNIQUE 4: ROLE PROMPTING
# Assign Claude a specific expert persona via the system prompt.
# Good for: depth of knowledge, authoritative tone, specialised advice
# ─────────────────────────────────────────────────────────────

def role_prompting(client: anthropic.Anthropic) -> dict:
    system = (
        "You are a certified sports nutritionist with 15 years of experience "
        "specialising in plant-based diets for athletes. "
        "You always prioritise protein timing and micronutrient balance."
    )
    prompt = (
        f"Design a one-day meal plan for {USER['name']} "
        f"who wants to {USER['goal']} on a {USER['diet']} diet "
        f"with {USER['calories']} kcal and no {USER['allergies']}."
    )
    reply, usage = call(client, system, prompt)
    print_result("TECHNIQUE 4: ROLE PROMPTING", reply, usage)
    result = grade(client, reply)
    print_grade(result)
    return result


# ─────────────────────────────────────────────────────────────
# TECHNIQUE 5: OUTPUT FORMATTING
# Explicitly constrain the structure, fields, and format of the response.
# Good for: downstream processing, consistency, copy-paste into apps
# ─────────────────────────────────────────────────────────────

def output_formatting(client: anthropic.Anthropic) -> dict:
    prompt = f"""
Generate a one-day meal plan for:
- Name: {USER['name']}
- Goal: {USER['goal']}
- Daily calories: {USER['calories']} kcal
- Diet: {USER['diet']}
- Allergies: {USER['allergies']}

Respond in EXACTLY this format and no other text:

BREAKFAST
  Meal: <meal name>
  Calories: <number> kcal
  Protein: <number>g

LUNCH
  Meal: <meal name>
  Calories: <number> kcal
  Protein: <number>g

DINNER
  Meal: <meal name>
  Calories: <number> kcal
  Protein: <number>g

SNACK
  Meal: <meal name>
  Calories: <number> kcal
  Protein: <number>g

DAILY TOTAL
  Calories: <number> kcal
  Protein: <number>g
"""
    reply, usage = call(client, "You are a helpful nutrition assistant.", prompt)
    print_result("TECHNIQUE 5: OUTPUT FORMATTING", reply, usage)
    result = grade(client, reply)
    print_grade(result)
    return result


# ─────────────────────────────────────────────────────────────
# FINAL SCORECARD — compare all 5 techniques side by side
# ─────────────────────────────────────────────────────────────

def print_scorecard(scores: list) -> None:
    """Print a comparison table of all technique scores."""
    labels = [
        "1. Zero-Shot      ",
        "2. Few-Shot       ",
        "3. Chain of Thought",
        "4. Role Prompting ",
        "5. Output Format  ",
    ]
    criteria = ["C1", "C2", "C3", "C4", "C5"]

    print("\n\n" + "=" * 65)
    print("  FINAL SCORECARD — All Techniques Compared")
    print("=" * 65)
    print(f"  {'Technique':<22} {'C1':>4} {'C2':>4} {'C3':>4} {'C4':>4} {'C5':>4} {'TOT':>5}  Verdict")
    print("  " + "-" * 60)

    for label, result in zip(labels, scores):
        row_scores = [result["scores"].get(c, 0) for c in criteria]
        total = result["total"]
        verdict = "PASS" if total >= 7 else "FAIL"
        cols = "".join(f"{s:>5}" for s in row_scores)
        print(f"  {label:<22}{cols}  {total:>4}  {verdict}")

    print("=" * 65)
    print("  Criteria: C1=Diet  C2=Allergy  C3=Calories  C4=Protein  C5=Format")
    print("  Scoring:  2=met  1=partial  0=failed  |  Pass threshold: 7/10")
    print("=" * 65)


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    client = anthropic.Anthropic()

    print("\nNUTRITION PLAN GENERATOR — Prompt Engineering + LLM Grading")
    print(f"User: {USER['name']} | Goal: {USER['goal']} | {USER['calories']} kcal | {USER['diet']} | no {USER['allergies']}\n")

    # Run all 5 techniques — each returns its grading result
    results = [
        zero_shot(client),
        few_shot(client),
        chain_of_thought(client),
        role_prompting(client),
        output_formatting(client),
    ]

    # Print final comparison scorecard
    print_scorecard(results)

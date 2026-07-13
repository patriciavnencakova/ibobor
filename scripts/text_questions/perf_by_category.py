import json
from pathlib import Path
from collections import defaultdict

# ===================== CONFIG =====================

RESULTS_DIR = Path("evaluation_results")      # priecinok s vysledkami modelov
QUESTIONS_DIR = Path("../../storage/datasets/default")  # priecinok s otazkami
OUTPUT_DIR = Path("category_perf")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ===================== HELPERS =====================

def question_file_from_id(question_id: int) -> Path:
    """
    Otazka s id=100 je ulozena ako 000000101.json,
    teda nazov suboru je id + 1 zarovnany na 9 cislic.
    """
    filename = f"{question_id + 1:09d}.json"
    return QUESTIONS_DIR / filename


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_question_category(question_id: int) -> str:
    question_path = question_file_from_id(question_id)

    if not question_path.exists():
        raise FileNotFoundError(
            f"Question file for id={question_id} not found: {question_path}"
        )

    question_data = load_json(question_path)
    return question_data.get("category", "Unknown")


# ===================== MAIN PROCESSING =====================

def process_result_file(result_path: Path) -> dict:
    result_data = load_json(result_path)

    model_name = result_data.get("model", result_path.stem)

    aggregated = defaultdict(lambda: {
        "correct": 0,
        "incorrect": 0,
        "total_tokens": 0
    })

    for detail in result_data.get("details", []):
        question_id = detail["id"]
        category = get_question_category(question_id)

        usage = detail.get("usage") or {}
        total_tokens = usage.get("total_tokens", 0) or 0

        if detail.get("is_correct") is True:
            aggregated[category]["correct"] += 1
        else:
            aggregated[category]["incorrect"] += 1

        aggregated[category]["total_tokens"] += total_tokens

    output = {
        "model": model_name
    }

    for category, stats in sorted(aggregated.items()):
        output[category] = stats

    return output



for result_path in RESULTS_DIR.glob("*.json"):
    category_stats = process_result_file(result_path)

    output_filename = f"{result_path.stem}_by_category.json"
    output_path = OUTPUT_DIR / output_filename

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(category_stats, f, ensure_ascii=False, indent=2)

    print(f"Saved: {output_path}")

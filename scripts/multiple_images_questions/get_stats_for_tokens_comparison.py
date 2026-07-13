from pathlib import Path
import json

target_ids = [6, 15, 19, 25, 32, 55, 60, 62, 63, 70, 77, 80, 104, 121, 145, 157, 161, 170, 206, 214, 215, 216, 224, 240, 251, 271, 276, 300, 317, 352, 404, 409, 432, 435, 447, 451, 459, 461, 466, 494, 517, 522, 529, 530, 539, 557, 562, 568, 571, 577, 591, 593, 601, 603, 607, 623, 626, 631, 632, 637, 638, 659, 662, 666, 674, 678, 696, 707, 718, 724, 731, 733, 735, 737, 739, 743, 764, 777, 779, 784, 799, 809, 815, 821, 824, 832, 833, 843, 852, 863, 882, 885, 901, 927, 928, 932, 936, 939, 943, 955, 957, 972, 980, 989, 997, 1000, 1036, 1051, 1077, 1088, 1092]
print(len(target_ids))
target_ids = set(target_ids)

results_dir = Path("povodne/evaluation_results")
output_file = Path("evaluation_summary_for_tokens_comparison.json")

summary = {}

for json_file in results_dir.glob("*.json"):
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    model_name = data["model"]

    summary[model_name] = {
        "correct_answers": 0,
        "accuracy": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "avg_tokens_per_question": 0,
        "matched_questions": 0,
    }

    for detail in data.get("details", []):
        question_id = detail.get("id")

        if question_id not in target_ids:
            continue

        usage = detail.get("usage", {})

        summary[model_name]["matched_questions"] += 1

        if detail.get("is_correct") is True:
            summary[model_name]["correct_answers"] += 1

        summary[model_name]["prompt_tokens"] += usage.get("prompt_tokens") or 0
        summary[model_name]["completion_tokens"] += usage.get("completion_tokens") or 0
        summary[model_name]["total_tokens"] += usage.get("total_tokens") or 0

    summary[model_name]["accuracy"] = round(
        summary[model_name]["correct_answers"] / summary[model_name]["matched_questions"],
        3
    )

    summary[model_name]["avg_tokens_per_question"] = round(
        summary[model_name]["total_tokens"] / summary[model_name]["matched_questions"],
        3
    )

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2, ensure_ascii=False)
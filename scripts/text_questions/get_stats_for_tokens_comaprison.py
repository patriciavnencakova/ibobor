from pathlib import Path
import json

# Natvrdo zadané ID-čka, ktoré chceš vyhodnocovať
target_ids = [53, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 150, 154, 158, 159, 165, 180, 181, 182, 183, 184, 185, 186, 187, 188, 189, 190, 191, 192, 193, 194, 195, 196, 197, 200, 228, 239, 249, 262, 272, 279, 280, 281, 282, 283, 284, 285, 286, 287, 288, 289, 290, 291, 292, 293, 294, 295, 296, 298, 318, 333, 348, 377, 378, 379, 380, 381, 382, 383, 384, 385, 386, 387, 388, 389, 390, 391, 392, 393, 394, 395, 399, 407, 427, 431, 442, 448, 450, 452, 458, 480, 493, 504, 512, 519, 526, 534, 553, 582, 585, 611, 625, 633, 641, 642, 652, 655, 658, 671, 675, 682, 685, 700, 715, 726, 741, 745, 770, 780, 783, 798, 804, 806, 807, 808, 818, 819, 826, 828, 830, 837, 839, 847, 848, 857, 858, 860, 861, 877, 880, 903, 917, 930, 931, 934, 942, 947, 950, 952, 959, 960, 961, 962, 968, 976, 977, 979, 990, 992, 993, 1004, 1008, 1009, 1012, 1013, 1020, 1024, 1028, 1029, 1031, 1038, 1039, 1041, 1044, 1045, 1047, 1048, 1049, 1052, 1053, 1054, 1058, 1062, 1064, 1096]
print(len(target_ids))
target_ids = set(target_ids)

results_dir = Path("evaluation_results")
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

        summary[model_name]["prompt_tokens"] += usage.get("prompt_tokens", 0)
        summary[model_name]["completion_tokens"] += usage.get("completion_tokens", 0)
        summary[model_name]["total_tokens"] += usage.get("total_tokens", 0)

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
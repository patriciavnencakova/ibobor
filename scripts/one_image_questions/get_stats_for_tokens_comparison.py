from pathlib import Path
import json

target_ids = [3, 10, 12, 21, 22, 23, 26, 30, 33, 35, 36, 39, 42, 43, 46, 56, 68, 76, 102, 107, 109, 125, 132, 133, 138, 142, 147, 149, 151, 155, 162, 168, 171, 172, 173, 175, 199, 205, 209, 212, 213, 226, 230, 244, 245, 247, 250, 255, 256, 259, 260, 261, 264, 266, 275, 277, 304, 305, 306, 307, 310, 313, 315, 322, 324, 325, 328, 336, 341, 342, 343, 346, 350, 351, 355, 357, 359, 360, 361, 364, 370, 371, 372, 374, 375, 376, 397, 403, 406, 413, 417, 428, 430, 433, 436, 439, 440, 441, 444, 445, 455, 457, 462, 464, 465, 467, 470, 473, 475, 481, 483, 484, 487, 488, 489, 501, 505, 510, 511, 516, 518, 521, 536, 537, 540, 542, 544, 547, 554, 555, 558, 559, 560, 566, 569, 572, 576, 579, 586, 588, 589, 596, 597, 598, 604, 605, 606, 608, 609, 610, 618, 619, 620, 621, 627, 634, 636, 639, 644, 645, 650, 651, 654, 656, 657, 660, 661, 665, 667, 668, 672, 673, 677, 679, 681, 683, 686, 690, 698, 702, 703, 708, 709, 710, 711, 712, 713, 714, 717, 719, 722, 727, 728, 729, 732, 734, 738, 742, 744, 747, 751, 752, 754, 762, 768, 771, 774, 775, 776, 786, 790, 803, 805, 810, 811, 817, 820, 822, 831, 834, 835, 836, 838, 841, 842, 845, 849, 850, 851, 853, 854, 859, 864, 865, 867, 869, 871, 872, 873, 881, 886, 887, 895, 902, 906, 909, 911, 912, 913, 916, 918, 919, 922, 924, 929, 933, 937, 940, 941, 945, 948, 949, 951, 953, 956, 958, 966, 969, 970, 981, 982, 984, 986, 994, 999, 1003, 1005, 1006, 1010, 1011, 1015, 1016, 1022, 1025, 1026, 1032, 1033, 1035, 1042, 1043, 1050, 1057, 1059, 1066, 1067, 1069, 1073, 1074, 1076, 1079, 1080, 1081, 1082, 1087, 1089, 1093, 1094, 1097]
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
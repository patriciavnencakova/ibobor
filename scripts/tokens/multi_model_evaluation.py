import json
import re
import os
import time
import base64
from datetime import datetime
from pathlib import Path
from openai import OpenAI

API_KEY = "..."
BASE_URL = "https://openrouter.ai/api/v1"

MODELS = [
    "openai/gpt-5.2"
    "openai/gpt-5.4-mini"
    "google/gemini-2.5-flash",
    "google/gemini-2.5-pro",
    "meta-llama/llama-4-maverick",
    "meta-llama/llama-4-scout"
]

QUESTIONS_FILE = "../../storage/datasets/default"
IMAGE_FOLDER = "../../questions"

RAW_RESULTS_DIR = "raw_results"
EVAL_RESULTS_DIR = "evaluation_results"
COMBINED_SUMMARY_FILE = "combined_evaluation_summary.json"

TEMPERATURE = 0

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
os.makedirs(RAW_RESULTS_DIR, exist_ok=True)
os.makedirs(EVAL_RESULTS_DIR, exist_ok=True)

correct_answers = {}
for filename in os.listdir(QUESTIONS_FILE):
    if filename.endswith(".json") and filename != "__metadata__.json":
        file_path = os.path.join(QUESTIONS_FILE, filename)
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            correct_answers[data["id"]] = data["correct_answer_plain"]


def get_usage_dict(response):
    usage = getattr(response, "usage", None)

    prompt_tokens = getattr(usage, "prompt_tokens", None) if usage else None
    completion_tokens = getattr(usage, "completion_tokens", None) if usage else None
    total_tokens = getattr(usage, "total_tokens", None) if usage else None

    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
    }


def encode_image(path):
    suffix = Path(path).suffix.lower()

    if suffix == ".png":
        mime_type = "image/png"
    elif suffix in [".jpg", ".jpeg"]:
        mime_type = "image/jpeg"
    elif suffix == ".gif":
        mime_type = "image/gif"
    elif suffix == ".webp":
        mime_type = "image/webp"
    else:
        mime_type = "image/png"

    with open(path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")

    return f"data:{mime_type};base64,{encoded}"


def normalize_text(s: str) -> str:
    if not s:
        return ""
    s = re.sub(r"\s+", "", s)
    return s.strip().lower()


def evaluate_results(model_name, results):
    total = len(results)
    correct = 0
    detailed_results = []

    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_tokens = 0

    for r in results:
        qid = r["id"]
        model_answer = r["model_answer"]
        correct_answer = correct_answers.get(qid)

        is_correct = normalize_text(model_answer) == normalize_text(correct_answer)
        if is_correct:
            correct += 1

        usage = r.get("usage", {}) or {}

        prompt_tokens = usage.get("prompt_tokens") or 0
        completion_tokens = usage.get("completion_tokens") or 0
        used_total_tokens = usage.get("total_tokens") or 0

        total_prompt_tokens += prompt_tokens
        total_completion_tokens += completion_tokens
        total_tokens += used_total_tokens

        detailed_results.append({
            "id": qid,
            "model_answer": model_answer,
            "correct_answer": correct_answer,
            "is_correct": is_correct,
            "error": r.get("error"),
            "usage": usage
        })

    accuracy = correct / total if total else 0

    return {
        "model": model_name,
        "timestamp": datetime.utcnow().isoformat(),
        "total_questions": total,
        "correct_answers": correct,
        "incorrect_answers": total - correct,
        "accuracy": round(accuracy, 4),
        "token_usage": {
            "prompt_tokens": total_prompt_tokens,
            "completion_tokens": total_completion_tokens,
            "total_tokens": total_tokens,
        },
        "avg_tokens_per_question": {
            "prompt_tokens": round(total_prompt_tokens / total, 2) if total else 0,
            "completion_tokens": round(total_completion_tokens / total, 2) if total else 0,
            "total_tokens": round(total_tokens / total, 2) if total else 0,
        },
        "details": detailed_results
    }


def run_model(model_name):
    print(f"Starting evaluation for: {model_name}")
    results = []
    start_time = time.time()

    instruction_text = """
    You will receive one multiple-choice question given as an image.
    
    Select the correct answer.
    Return the EXACT answer text as written in the image. Do not translate.

    Return JSON only in this exact format:
    {
      "exact_answer_text": "string"
    }
    """.strip()

    images = sorted(Path(IMAGE_FOLDER).glob("*"))
    total_images = len(images)
    last_reported_pct = -10

    for idx, image in enumerate(images):

        current_pct = int((idx / total_images) * 100)
        if current_pct >= last_reported_pct + 10:
            milestone = (current_pct // 10) * 10
            print(f"{model_name}: {milestone}% complete ({idx}/{total_images})")
            last_reported_pct = milestone

        output_text = None
        usage_info = {
            "prompt_tokens": None,
            "completion_tokens": None,
            "total_tokens": None,
        }

        base64_img = encode_image(image)
        user_content = [{
            "type": "image_url",
            "image_url": {
                "url": base64_img
            }
        }]


        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": instruction_text},
                    {"role": "user", "content": user_content}
                ],
                temperature=TEMPERATURE,
                response_format={"type": "json_object"}
            )

            usage_info = get_usage_dict(response)
            output_text = response.choices[0].message.content
            output_json = json.loads(output_text)

            print(output_json)
            exact_answer = output_json.get("exact_answer_text")

            results.append({
                "id": int(Path(image).stem),
                "model_answer": exact_answer,
                "raw_response": output_text,
                "usage": usage_info
            })

        except Exception as e:
            print(f"❌ Error processing {image.name}: {e}")
            results.append({
                "id": int(Path(image).stem),
                "model_answer": None,
                "error": str(e),
                "raw_response": output_text,
                "usage": usage_info
            })

    elapsed = time.time() - start_time
    return results, elapsed


combined_summary = {
    "timestamp": datetime.utcnow().isoformat(),
    "models": []
}

for model in MODELS:
    model_results, elapsed_time = run_model(model)

    raw_output_path = os.path.join(
        RAW_RESULTS_DIR,
        f"{model.replace('/', '_')}_raw_results.json"
    )

    with open(raw_output_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "model": model,
                "timestamp": datetime.utcnow().isoformat(),
                "results": model_results
            },
            f,
            indent=2,
            ensure_ascii=False
        )

    evaluation_summary = evaluate_results(model, model_results)
    evaluation_summary["elapsed_time_seconds"] = round(elapsed_time, 2)
    evaluation_summary["elapsed_time_human"] = f"{int(elapsed_time // 60)}m {int(elapsed_time % 60)}s"

    eval_output_path = os.path.join(
        EVAL_RESULTS_DIR,
        f"{model.replace('/', '_')}_evaluation_summary.json"
    )
    with open(eval_output_path, "w", encoding="utf-8") as f:
        json.dump(evaluation_summary, f, indent=2, ensure_ascii=False)

    combined_summary["models"].append({
        "model": model,
        "accuracy": evaluation_summary["accuracy"],
        "total_questions": evaluation_summary["total_questions"],
        "correct_answers": evaluation_summary["correct_answers"],
        "incorrect_answers": evaluation_summary["incorrect_answers"],
        "elapsed_time_seconds": evaluation_summary["elapsed_time_seconds"],
        "elapsed_time_human": evaluation_summary["elapsed_time_human"],
        "token_usage": evaluation_summary["token_usage"],
        "avg_tokens_per_question": evaluation_summary["avg_tokens_per_question"],
        "evaluation_file": eval_output_path,
        "raw_results_file": raw_output_path
    })

with open(COMBINED_SUMMARY_FILE, "w", encoding="utf-8") as f:
    json.dump(combined_summary, f, indent=2, ensure_ascii=False)

print("All models evaluated successfully.")
print(f"Combined summary saved to {COMBINED_SUMMARY_FILE}")

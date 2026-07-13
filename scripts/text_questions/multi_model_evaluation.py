import json
import os
import time
from datetime import datetime
from openai import OpenAI

API_KEY = "..."

BASE_URL = "https://openrouter.ai/api/v1"

MODELS = [
    "openai/gpt-5.2"
    "openai/gpt-5.4-mini",
    "google/gemini-2.5-flash",
    "google/gemini-2.5-pro",
    "meta-llama/llama-4-maverick",
    "meta-llama/llama-4-scout"
]

INPUT_FILE = "text_questions.json"
QUESTIONS_FILE = "../../storage/datasets/default" # priecinok so zoscrapeovanymi otazkami

RAW_RESULTS_DIR = "raw_results"
EVAL_RESULTS_DIR = "evaluation_results"
COMBINED_SUMMARY_FILE = "combined_evaluation_summary.json"

TEMPERATURE = 0
# MAX_TOKENS = 100

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

os.makedirs(RAW_RESULTS_DIR, exist_ok=True)
os.makedirs(EVAL_RESULTS_DIR, exist_ok=True)

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    questions = json.load(f)

# questions = questions[:5]

correct_answers = {}
for filename in os.listdir(QUESTIONS_FILE):
    if filename.endswith(".json") and filename != "__metadata__.json":
        file_path = os.path.join(QUESTIONS_FILE, filename)
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if data.get("type") == "text":
                correct_answers[data["id"]] = str(data["correct_index"])


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


def evaluate_results(model_name, results):
    total = len(results)
    correct = 0
    detailed_results = []

    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_tokens = 0

    for r in results:
        qid = r["id"]
        model_choice = r.get("choice_value")
        correct_choice = correct_answers.get(qid)

        is_correct = model_choice == correct_choice
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
            "model_choice": model_choice,
            "correct_choice": correct_choice,
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
    You will receive one multiple-choice question.
    The input may contain HTML formatting such as bold text, line breaks, lists, or tables.
    Interpret this formatting as part of the question.
    
    Select the correct option value (NOT LABEL).

    Return JSON only in this exact format:
    {
      "id": number,
      "choice_value": "string"
    }
    """.strip()

    total_questions = len(questions)
    last_reported_pct = -10

    for idx, q in enumerate(questions, start=1):
        current_pct = int((idx / total_questions) * 100)

        if current_pct >= last_reported_pct + 10:
            milestone = (current_pct // 10) * 10
            print(f"{model_name}: {milestone}% complete ({idx}/{total_questions})")
            last_reported_pct = milestone
        output_text = None
        usage_info = {
            "prompt_tokens": None,
            "completion_tokens": None,
            "total_tokens": None,
        }

        valid_values = {str(c["value"]) for c in q["choices"]}
        valid_labels = {str(c["label"]) for c in q["choices"]}

        question_text = q["question"]
        choices_text = "\n".join(
            f'Option value: {c["value"]}, label: {c["label"]}'
            for c in q["choices"]
        )

        user_prompt = f"""
        Question ID: {q['id']}
        
        Question:
        {question_text}
        
        Choices:
        {choices_text}
        """.strip()

        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": instruction_text},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=TEMPERATURE,
                # max_tokens=MAX_TOKENS,
                response_format={"type": "json_object"}
            )

            usage_info = get_usage_dict(response)
            output_text = response.choices[0].message.content
            output_json = json.loads(output_text)

            # print(output_text)
            print(output_json)

            choice_value = str(output_json.get("choice_value"))
            if choice_value not in valid_values:
                if choice_value not in valid_labels:
                    raise ValueError(f"Invalid choice_value: {choice_value}")
                else:
                    choice_value = next(
                        str(c["value"]) for c in q["choices"]
                        if choice_value.strip() in str(c["label"]).strip()
                    )

            results.append({
                "id": q["id"],
                "choice_value": choice_value,
                "raw_response": output_text,
                "usage": usage_info
            })

        except Exception as e:
            print(f"Error for question ID {q['id']}: {e}")
            results.append({
                "id": q["id"],
                "choice_value": None,
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
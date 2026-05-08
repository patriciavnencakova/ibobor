# iBobor Task Scraper

This repository contains the source code of an automated data collection pipeline used to retrieve tasks from the Slovak iBobor demo platform. The scraper was developed as part of a diploma thesis focused on evaluating the performance of language models on tasks from the Slovak Bebras Challenge.

The collected data was later transformed into a structured dataset and used for experimental evaluation. The resulting dataset is publicly available on Hugging Face:

https://huggingface.co/datasets/patriciavnencakova/SlovakBebrasChallenge

## Overview

The main script, `main.py`, uses Crawlee with the PlaywrightCrawler framework to automate interaction with the iBobor demo competition platform. The crawler goes through available competition years and categories, starts a demo competition session, visits individual task pages, and extracts task content and metadata.

For each supported task, the scraper collects information such as:

- task identifier,
- serial number within the competition test,
- task title,
- task statement,
- answer choices,
- image references,
- competition year,
- competition category,
- detected task type,
- correct answer,
- index of the correct answer.

The crawler distinguishes between several task types, including text-based tasks, image-based tasks, canvas tasks, and Flash tasks. Text-based and image-based tasks are processed into a structured machine-readable representation, while unsupported interactive task types are detected separately.

## Repository Structure

```text
.
├── main.py             # Main crawler implementation
├── pyproject.toml      # Project configuration and dependencies
├── uv.lock             # Locked dependency versions
├── .python-version     # Python version used by the project
└── README.md           # Project documentation
```

## Requirements

The project requires Python 3.10 or newer.

The main dependency is:

- `crawlee[all]`

The script also uses BeautifulSoup for parsing HTML fragments. If it is not already installed through the project environment, install it separately:

```bash
uv add beautifulsoup4
```

## Installation

Clone the repository:

```bash
git clone https://github.com/patriciavnencakova/ibobor.git
cd ibobor
```

Install dependencies using `uv`:

```bash
uv sync
```

If Playwright browsers are not installed automatically, install them manually:

```bash
uv run playwright install
```

## Usage

Run the crawler with:

```bash
uv run python main.py
```

The crawler starts from the iBobor demo platform and automatically processes the available years, categories, and tasks.

Extracted records are stored using Crawlee's dataset storage. Each pushed record corresponds to one collected task and contains both task content and metadata.

## Output Format

Each collected task is represented as a JSON object with the following structure:

```json
{
  "id": 0,
  "serial_number": 1,
  "title": "Task title",
  "question": "Task statement",
  "choices": [
    {
      "value": "0",
      "label": "Answer option"
    }
  ],
  "images": [],
  "year": "2019/2020",
  "category": "Senior",
  "type": "text",
  "correct_index": 0,
  "correct_answer": "Answer option",
  "correct_answer_plain": "Answer option"
}
```

Image-based tasks may contain placeholders such as `<image_1>` in the task statement or answer options. These placeholders refer to the corresponding image URL stored in the `images` array.

## Purpose

The scraper was created to support the construction of a structured dataset of Slovak iBobor tasks. This dataset was then used to evaluate how selected language models perform on computational thinking tasks from the Slovak Bebras Challenge.

The implementation is included for transparency and reproducibility of the data collection process described in the thesis.

## Notes

The scraper depends on the structure of the iBobor demo platform. Changes to the platform's HTML structure, form names, URLs, or navigation flow may require updates to the selectors used in the script.

Interactive tasks implemented using Flash or canvas are detected, but they are not processed in the same structured way as text-based and image-based multiple-choice tasks.

## Related Resources

- Dataset: https://huggingface.co/datasets/patriciavnencakova/SlovakBebrasChallenge
- iBobor demo platform: http://demo.ibobor.sk/sutaz_demo/

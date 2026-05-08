# iBobor Task Scraper

This repository contains the source code of an automated data collection pipeline used to retrieve tasks from the Slovak iBobor demo platform (http://demo.ibobor.sk/sutaz_demo/). The scraper was developed as part of a diploma thesis focused on evaluating the performance of language models on tasks from the Slovak Bebras Challenge.

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

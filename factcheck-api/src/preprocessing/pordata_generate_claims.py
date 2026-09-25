"""
Turn PORDATA statistics tables into true claims, one per observation.

The crawler stores a statistic's metadata (question, indicator name, source, theme) as one
record, and its data table as a CSV alongside it. Neither is a claim on its own: the metadata
`title` is the question the statistic answers, and the CSV is just numbers. A claim is one cell
of that table written out in full, with everything needed to check it.
"""

import csv
import json
import logging
import os
import random
import re

from src.preprocessing.utils import clean_label

logger = logging.getLogger(__name__)

DEFAULT_DATA_FOLDER = "pordata_csv"
DEFAULT_RECENT_YEARS = 1
DEFAULT_MAX_CLAIMS_PER_STAT = 5
DEFAULT_SEED = 0

SYMBOL_NOTES = {
    "Pro": "Valor provisório.",
    "Pre": "Valor preliminar.",
    "(R)": "Valor revisto.",
}

PERCENTAGE_SCALES = ("%", "‰")
NON_UNIT_SCALES = {"valor absoluto"}

# a table combining several indicators tags its columns and its units "(A)", "(B)"
GROUP_MARKER_PATTERN = re.compile(r"\s*\(([A-Z])\)\s*$")
GROUP_SCALE_PATTERN = re.compile(r"\(([A-Z])\)\s*")


def indicator_subject(summary: str) -> str:
    """
    Shorten an indicator name to the part that names the subject.

    PORDATA names an indicator after its subject and then lists its breakdowns, as in
    "Explorações agrícolas: total e por forma de exploração". The breakdown of the row being
    described is already stated separately, so only the subject is kept.
    """
    subject = summary.split(":", 1)[0].strip() if ":" in summary else summary.strip()

    if not subject:
        return summary

    # the subject runs on from the middle of a sentence, but acronyms keep their case
    head = subject.split(" ", 1)[0]
    if head.isupper() or head[1:].lower() != head[1:]:
        return subject

    return subject[0].lower() + subject[1:]


def tokens(text: str) -> set[str]:
    return set(re.findall(r"\w+", text.lower()))


def restates_subject(label: str, subject: str) -> bool:
    """
    Whether a breakdown label only repeats the indicator the claim already names.

    Only labels that add no word of their own count as repetition. A label that narrows the
    indicator ("População residente estrangeira" under "população residente") has to survive,
    otherwise two different rows would be written as the same claim with different values.
    """
    return bool(label) and tokens(label) <= tokens(subject)


def group_marker(label: str) -> str | None:
    match = GROUP_MARKER_PATTERN.search(label)
    return match.group(1) if match else None


def scale_for_group(scale: str, marker: str | None) -> str:
    """
    Narrow a scale to the one unit that applies, on a table combining several indicators.

    Such a table states every unit at once, as in "(A) Número Índice (B) t CO 2 eq - Rácio".
    """
    if not marker:
        return scale

    parts = GROUP_SCALE_PATTERN.split(scale)
    units = dict(zip(parts[1::2], parts[2::2]))

    return units.get(marker, scale).strip()


def format_value(value: str, scale: str) -> str:
    scale = clean_label(scale)

    if not scale or scale.lower() in NON_UNIT_SCALES:
        return value

    if scale.endswith(PERCENTAGE_SCALES):
        return f"{value} {scale[-1]}"

    return f"{value} {scale}"


def format_breakdown(dimension: str, category: str, subject: str) -> str:
    dimension = GROUP_MARKER_PATTERN.sub("", clean_label(dimension))
    category = GROUP_MARKER_PATTERN.sub("", clean_label(category))

    # a dimension often opens by repeating the indicator, which the claim has just said
    if dimension.lower().startswith(subject.lower()):
        dimension = dimension[len(subject) :].lstrip(" -–:")

    if category == "Total":
        category = ""

    labels = [label for label in (dimension, category) if label and not restates_subject(label, subject)]

    return f" ({': '.join(labels)})" if labels else ""


def build_claim(row: dict[str, str], metadata: dict) -> tuple[str, str]:
    summary = clean_label(metadata["summary"])
    subject = indicator_subject(summary)
    territory = clean_label(row["Território"]) or "Portugal"
    breakdown = format_breakdown(row["Dimensão"], row["Categoria"], subject)

    marker = group_marker(row["Categoria"]) or group_marker(row["Dimensão"])
    value = format_value(row["Valor"], scale_for_group(row["Escala"], marker))

    claim = f"Em {row['Ano']}, em {territory}, {subject}{breakdown} foi {value}."

    note = SYMBOL_NOTES.get(row["Símbolo"])
    if not note and row["Símbolo"]:
        note = f"Valor assinalado com «{row['Símbolo']}» na fonte."

    explanation = (
        f"Segundo {metadata['author']} ({metadata['origin']}), o indicador "
        f"«{summary}» regista, para {territory} em {row['Ano']}"
        f"{breakdown}, o valor de {value}."
    )

    return claim, " ".join(filter(None, [explanation, note]))


def select_rows(
    rows: list[dict[str, str]],
    recent_years: int,
    max_claims: int,
    sampler: random.Random,
) -> list[dict[str, str]]:
    """
    Pick the rows of a table worth turning into claims.

    A table repeats the same series for every year it covers, and the municipality tables
    repeat it for every one of 350 territories, so writing out every cell would bury the
    dataset. Only the most recent years of each series are kept, and each statistic contributes
    a bounded sample of them.
    """
    # a row without a number carries a "no data" marker instead, so there is nothing to claim
    rows = [row for row in rows if any(character.isdigit() for character in row["Valor"])]

    if not rows:
        return []

    latest = sorted({row["Ano"] for row in rows}, reverse=True)[:recent_years]
    rows = [row for row in rows if row["Ano"] in latest]

    if max_claims and len(rows) > max_claims:
        rows = sampler.sample(rows, max_claims)

    return rows


async def preprocess(input_file: str, output_file: str, **kwargs: dict):
    """
    input_file: crawled PORDATA metadata JSONL, one statistic per line
    output_file: JSONL of claims, shaped like a raw crawl record

    kwargs:
        - data_folder: folder holding the CSVs, relative to the input file (default pordata_csv)
        - recent_years: how many of the most recent years of each series to keep (default 1)
        - max_claims_per_stat: cap on the claims one statistic contributes (default 5, 0 = all)
        - seed: seed for the row sample, so a run over the same input repeats (default 0)
    """
    data_folder = kwargs.get("data_folder", DEFAULT_DATA_FOLDER)
    recent_years = int(kwargs.get("recent_years", DEFAULT_RECENT_YEARS))
    max_claims = int(kwargs.get("max_claims_per_stat", DEFAULT_MAX_CLAIMS_PER_STAT))
    seed = int(kwargs.get("seed", DEFAULT_SEED))

    logger.info(f"Generating PORDATA claims: {input_file} -> {output_file}")
    logger.info(f"Config: recent_years={recent_years}, max_claims_per_stat={max_claims or 'all'}, seed={seed}")

    csv_folder = os.path.join(os.path.dirname(input_file), data_folder)
    statistics = claims = unreadable_statistics = repeated_claims = 0
    sampler = random.Random(seed)

    # the same figure is occasionally published under two indicators
    seen: set[str] = set()

    with open(input_file, encoding="utf-8") as metadata_file, open(output_file, "w", encoding="utf-8") as out_file:
        for line in metadata_file:
            if not line.strip():
                continue

            metadata = json.loads(line)
            statistics += 1

            rows = read_data_table(csv_folder, metadata.get("data_file"))
            if rows is None:
                unreadable_statistics += 1
                continue

            for row in select_rows(rows, recent_years, max_claims, sampler):
                claim, explanation = build_claim(row, metadata)

                if claim in seen:
                    repeated_claims += 1
                    continue

                seen.add(claim)

                out_file.write(
                    json.dumps(
                        {
                            "title": claim,
                            "assessement_result": "Verdadeiro",
                            "summary": clean_label(metadata["summary"]),
                            "explanation": explanation,
                            "category": metadata["category"],
                            "publication_date": metadata["publication_date"],
                            "author": metadata["author"],
                            "origin": metadata["origin"],
                            "data_file": metadata["data_file"],
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                claims += 1

    logger.info(f"Generated {claims} claims from {statistics - unreadable_statistics}/{statistics} statistics")

    if repeated_claims:
        logger.info(f"Dropped {repeated_claims} claims already stated word for word by another statistic")

    if unreadable_statistics:
        logger.warning(f"Skipped {unreadable_statistics} statistics with no readable data file")


def read_data_table(csv_folder: str, data_file: str | None) -> list[dict[str, str]] | None:
    if not data_file:
        return None

    csv_path = os.path.join(csv_folder, data_file)

    try:
        with open(csv_path, encoding="utf-8", newline="") as file:
            return list(csv.DictReader(file))
    except OSError as e:
        logger.warning(f"Could not read data file {csv_path}: {e}")
        return None

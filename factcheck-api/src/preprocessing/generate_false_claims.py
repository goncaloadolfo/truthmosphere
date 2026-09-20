"""
Generate realistic false claims by LLM-controlled perturbation of true claims.

Perturbation strategies:
  - number:   Modify numerical values (percentages, counts, dates, monetary amounts)
  - entity:   Replace named entities (people, organizations, locations)
  - causal:   Invert or alter causal/logical relationships
  - combined: Mix of the above for harder negatives

The generator preserves fluency, plausibility, domain, style, and approximate length.
"""

import asyncio
import logging
import os
import random
import re
from enum import Enum
from string import Template
from typing import Any

import litellm
import pandas as pd
from thefuzz import fuzz
from tqdm import tqdm

logger = logging.getLogger(__name__)


class PerturbationStrategy(str, Enum):
    NUMBER = "number"
    ENTITY = "entity"
    CAUSAL = "causal"
    COMBINED = "combined"


STRATEGY_INSTRUCTIONS: dict[PerturbationStrategy, str] = {
    PerturbationStrategy.NUMBER: (
        "Modify ONE OR MORE numerical values in the claim (e.g., percentages, counts, years, "
        "monetary amounts). The change should be plausible but factually incorrect. "
        "For example, change '15%' to '25%' or '2019' to '2017'."
    ),
    PerturbationStrategy.ENTITY: (
        "Replace ONE OR MORE named entities (people, organizations, locations, products) "
        "with different but contextually plausible alternatives. "
        "For example, change 'Amazon' to 'Microsoft' or 'Portugal' to 'Spain'."
    ),
    PerturbationStrategy.CAUSAL: (
        "Alter the causal or logical relationship expressed in the claim. "
        "You may invert cause and effect, negate a relationship, or change the direction "
        "of a trend (e.g., 'increased' → 'decreased', 'caused by' → 'unrelated to')."
    ),
    PerturbationStrategy.COMBINED: (
        "Apply a MIX of the following perturbations to make the claim false:\n"
        "  • Modify numerical values\n"
        "  • Replace named entities\n"
        "  • Alter causal/logical relationships\n"
        "Choose whichever combination makes the resulting claim plausible yet clearly false."
    ),
}

SYSTEM_PROMPT = """\
You are an expert at generating realistic but FALSE claims for fact-checking research.
Your task is to subtly modify a true claim so that it becomes factually incorrect while
preserving the original style, fluency, domain, and approximate length.
The false claim must be plausible enough that a reader might believe it without verification.
IMPORTANT: Return ONLY the rewritten false claim, nothing else."""

USER_PROMPT_TEMPLATE = Template(
    """\
ORIGINAL TRUE CLAIM:
\"\"\"
$claim
\"\"\"

PERTURBATION STRATEGY:
$strategy_instruction

CONSTRAINTS:
1. Keep the same language as the original claim.
2. Preserve the writing style, tone, and domain.
3. Keep approximately the same length (within ±20% of word count).
4. Ensure the result is grammatically correct and fluent.
5. The claim must be clearly FALSE but still plausible.
6. Do NOT add disclaimers, explanations, or meta-commentary.

Generate the FALSE version of the claim:"""
)


def validate_length(original: str, generated: str, tolerance: float = 0.25) -> bool:
    orig_words = len(original.split())
    gen_words = len(generated.split())

    if orig_words == 0 or gen_words == 0:
        return False

    # 25% (default) more or less words
    ratio = gen_words / orig_words
    return (1 - tolerance) <= ratio <= (1 + tolerance)


def validate_similarity(original: str, generated: str, min_sim: int = 40, max_sim: int = 95) -> bool:
    sim = fuzz.ratio(original, generated)
    return min_sim <= sim <= max_sim


def validate_not_empty(text: str) -> bool:
    return bool(text and text.strip())


def run_all_validators(
    original: str,
    generated: str,
    length_tolerance: float = 0.25,
    min_similarity: int = 40,
    max_similarity: int = 95,
) -> tuple[bool, list[str]]:
    failures = []

    if not validate_not_empty(generated):
        failures.append("empty_output")
    if not validate_length(original, generated, length_tolerance):
        failures.append("length_mismatch")
    if not validate_similarity(original, generated, min_similarity, max_similarity):
        failures.append("similarity_out_of_range")

    return len(failures) == 0, failures


async def generate_false_claim(
    claim: str,
    strategy: PerturbationStrategy,
    model: str,
    temperature: float = 0.7,
    length_tolerance: float = 0.25,
    min_similarity: int = 40,
    max_similarity: int = 95,
) -> tuple[str | None, float, list[str]]:
    if not claim or not claim.strip():
        return None, 0.0, ["empty_input"]

    # prompt with perturbation strategy
    strategy_instruction = STRATEGY_INSTRUCTIONS[strategy]
    user_prompt = USER_PROMPT_TEMPLATE.substitute(
        claim=claim.strip(),
        strategy_instruction=strategy_instruction,
    )

    generated = None
    cost = 0.0
    failures: list[str] = []

    try:
        response = await litellm.acompletion(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            num_retries=2,
        )
        cost = response._hidden_params.get("response_cost", 0.0) or 0.0

        if response.choices:
            generated = response.choices[0].message.content.strip()

            # clean up surrounding quotes/newlines the LLM might add
            generated = re.sub(r"^[\"\'\s\\n]+|[\"\'\s\\n]+$", "", generated)
            generated = re.sub(r'^"{2,}|"{2,}$', "", generated)
            generated = generated.strip()

            passed, failures = run_all_validators(
                claim,
                generated,
                length_tolerance,
                min_similarity,
                max_similarity,
            )
            if passed:
                return generated, cost, []

    except Exception as e:
        logger.warning(f"LLM call failed: {e}")

    return None, cost, failures


async def process_claim(
    record: dict[str, Any],
    claim_field: str,
    pertubation_strategy: PerturbationStrategy,
    model: str,
    temperature: float,
    length_tolerance: float,
    min_similarity: int,
    max_similarity: int,
) -> dict[str, Any]:
    claim = record.get(claim_field, "")
    fact_id = record.get("fact_id", "unknown")
    new_record = None

    generated, cost, failures = await generate_false_claim(
        claim=claim,
        strategy=pertubation_strategy,
        model=model,
        temperature=temperature,
        length_tolerance=length_tolerance,
        min_similarity=min_similarity,
        max_similarity=max_similarity,
    )
    logger.info(
        f"Processed fact_id={fact_id} strategy={pertubation_strategy.value} cost=${cost:.4f} failures={failures}"
    )

    if generated:
        new_record = record.copy()

        # false claim fields
        new_record[claim_field] = generated
        new_record["assessement_result"] = "Falso"
        new_record["assessement_binary"] = False
        new_record["ref_original_claim"] = fact_id
        new_record["perturbation_strategy"] = pertubation_strategy.value
        new_record["is_synthetic_false_claim"] = True
    else:
        logger.warning(
            f"Failed to generate false claim for fact_id={fact_id} "
            f"strategy={pertubation_strategy.value} failures={failures}"
        )

    return new_record


async def process_batch(
    batch: list[dict[str, Any]],
    claim_field: str,
    strategies: list[PerturbationStrategy],
    model: str,
    temperature: float,
    length_tolerance: float,
    min_similarity: int,
    max_similarity: int,
) -> list[dict[str, Any]]:
    tasks = [
        process_claim(
            record=record,
            claim_field=claim_field,
            pertubation_strategy=strategy,
            model=model,
            temperature=temperature,
            length_tolerance=length_tolerance,
            min_similarity=min_similarity,
            max_similarity=max_similarity,
        )
        for record, strategy in zip(batch, strategies)
    ]
    return await asyncio.gather(*tasks)


async def preprocess(input_file: str, output_file: str, **kwargs: dict) -> None:
    """
    Preprocess input file to generate false claims using LLM-based perturbation.

    Config options (passed via kwargs):
        - model: LLM model to use (default: "gpt-4o-mini")
        - claim_field: Field containing the claim text (default: "title")
        - strategies: List of perturbation strategies (default: all)
        - temperature: LLM temperature (default: 0.7)
        - batch_size: Number of records to process concurrently (default: 5)
        - length_tolerance: Max allowed length deviation (default: 0.25)
        - min_similarity: Min fuzzy similarity score (default: 40)
        - max_similarity: Max fuzzy similarity score (default: 95)
        - filter_true_only: Only generate false claims from true claims (default: True)
        - sample_size: Number of records to sample (default: None = all)
        - random_seed: Random seed for sampling (default: 42)
    """
    logger.info(f"Starting false claim generation: {input_file} -> {output_file}")

    # configuration values
    model = kwargs.get("model", "gpt-4o-mini")
    claim_field = kwargs.get("claim_field", "title")
    temperature = kwargs.get("temperature", 0.7)
    batch_size = kwargs.get("batch_size", 5)
    length_tolerance = kwargs.get("length_tolerance", 0.25)
    min_similarity = kwargs.get("min_similarity", 40)
    max_similarity = kwargs.get("max_similarity", 95)
    sample_size = kwargs.get("sample_size", None)

    # perturbation strategies
    strategy_names = kwargs.get("strategies", PerturbationStrategy.__members__.keys())
    strategies = [PerturbationStrategy(s) for s in strategy_names]
    logger.info(f"Config: model={model}, claim_field={claim_field}, strategies={[s.value for s in strategies]}")

    # input claims
    input_facts_data = pd.read_json(input_file, lines=True)
    logger.info(f"Loaded {len(input_facts_data)} records from {input_file}")

    if claim_field not in input_facts_data.columns:
        raise ValueError(
            f"Claim field '{claim_field}' not found in input data. Available: {list(input_facts_data.columns)}"
        )

    if sample_size and sample_size < len(input_facts_data):
        facts_data = input_facts_data.sample(n=sample_size)
        logger.info(f"Sampled {sample_size} records")
    else:
        facts_data = input_facts_data

    records = facts_data.to_dict(orient="records")

    # resume without repeating the same base fact and strategy
    processed_fact_ids: set[str] = set()
    if os.path.exists(output_file):
        existing_data = pd.read_json(output_file, lines=True)

        for _, row in existing_data.iterrows():
            original_id = row.get("ref_original_claim", "")
            strategy = row.get("perturbation_strategy", "")
            processed_fact_ids.add(f"{original_id}_{strategy}")

        logger.info(f"Found {len(existing_data)} existing records in output file, will resume")

    # batch generation loop
    total_generated = 0
    pbar = tqdm(total=len(records), desc="Generating false claims")

    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]

        batch_to_process = []
        for record in batch:
            fact_id = record.get("fact_id", "")
            strategy = random.choice(list(strategies))

            key = f"{fact_id}_{strategy.value}"
            if key not in processed_fact_ids:
                batch_to_process.append((record, strategy))

        if not batch_to_process:
            pbar.update(len(batch))
            continue

        batch_results = await process_batch(
            batch=[r[0] for r in batch_to_process],
            claim_field=claim_field,
            strategies=[r[1] for r in batch_to_process],
            model=model,
            temperature=temperature,
            length_tolerance=length_tolerance,
            min_similarity=min_similarity,
            max_similarity=max_similarity,
        )

        # write results incrementally
        valid_results = [r for r in batch_results if r is not None]
        if valid_results:
            pd.DataFrame(valid_results).to_json(output_file, orient="records", lines=True, force_ascii=False, mode="a")

        total_generated += len(valid_results)
        pbar.update(len(batch))

    # union with input data
    input_facts_data.to_json(output_file, orient="records", lines=True, force_ascii=False, mode="a")

    pbar.close()
    logger.info("False claim generation completed.")
    logger.info(f"Total records generated: {total_generated}")
    logger.info(f"Output saved to: {output_file}")

import asyncio
import logging
import os
from string import Template

import litellm
import pandas as pd
from thefuzz import fuzz
from tqdm import tqdm

SYSTEM_PROMPT = "You are a helpful assistant that fixes grammar and spelling."

PROMPT_TEMPLATE = Template(
    (
        "Please fix the grammar, spelling, and punctuation in the following paragraph.\n"
        "Only return the corrected text, with no explanations or extra comments:\n\n"
        "$text"
    )
)

logger = logging.getLogger(__name__)


async def preprocess(input_file: str, output_file: str, **kwargs: dict):
    """
    Preprocess the input file by fixing typos using an LLM and saving the results to the output file.
    """
    logger.info(f"Preprocessing file: {input_file} to {output_file}")
    facts_data = pd.read_json(input_file, lines=True)

    if os.path.exists(output_file):
        output_file_data = pd.read_json(output_file, lines=True)
    else:
        output_file_data = []

    model = kwargs.get("fix_typos_model", "gpt-4o-mini")
    fuzzy_match_threshold = kwargs.get("fuzzy_match_threshold", 97)
    batch_size = kwargs.get("batch_size", 10)

    # validate fields to fix
    fix_fields = kwargs.get("fix_typos_fields")
    if not fix_fields:
        raise ValueError("No fields specified for typo fixing.")
    else:
        for field in fix_fields:
            if field not in facts_data.columns:
                raise ValueError(f"Field '{field}' not found in input data columns.")

    # process and save in batches to allow resuming
    pbar = tqdm(initial=len(output_file_data), total=len(facts_data), desc="Fixing typos")
    total_cost = 0.0

    for i in range(len(output_file_data), len(facts_data), batch_size):
        batch = facts_data.iloc[i : i + batch_size].copy()

        for field in fix_fields:
            batch, batch_cost = await apply_corrections_batch(batch, field, model, fuzzy_match_threshold)
            total_cost += batch_cost

        batch.to_json(output_file, lines=True, orient="records", mode="a", force_ascii=False)
        pbar.update(len(batch))

    pbar.close()
    logger.info(f"Preprocessing completed. Output saved to {output_file}")
    logger.info(f"Total cost of fixing typos: ${total_cost}")
    logger.info(f"Average cost per record: ${total_cost / (len(facts_data) - len(output_file_data))}")


async def apply_corrections_batch(
    batch: pd.DataFrame, field: str, model: str, fuzzy_threshold: int
) -> tuple[pd.DataFrame, float]:
    fix_typos_tasks = [
        fix_typos_llm(
            text,
            model,
            fuzzy_threshold,
        )
        for text in batch[field].tolist()
    ]

    completion_results = await asyncio.gather(*fix_typos_tasks)
    corrected_texts = [result[0] for result in completion_results]
    batch_cost = sum(result[1] for result in completion_results)
    batch[f"{field}_corrected"] = corrected_texts

    return batch, batch_cost


async def fix_typos_llm(text: str, model: str, fuzzy_threshold: int) -> tuple[str, float]:
    if not text:
        return text, 0.0

    text = text.strip()

    response_completion = await litellm.acompletion(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": PROMPT_TEMPLATE.substitute(text=text)},
        ],
        temperature=0.0,
        num_retries=3,
    )
    cost = response_completion._hidden_params["response_cost"]

    if response_completion.choices:
        corrected_text = response_completion.choices[0].message.content.strip()
        if fuzz.ratio(text, corrected_text) >= fuzzy_threshold:
            return corrected_text, cost

    return text, cost

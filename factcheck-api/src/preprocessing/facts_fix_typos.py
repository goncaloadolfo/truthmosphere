import asyncio
import logging
import os
from string import Template

import openai
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

openai_client = openai.AsyncOpenAI()


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

    # process explanation and summary in batches
    pbar = tqdm(initial=len(output_file_data), total=len(facts_data), desc="Fixing typos")

    for i in range(len(output_file_data), len(facts_data), batch_size):
        batch = facts_data.iloc[i : i + batch_size].copy()

        fix_typos_explanation_tasks = [
            fix_typos_llm(
                text,
                model,
                fuzzy_match_threshold,
            )
            for text in batch["explanation"].tolist()
        ]

        fix_typos_summary_tasks = [
            fix_typos_llm(
                text,
                model,
                fuzzy_match_threshold,
            )
            for text in batch["summary"].tolist()
        ]

        batch["explanation_corrected"] = await asyncio.gather(*fix_typos_explanation_tasks)
        batch["summary_corrected"] = await asyncio.gather(*fix_typos_summary_tasks)
        batch.to_json(output_file, lines=True, orient="records", mode="a", force_ascii=False)
        pbar.update(len(batch))

    pbar.close()
    logger.info(f"Preprocessing completed. Output saved to {output_file}")


async def fix_typos_llm(text: str, model: str, fuzzy_threshold: int) -> str:
    if not text:
        return text

    text = text.strip()

    response_completion = await openai_client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": PROMPT_TEMPLATE.substitute(text=text)},
        ],
        temperature=0.0,
    )

    if response_completion.choices:
        corrected_text = response_completion.choices[0].message.content.strip()
        if fuzz.ratio(text, corrected_text) >= fuzzy_threshold:
            return corrected_text

    return text

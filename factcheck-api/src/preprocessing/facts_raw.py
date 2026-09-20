import logging

import pandas as pd

logger = logging.getLogger(__name__)


ASSESSEMENT_MAPPING = {
    "verdadeiro": True,
    "verdadeiro, mas…": True,
    "impreciso": False,
    "falso": False,
    "manipulado": False,
    "descontextualizado": False,
    "pimenta na língua": False,
}

MONTH_MAPPING = {
    "janeiro": "January",
    "fevereiro": "February",
    "março": "March",
    "abril": "April",
    "maio": "May",
    "junho": "June",
    "julho": "July",
    "agosto": "August",
    "setembro": "September",
    "outubro": "October",
    "novembro": "November",
    "dezembro": "December",
}


async def preprocess(input_file: str, output_file: str, **kwargs) -> None:
    logger.info(f"Preprocessing file: {input_file} to {output_file}")

    origin = kwargs.get("origin", None)
    date_format = kwargs.get("date_format", None)

    # assessement
    raw_facts_data = pd.read_json(input_file, lines=True)
    raw_facts_data["assessement_binary"] = raw_facts_data["assessement_result"].str.lower().map(ASSESSEMENT_MAPPING)

    # publication date
    raw_facts_data["publication_datetime"] = raw_facts_data["publication_date"].apply(
        lambda x: parse_pt_datetime(x, date_format)
    )
    raw_facts_data["publication_datetime"] = raw_facts_data["publication_datetime"].astype(str)

    # fill some of the values
    raw_facts_data["origin"] = raw_facts_data.get("origin", origin)
    raw_facts_data["author"] = raw_facts_data.get("author", None)
    raw_facts_data["summary"] = raw_facts_data.get("summary", None)
    raw_facts_data["data_file"] = raw_facts_data.get("data_file", None)

    # save to output file, ensure encoding
    raw_facts_data.to_json(output_file, lines=True, orient="records", force_ascii=False)

    logger.info(f"Preprocessing completed. Output saved to {output_file}")


def parse_pt_datetime(date_str: str, date_format: str) -> pd.Timestamp:
    """
    Parse a Portuguese date string into a pandas Timestamp.
    Example input: "1 de Janeiro de 2020 12:00"
    """
    date_str = date_str.replace(" às ", " ")
    for pt_month, en_month in MONTH_MAPPING.items():
        date_str = date_str.lower().replace(pt_month, en_month)
    return pd.to_datetime(date_str, format=date_format)

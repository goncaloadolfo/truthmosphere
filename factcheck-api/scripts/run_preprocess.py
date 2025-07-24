import logging

import fire
import yaml
from src.preprocessing import *  # noqa

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


def run_preprocess(config_file: str):
    with open(config_file, "r") as file:
        config: dict = yaml.safe_load(file)

    input_file = config.pop("input_file")
    output_file = config.pop("output_file")
    operation_name = config.pop("operation_name")

    if not input_file or not output_file or not operation_name:
        raise ValueError("Input file, output file, and operation name must be specified in the configuration.")

    logger.info(f"Running preprocessing on {input_file} to {output_file}")

    # dynamically call the preprocessing function
    if operation_name not in globals():
        raise ValueError(f"Operation '{operation_name}' is not defined in the preprocessing module.")

    preprocess_function = globals()[operation_name]
    preprocess_function(input_file=input_file, output_file=output_file)
    logger.info(f"Preprocessing completed. Output saved to {output_file}")


if __name__ == "__main__":
    fire.Fire(run_preprocess)

from .facts_fix_typos import preprocess as facts_fix_typos_preprocess
from .facts_raw import preprocess as facts_raw_preprocess
from .generate_false_claims import preprocess as generate_false_claims_preprocess

__all__ = ["facts_raw_preprocess", "facts_fix_typos_preprocess", "generate_false_claims_preprocess"]

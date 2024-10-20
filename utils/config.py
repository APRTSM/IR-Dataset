import os
import logging
import time
from tqdm import tqdm
from datetime import datetime

FORMATTED_DATE_TIME = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

""" Directories """
PROJECT_DIR = os.getcwd()

# DATASETS
DATASETS_DIR = os.path.join(PROJECT_DIR, "datasets")
DL4PC2_DIR = os.path.join(DATASETS_DIR, "dl4pc2")
APRE_NFL_DIR = os.path.join(DATASETS_DIR, "aprenfl")
DEFECTREPAIRING_DIR = os.path.join(DATASETS_DIR, "defectrepairing")
DRR_DIR = os.path.join(DATASETS_DIR, "drr")
WANGICSE_DIR = os.path.join(DATASETS_DIR, "wangicse")

# BENCHMARKS
BENCHMARKS_DIR = os.path.join(PROJECT_DIR, "benchmarks")
DEFECTS4J_DIR = os.path.join(BENCHMARKS_DIR, "defects4j")
BUGSJAR_DIR = os.path.join(BENCHMARKS_DIR, "bugsjar")
QUIXBUGS_DIR = os.path.join(BENCHMARKS_DIR, "quixbugs")
BEARS_DIR = os.path.join(BENCHMARKS_DIR, "bears")
INTROCLASSJAVA_DIR = os.path.join(BENCHMARKS_DIR, "introclassjava")

# TOOLS
TOOLS_DIR = os.path.join(PROJECT_DIR, "tools")
OLLAMA_DIR = os.path.join(TOOLS_DIR, "ollama")
OLLAMA_PROMPTS_JSON =  os.path.join(OLLAMA_DIR, "prompts.json")
OLLAMA_MODELS_JSON = os.path.join(OLLAMA_DIR, "models.json")
OLLAMA_TEMPERATURES_JSON = os.path.join(OLLAMA_DIR, "temperatures.json")

# SETTINGS
SETTINGS_FILE = os.path.join(PROJECT_DIR, "settings.xml")
BENCHMARKS_JSON = os.path.join(BENCHMARKS_DIR, "benchmarks.json")
DATASETS_JSON = os.path.join(DATASETS_DIR, "datasets.json")
TOOLS_JSON = os.path.join(TOOLS_DIR, "tools.json")

INPUT_DIR = os.path.join(PROJECT_DIR, "input")

# TMP
TMP_DIR = os.path.join(PROJECT_DIR, "tmp")
TMP_CHECKOUTS_DIR = os.path.join(TMP_DIR, "checkouts")
TMP_METHODS_DIR = os.path.join(TMP_DIR, "methods")
TMP_PATCHES_DIR = os.path.join(TMP_DIR, "patches")
TMP_DATA_DIR = os.path.join(TMP_DIR, "data")
TMP_RESULTS_DIR = os.path.join(TMP_DIR, "results")
TMP_PLOTS_DIR = os.path.join(TMP_DIR, "plots")

## Initial Data
TMP_FORMATTED_PATCH_DIR = os.path.join(TMP_PATCHES_DIR, "cleaned")
TMP_DEVELOPER_PATCH_DIR = os.path.join(TMP_PATCHES_DIR, "raw")

TMP_META_DATA = os.path.join(TMP_DATA_DIR, "metadata")
TMP_SETTINGS_FILE = os.path.join(TMP_META_DATA, "settings.xml") 
TMP_BENCHMARKS_JSON = os.path.join(TMP_META_DATA, "benchmarks.json")
TMP_DATASETS_JSON = os.path.join(TMP_META_DATA, "datasets.json")
TMP_TOOLS_JSON = os.path.join(TMP_META_DATA, "tools.json")

TMP_BUGS_PKL = os.path.join(TMP_DATA_DIR, "bugs.pkl")
TMP_DEVELOPER_PATHCES_PKL = os.path.join(TMP_DATA_DIR, "developer-patches.pkl")
TMP_TOOL_PATHCES_PKL = os.path.join(TMP_DATA_DIR, "tool-patches.pkl")
TMP_CLEANED_DEVELOPER_PATHCES_PKL = os.path.join(TMP_DATA_DIR, "cleaned-developer-patches.pkl")
TMP_CLEANED_TOOL_PATHCES_PKL = os.path.join(TMP_DATA_DIR, "cleaned-tool-patches.pkl")

## Patch Processing
TMP_PROCESSORS_JSON = os.path.join(TMP_META_DATA, "processors.json")

## Tool Settings 
TMP_OLLAMA_DIR = os.path.join(TMP_META_DATA, "ollama")
TMP_OLLAMA_PROMPTS_JSON =  os.path.join(TMP_OLLAMA_DIR, "prompts.json")
TMP_OLLAMA_MODELS_JSON = os.path.join(TMP_OLLAMA_DIR, "models.json")
TMP_OLLAMA_TEMPERATURES_JSON = os.path.join(TMP_OLLAMA_DIR, "temperatures.json")

# Processed Data
TMP_TEST_RESULTS_DIR = os.path.join(TMP_RESULTS_DIR, "test")
TMP_CLASSIFICATION_RESULTS_DIR = os.path.join(TMP_RESULTS_DIR, "classification")

# Plots
TMP_RESULTS_JSON_FILE = os.path.join(TMP_PLOTS_DIR, "results.json")

LOG_DIR = os.path.join(TMP_DIR, "logs")
LOG_FILE = os.path.join(LOG_DIR, f"{FORMATTED_DATE_TIME}.log")

""" Naming Conventions """
SEPERATOR = '_'
PATCH_FILE_SUFFIX = ".patch"


""" Other Configurations """
logging.basicConfig(
    filename=LOG_FILE, 
    filemode='w',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)
tqdm.pandas(desc="Unknown Process.")


if __name__=="__main__":
    pass
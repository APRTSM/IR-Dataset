from utils.benchmark import *
from string import Template
import pandas as pd
import json
import os
import ollama
from tqdm import tqdm


class Collector:
    def __init__(self):
        with open(BENCHMARKS_JSON, 'r') as file:
            self.benchmarks = json.load(file)
            self.configure_functions = {
                'defects4j': configure_defects4j,
            }
            self.get_bug_list_functions = {
                'defects4j': get_bug_list_defects4j,
            }
            self.checkout_functions = {
                'defects4j': checkout_bug_defects4j,
            }

        self._configure_benchmarks()

    # Configure the benchmarks
    def _configure_benchmarks(self):
        for benchmark in self.benchmarks:
            self.configure_functions[benchmark['uid']]()

    # Get the list of bugs
    def get_bug_list(self):
        bugs_list = []

        for benchmark in self.benchmarks:
            bugs_list += self.get_bug_list_functions[benchmark['uid']]()

        self.bugs = pd.DataFrame(bugs_list).set_index("uid")

    # Discard the bugs with no report
    def clean_no_report(self):
        self.bugs = self.bugs[self.bugs['report_link'].notna()]

    def _developer_patch_exists(self, bug):
        # check if file exists
        dir = os.path.join(TMP_FORMATTED_PATCH_DIR, f"{bug.name}-developer.patch")

        if os.path.exists(dir):
            return True
        
        return False
    
    # Discard bugs with no proper developer patch
    def clean_no_patch(self):
        self.bugs = self.bugs[self.bugs.apply(self._developer_patch_exists, axis=1)]

    def _checkout_bug(self, bug):
        return self.checkout_functions[bug['benchmark']](bug) ############ Check this

    def checkout_bugs(self):
        self.bugs = self.bugs.loc[['defects4j-Cli-28']]
        self.bugs['checkout_dir'] = self.bugs.apply(self._checkout_bug, axis=1)

    def get_methods(self):
        self.bugs['methods_dir'] = self.bugs.apply(get_source_methods, axis=1)


class Executor:
    def __init__(self, model, prompt, prompt_id, temperature):
        self.collector = Collector()

        self.collector.get_bug_list()
        self.collector.clean_no_report()
        self.collector.clean_no_patch()
        self.collector.checkout_bugs()
        self.collector.get_methods()

        self.model = model
        self.prompt = prompt
        self.prompt_id = prompt_id
        self.temperature = temperature

    def _get_response(self, method):
        response = ollama.chat(model=self.model, keep_alive=-1, options=ollama.Options(temperature=self.temperature), messages=[
            {
                "role": "system",
                "content": self.prompt.format(method=method["method"])
            },
        ])

        return response["message"]["content"]
    
    def _run_bug(self, bug):
        process_id = f"{bug.name}-{self.model}-{self.prompt_id}-{self.temperature}"
        
        logging.info(f"Processing {process_id}!")

        bug_methods = pd.read_pickle(bug["methods_dir"])
        tqdm.pandas(desc=f"Processing  {process_id}!")
        bug_methods["response"] = bug_methods.progress_apply(self._get_response, axis=1)
        
        out_file_name = f"{process_id}.pkl"
        bug_methods.to_pickle(os.path.join(TMP_RESULTS_DIR, out_file_name))

    def run(self):
        self.collector.bugs.apply(self._run_bug, axis=1)


if __name__=="__main__":
    simple_prompt = """
        Please Provide information about the following method, and describe what it does generally.

        {method}
    """
    executor = Executor("codellama:7b-instruct", simple_prompt, "simple", 0.1)
    executor.run()




    


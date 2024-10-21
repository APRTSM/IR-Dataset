from utils.benchmark import *
import pandas as pd
import json

class MethodFetcher:
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
        print(self.bugs)
        self.bugs = self.bugs.sample(n=10, random_state=1) # Temporary
        self.bugs['checkout_dir'] = self.bugs.apply(self._checkout_bug, axis=1)


if __name__=="__main__":
    fetcher = MethodFetcher()
    fetcher.get_bug_list()
    fetcher.clean_no_report()
    fetcher.clean_no_patch()
    fetcher.checkout_bugs()

    


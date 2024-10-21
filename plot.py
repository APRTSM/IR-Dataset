import pandas as pd
from utils.benchmark import *


if __name__ == "__main__":
    df = pd.read_pickle("tmp/results/defects4j-Cli-25-codellama:7b-instruct-simple-0.1.pkl")
    df.to_html("tmp/results/defects4j-Cli-25-codellama:7b-instruct-simple-0.1.html")

    # configure_defects4j()
    # bugs = get_bug_list_defects4j()
    # bugs = pd.DataFrame(bugs).set_index("uid")
    # selected_bug = bugs.loc["defects4j-Cli-25"]
    # print(selected_bug)

    query = """
    If there is not enough space to display a word on a single line, HelpFormatter goes into a infinite loops until the JVM crashes with an OutOfMemoryError.

    Test case:

    Options options = new Options();
    options.addOption("h", "help", false, "This is a looooong description");

    HelpFormatter formatter = new HelpFormatter();
    formatter.setWidth(20);
    formatter.printHelp("app", options); // hang & crash
    An helpful exception indicating the insufficient width would be more appropriate than an OutOfMemoryError.
    """

    data = [
        {
            "query": query,
            "label": 40
        }
    ]
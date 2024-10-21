import os
import csv
import shutil
import logging
import json
import time
from .utils import *
from .config import *
import pandas as pd


""" Defects4J """
# Configuring Defects4J.
def configure_defects4j():    
    # Installing dependencies
    execute_bash_command("cpanm --installdeps .", DEFECTS4J_DIR)

    # Initializing Defects4J
    execute_bash_command("./init.sh", DEFECTS4J_DIR)

    # Adding Defects4J's executables to the PATH variable
    if not os.path.normpath(f"{DEFECTS4J_DIR}/framework/bin") in os.environ["PATH"]:
        current_path_variable = os.environ["PATH"]
        os.environ["PATH"] = os.path.normpath(f"{current_path_variable}{os.pathsep}{DEFECTS4J_DIR}/framework/bin")

    # Checking installation
    execute_bash_command("defects4j info -p Lang")
    
# Output of this function should be a list of dictionaries (bugs). Include keys that you want to see in the list view.
def get_bug_list_defects4j():
    projects_dir = os.path.normpath(f"{DEFECTS4J_DIR}/framework/projects")
    bug_list = []

    for project in os.listdir(projects_dir):
        folder_path = os.path.join(projects_dir, project)
        
        if os.path.isdir(folder_path):
            for file in os.listdir(folder_path):
                if file == "active-bugs.csv":
                    file_path = os.path.join(folder_path, file) 

                    with open(file_path, mode='r', newline='', encoding='utf-8-sig') as file:
                        reader = csv.DictReader(file)
                        
                        for row in reader:
                            report_link = row["report.url"]

                            if report_link == "UNKNOWN":
                                report_link = None

                            id_in_project = row["bug.id"]
                            bug_info = {
                                "uid": f"defects4j-{project}-{id_in_project}",
                                "benchmark": "defects4j",
                                "project": project,
                                "number": id_in_project,
                                "report_link": report_link,
                                "language": "Java"
                            }

                            bug_list.append(bug_info)

    return bug_list

def checkout_bug_defects4j(bug):
    bug_uid, id, project = bug.name, bug["number"], bug["project"]
    output_dir = os.path.join(TMP_CHECKOUTS_DIR, f"{bug_uid}")
    
    execute_bash_command(f"defects4j checkout -p {project} -v {id}b -w {output_dir}")

    return output_dir

def checkout_fix_defects4j(bug):
    bug_uid, id, project = bug["uid"], bug["number"], bug["project"]
    output_dir = os.path.join(TMP_CHECKOUTS_DIR, f"{bug_uid}-fixed")
    
    execute_bash_command(f"defects4j checkout -p {project} -v {id}f -w {output_dir}")

    return output_dir

def get_developer_patch_defects4j(bug, buggy_project_dir, fixed_project_dir):
    bug_uid = bug["uid"]
    patch_uid = f"{bug_uid}-developer"

    if bug["project"] == "Chart":
        source_folder = "source"

    elif bug["project"] == "Gson":
        source_folder = os.path.join("gson", "src")

    else:
        source_folder = "src"

    buggy_source = os.path.join(buggy_project_dir, source_folder)
    fixed_source = os.path.join(fixed_project_dir, source_folder)

    diff, _ = execute_bash_command(f"git diff {buggy_source} {fixed_source}", dir=os.path.dirname(PROJECT_DIR), error_allowed=True)

    tmp_patch_dir = os.path.join(TMP_DEVELOPER_PATCH_DIR, f"{patch_uid}.patch")

    with open(tmp_patch_dir, 'w') as file:
        file.write(diff)

    patch = {
        "uid": patch_uid,
        "bug_uid": bug["uid"],
        "generator": "Developer",
        "location": os.path.relpath(tmp_patch_dir, PROJECT_DIR),
        "correctness": "Correct",
        "origin": bug["benchmark"]
    }
    return patch

""" Bugs.jar """
def get_bug_list_bugsjar():
    bugs = []
    
    for folder_name in os.listdir(BUGSJAR_DIR):
        folder_path = os.path.join(BUGSJAR_DIR, folder_name)
        
        # Check if it is a folder
        if os.path.isdir(folder_path) and folder_name != ".git":
            if folder_name == "ID2commit":
                continue

            result = execute_bash_command("git branch -a | grep bugs-dot-jar_", dir=folder_path)

            # Filter the output using grep
            filtered_output = [line for line in result.split('\n') if 'bugs-dot-jar_' in line]
            
            # Print the filtered output
            for line in filtered_output:
                bug_issue_name, sha = line.split("/")[-1].split("_")[1:]
                project_issue_name, issue_number = bug_issue_name.split("-")
                
                with open(os.path.join(BUGSJAR_DIR, "ID2commit", f"{folder_name}.txt")) as map_file:
                    for line in map_file.read().split("\n"):
                        if line.split(",")[1] == f"{project_issue_name}-{issue_number}_{sha}":
                            bug_number = line.split(",")[0]

                            break
                
                bug_info = {
                    "uid": f"bugsjar-{folder_name}-{sha}",
                    "benchmark": "Bugs.jar",
                    "project": folder_name,
                    "sha": sha,
                    "number": bug_number,
                    "project_issue_name": project_issue_name,
                    "issue_number": issue_number, 
                    "report_link": f"https://issues.apache.org/jira/browse/{project_issue_name}-{issue_number}",
                    "language": "Java"
                }
                bugs.append(bug_info)

    return bugs
            
def checkout_bug_bugsjar(bug):
    bug_uid, project, id, folder_name, sha = bug["uid"], bug["project_issue_name"], bug["issue_number"], bug["project"], bug["sha"]
    tmp_bugsjar_dir =os.path.join(TMP_CHECKOUTS_DIR, ".tmp_bugsjar")

    execute_bash_command(f"cp -r {BUGSJAR_DIR} {tmp_bugsjar_dir}")

    project_dir = os.path.join(tmp_bugsjar_dir, folder_name)

    execute_bash_command(f"git checkout bugs-dot-jar_{project}-{id}_{sha}", dir=project_dir)
    
    output_dir = os.path.join(TMP_CHECKOUTS_DIR, f"{bug_uid}")
    
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)

    shutil.copytree(project_dir, output_dir)

    execute_bash_command("rm .git", dir=output_dir)
    execute_bash_command("git init", dir=output_dir)
    execute_bash_command("git add .", dir=output_dir)
    execute_bash_command('git commit -m "init"', dir=output_dir)
    execute_bash_command(f"rm -rf {tmp_bugsjar_dir}")

    return output_dir
            
def get_developer_patch_bugsjar(bug, buggy_project_dir): 
    bug_uid = bug["uid"]
    patch_uid = f"{bug_uid}-developer"
    patch_dir = os.path.join(buggy_project_dir, ".bugs-dot-jar", "developer-patch.diff")
    tmp_patch_dir = os.path.join(TMP_DEVELOPER_PATCH_DIR, f"{patch_uid}.patch")
    execute_bash_command(f"cp {patch_dir} {tmp_patch_dir}")

    patch = {
        "uid": patch_uid,
        "bug_uid": bug["uid"],
        "generator": "Developer",
        "location": os.path.relpath(tmp_patch_dir, PROJECT_DIR),
        "correctness": "Correct",
        "origin": bug["benchmark"]
    }
    return patch
    
def checkout_fix_bugsjar(bug):
    bug_uid, project, id, folder_name, sha = bug["uid"], bug["project_issue_name"], bug["issue_number"], bug["project"], bug["sha"]
    tmp_bugsjar_dir =os.path.join(TMP_CHECKOUTS_DIR, ".tmp_bugsjar")

    execute_bash_command(f"cp -r {BUGSJAR_DIR} {tmp_bugsjar_dir}")

    project_dir = os.path.join(tmp_bugsjar_dir, folder_name)

    execute_bash_command(f"git checkout bugs-dot-jar_{project}-{id}_{sha}", dir=project_dir)
    
    output_dir = os.path.join(TMP_CHECKOUTS_DIR, f"{bug_uid}-fixed")
    
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)

    shutil.copytree(project_dir, output_dir)

    execute_bash_command("rm .git", dir=output_dir)
    execute_bash_command("git init", dir=output_dir)
    execute_bash_command("git add .", dir=output_dir)
    execute_bash_command('git commit -m "init"', dir=output_dir)

    execute_bash_command(f"rm -rf {tmp_bugsjar_dir}")

    patch_dir = os.path.join(output_dir, ".bugs-dot-jar", "developer-patch.diff")

    apply_patch_to_git_repo(output_dir, patch_dir)

    return output_dir


""" QuixBugs """
def get_bug_list_quixbugs_java():
    bugs = []
    correct_dir = os.path.join(QUIXBUGS_DIR, "correct_java_programs")

    for file_name in os.listdir(correct_dir):
        bug_name = None

        if not file_name.endswith(".java"):
            continue

        bug_name = file_name[:-5]

        # Continue before this
        assert bug_name

        bug_info = {
            "uid": f"quixbugs-{bug_name}-java",
            "benchmark": "QuixBugs",
            "project": bug_name,
            "language": "Java"
        }
        bugs.append(bug_info)

    return bugs

def get_bug_list_quixbugs_python():
    bugs = []
    correct_dir = os.path.join(QUIXBUGS_DIR, "correct_python_programs")

    for file_name in os.listdir(correct_dir):
        bug_name = None

        if not file_name.endswith(".py"):
            continue

        bug_name = file_name[:-3]

        # Continue before this
        assert bug_name

        bug_info = {
            "uid": f"quixbugs-{bug_name}-python",
            "benchmark": "QuixBugs",
            "project": bug_name,
            "language": "Python"
        }
        bugs.append(bug_info)

    return bugs

def get_developer_patch_quixbugs_java(bug):
    bug_name, bug_uid = bug["project"], bug["uid"]
    file_name = f"{bug_name}.java"
    patch_uid = f"{bug_uid}-developer"

    # Get buggy file dir
    buggy_file_dir = os.path.join(QUIXBUGS_DIR, "java_programs", file_name)

    # Fix correct file, save it in tmp and get the dir
    correct_file_dir = os.path.join(QUIXBUGS_DIR, "correct_java_programs", file_name)
    
    with open(correct_file_dir, 'r') as input_file:
        correct_file_content = input_file.read()

    correct_file_content = correct_file_content.replace("correct_", "").replace("java_programs;", "java_programs;")
    correct_file_tmp_dir = os.path.join(TMP_CHECKOUTS_DIR, "correct_" + file_name)

    with open(correct_file_tmp_dir, 'w') as output_file:
        output_file.write(correct_file_content)

    # Get diff
    diff, _ = execute_bash_command(f"git diff {buggy_file_dir} {correct_file_tmp_dir}", dir=os.path.dirname(PROJECT_DIR), error_allowed=True)

    # Remove tmp correct file
    os.remove(correct_file_tmp_dir)

    # Save patch
    tmp_patch_dir = os.path.join(TMP_DEVELOPER_PATCH_DIR, f"{patch_uid}.patch")

    with open(tmp_patch_dir, 'w') as file:
        file.write(diff)

    # Generate patch
    patch = {
        "uid": patch_uid,
        "bug_uid": bug["uid"],
        "generator": "Developer",
        "location": os.path.relpath(tmp_patch_dir,PROJECT_DIR),
        "correctness": "Correct",
        "origin": bug["benchmark"]
    }

    return patch

def get_developer_patch_quixbugs_python(bug):
    bug_name, bug_uid = bug["project"], bug["uid"]
    file_name = f"{bug_name}.py"
    patch_uid = f"{bug_uid}-developer"

    # Get buggy file dir
    buggy_file_dir = os.path.join(QUIXBUGS_DIR, "python_programs", file_name)

    # Fix correct file, save it in tmp and get the dir
    correct_file_dir = os.path.join(QUIXBUGS_DIR, "correct_python_programs", file_name)

    # Get diff
    diff, _ = execute_bash_command(f"git diff {buggy_file_dir} {correct_file_dir}", dir=os.path.dirname(PROJECT_DIR), error_allowed=True)

    # Save patch
    tmp_patch_dir = os.path.join(TMP_DEVELOPER_PATCH_DIR, f"{patch_uid}.patch")

    with open(tmp_patch_dir, 'w') as file:
        file.write(diff)

    # Generate patch
    patch = {
        "uid": patch_uid,
        "bug_uid": bug["uid"],
        "generator": "Developer",
        "location": os.path.relpath(tmp_patch_dir, PROJECT_DIR),
        "correctness": "Correct",
        "origin": bug["benchmark"]
    }

    return patch

def checkout_bug_quixbugs(bug):
    if bug["language"] == "Java":
        extension = ".java"
        bug_folder = "java_programs"

    else: 
        extension = ".py"
        bug_folder = "python_programs"

    bug_uid, file_name = bug["uid"], bug["project"]
    file_dir = os.path.join(QUIXBUGS_DIR, bug_folder, f"{file_name}{extension}")
    checkout_file_dir = os.path.join(TMP_CHECKOUTS_DIR, f"{bug_uid}{extension}")
    shutil.copyfile(file_dir, checkout_file_dir)

    return checkout_file_dir


""" Bears """
def get_bug_list_bears():
    bugs = []
    id_branch_map_file = os.path.join(BEARS_DIR, "scripts", "data", "bug_id_and_branch_2019.json")

    with open(id_branch_map_file) as file:
        id_branch_map = json.load(file)

    for mapping in id_branch_map:
        bug_branch = mapping["bugBranch"]
        project = '-'.join(mapping["bugBranch"].split('-')[1:-2])
        developer = mapping["bugBranch"].split('-')[0]
        _, bug_number = mapping["bugId"].split('-')

        # Issues exist for some bug but we will need to checkout first.
        bug = {
            "uid": f"bears-{bug_number}",
            "benchmark": "Bears",
            "number": bug_number,
            "project": project,
            "developer": developer,
            "branch": bug_branch,
            "branch_url": f"https://github.com/bears-bugs/bears-benchmark/tree/{bug_branch}",
            "language": "Java"
        }
        bugs.append(bug)

    return bugs

def checkout_bug_bears(bug):
    bug_uid = bug["uid"]
    checkout_dir = os.path.join(TMP_CHECKOUTS_DIR, bug_uid)

    if os.path.exists(checkout_dir):
        return checkout_dir
    
    new_bug_list_dir = os.path.join(BEARS_DIR, "scripts", "data", "bug_id_and_branch.json")
    old_bug_list_dir = os.path.join(BEARS_DIR, "scripts", "data", "bug_id_and_branch_2019.json")
    execute_bash_command(f"cp {old_bug_list_dir} {new_bug_list_dir}", dir=BEARS_DIR)

    checkout_bug_file = os.path.join(BEARS_DIR, "scripts", "checkout_bug.py")

    with open(checkout_bug_file, 'r') as file:
        content = file.read()

    old_content = """BUGGY_COMMIT = subprocess.check_output(cmd, shell=True).decode("utf-8")"""
    new_content = """BUGGY_COMMIT = subprocess.check_output(cmd, shell=True).decode("utf-8") \nif not BUGGY_COMMIT:
    cmd = "cd %s; git log --format=format:%%H --grep='Bug commit from';" % BEARS_PATH
    BUGGY_COMMIT = subprocess.check_output(cmd, shell=True).decode("utf-8")
    """

    content = content.replace(old_content, new_content)

    with open(checkout_bug_file, 'w') as file:
        file.write(content)

    bug_number = bug["number"]
    command = f"python scripts/checkout_bug.py --bugId Bears-{bug_number} --workspace {TMP_CHECKOUTS_DIR}"

    execute_bash_command(command, dir=BEARS_DIR)

    original_checkout_dir = os.path.join(TMP_CHECKOUTS_DIR, f"Bears-{bug_number}")

    os.rename(original_checkout_dir, checkout_dir)

    return checkout_dir

def checkout_fix_bears(bug):
    bug_uid = bug["uid"]
    checkout_dir = os.path.join(TMP_CHECKOUTS_DIR, f"{bug_uid}-fixed")

    if os.path.exists(checkout_dir):
        return checkout_dir
    
    new_bug_list_dir = os.path.join(BEARS_DIR, "scripts", "data", "bug_id_and_branch.json")
    old_bug_list_dir = os.path.join(BEARS_DIR, "scripts", "data", "bug_id_and_branch_2019.json")
    execute_bash_command(f"cp {old_bug_list_dir} {new_bug_list_dir}", dir=BEARS_DIR)
    
    bug_number = bug["number"]
    command = f"python scripts/checkout_bug.py --bugId Bears-{bug_number} --workspace {TMP_CHECKOUTS_DIR}"

    execute_bash_command(command, dir=BEARS_DIR)

    original_checkout_dir = os.path.join(TMP_CHECKOUTS_DIR, f"Bears-{bug_number}")
    os.rename(original_checkout_dir, checkout_dir)

    bug_branch = bug["branch"]

    # Use checkout command to go to latest commit in this branch.
    execute_bash_command(f"git checkout {bug_branch}", dir=checkout_dir)

    return checkout_dir

def get_developer_patch_bears(bug, buggy_project_dir, fixed_project_dir):
    bug_uid = bug["uid"]
    patch_uid = f"{bug_uid}-developer"

    diff = get_diff(buggy_project_dir, fixed_project_dir, types=[".java"], ignore_dirs=["target"])
    tmp_patch_dir = os.path.join(TMP_DEVELOPER_PATCH_DIR, f"{patch_uid}.patch")

    with open(tmp_patch_dir, 'w') as file:
        file.write(diff)

    patch = {
        "uid": patch_uid,
        "bug_uid": bug["uid"],
        "generator": "Developer",
        "location": os.path.relpath(tmp_patch_dir, PROJECT_DIR),
        "correctness": "Correct",
        "origin": bug["benchmark"]
    }
    return patch


""" IntroClassJava """
def get_bug_list_introclassjava():
    bugs = []

    with open(os.path.join(INTROCLASSJAVA_DIR, "dataset", "introclass.json")) as file:
        data = json.load(file)

    projects = {}

    for key in data:
        projects[key.split('/')[0]] = 0

    # benchmarkBugId
    for _, value in data.items():
        project, user, version = value["projectName"], value["projectUser"], value["projectUserVersion"]

        bug = {
                "uid": f"introclassjava-{project}-{user}-{version}",
                "benchmark": "IntroClassJava",
                "project": project,
                "developer": user,
                "number": version
            }

        bugs.append(bug)

    return bugs


""" General """
def configure_benchmarks():
    logging.info("Configuring benchmarks ...")
    
    configure_defects4j()

def get_bugs():
    bugs = []
    bugs += get_bug_list_bugsjar()
    bugs += get_bug_list_defects4j()
    bugs += get_bug_list_bears()
    bugs += get_bug_list_quixbugs_java()
    # bugs += get_bug_list_quixbugs_python()
    bugs += get_bug_list_introclassjava()

    return bugs

def checkout_bug(bug: pd.DataFrame) -> str:
    if bug["benchmark"] == "Defects4J":
        repo_dir = checkout_bug_defects4j(bug)

    elif bug["benchmark"] == "Bugs.jar":
        repo_dir = checkout_bug_bugsjar(bug)

    elif bug["benchmark"] == "Bears":
        repo_dir = checkout_bug_bears(bug)

    elif bug["benchmark"] == "QuixBugs":
        repo_dir = checkout_bug_quixbugs(bug)

    else:
        raise ValueError("Unexpected benchmark.")

    return repo_dir

def get_developer_patch(bug): 
    logging.info(f"Fetching developer patch of the bug: {bug}")

    bug_uid = bug["uid"]
    patch_uid = f"{bug_uid}-developer"
    location = os.path.join(TMP_DEVELOPER_PATCH_DIR, f"{patch_uid}.patch")

    if os.path.exists(location):
        logging.info(f"Developer patch has already been fetched for the bug: {bug}")


        patch = {
            "uid": patch_uid,
            "bug_uid": bug["uid"],
            "generator": "Developer",
            "location": os.path.relpath(location, PROJECT_DIR),
            "correctness": "Correct",
            "origin": bug["benchmark"]
        }      

        if not read_patch(location).strip():
            raise ValueError

        return patch
            
    if bug["benchmark"] == "Defects4J":
        buggy_project_dir = checkout_bug_defects4j(bug)
        fixed_project_dir = checkout_fix_defects4j(bug)
        patch = get_developer_patch_defects4j(bug, buggy_project_dir, fixed_project_dir)
        shutil.rmtree(buggy_project_dir)
        shutil.rmtree(fixed_project_dir)

    elif bug["benchmark"] == "Bugs.jar":
        buggy_project_dir = checkout_bug_bugsjar(bug)
        patch = get_developer_patch_bugsjar(bug, buggy_project_dir)
        time.sleep(2)
        
        shutil.rmtree(buggy_project_dir)

    elif bug["benchmark"] == "Bears":
        buggy_project_dir = checkout_bug_bears(bug)
        fixed_project_dir = checkout_fix_bears(bug)
        patch = get_developer_patch_bears(bug, buggy_project_dir, fixed_project_dir)
        shutil.rmtree(buggy_project_dir)
        shutil.rmtree(fixed_project_dir)

    elif bug["benchmark"] == "QuixBugs":
        if bug["language"] == "Java":
            patch = get_developer_patch_quixbugs_java(bug)

        elif bug["language"] == "Python":
            patch = get_developer_patch_quixbugs_python(bug)

    if not read_patch(location).strip():
        raise ValueError

    return patch

def get_developer_patches(bugs):
    logging.info("Fetching developer patches ...")

    patches = []

    for bug in bugs:

        if bug["benchmark"] == "IntroClassJava":
            continue

        patch = get_developer_patch(bug)

        patches.append(patch)

    logging.info("Developer patches are fetched.")

    return patches

# Fixes patch and stores it: returns relpath of the fixed patch
def fix_patch(patch: pd.Series, bugs: pd.DataFrame) -> str:
    patch_uid = patch.name
    formatted_patch_dir = os.path.join(TMP_FORMATTED_PATCH_DIR, f"{patch_uid}.patch")

    logging.info(f"Fixing the patch: {patch_uid}")

    # Check if patch exists
    if os.path.exists(formatted_patch_dir):
        logging.info(f"Formatted patch already exists.")

        return os.path.relpath(formatted_patch_dir, PROJECT_DIR)

    patch_abs_dir = os.path.join(PROJECT_DIR, patch["location"])

    bug = bugs.loc[patch["bug_uid"]].to_dict()
    bug["uid"] = patch["bug_uid"]

    one_file = False

    if bug["benchmark"] == "Defects4J":
        checkout_abs_dir = checkout_bug_defects4j(bug)
    
    elif bug["benchmark"] == "Bugs.jar":
        checkout_abs_dir = checkout_bug_bugsjar(bug)

    elif bug["benchmark"] == "Bears":
        checkout_abs_dir = checkout_bug_bears(bug)

    elif bug["benchmark"] == "QuixBugs":
        one_file = True
        checkout_abs_dir = checkout_bug_quixbugs(bug)

    else:
        raise ValueError("Unexpected benchmark.")
    
    if one_file:
        diff = fix_file_patch(patch_abs_dir, checkout_abs_dir)

        os.remove(checkout_abs_dir) 

    else:
        diff = fix_repo_patch(patch_abs_dir, checkout_abs_dir)

        shutil.rmtree(checkout_abs_dir, onerror=rmtree)

    # Output
    if diff:
        logging.info(f"Fixed the patch: {patch_uid}") 

        with open(formatted_patch_dir, 'w') as file:
            file.write(diff)

        return os.path.relpath(formatted_patch_dir, PROJECT_DIR)
    
    logging.info(f"Could not fix the patch: {patch_uid}") 

    return None 

def get_bug_repo_src(bug):
    if bug["benchmark"] == "defects4j":
        if "Cli" in bug.name:
            return os.path.join(bug['checkout_dir'], "src/java/org/apache/commons/cli")
        
    raise "Could not find the source directory for the bug!"

# Returns method
def get_method(patch: pd.Series, bugs: pd.DataFrame = None):
    patch_uid = patch.name

    logging.info(f"Getting method of the patch: {patch_uid}")

    out_put_dir = os.path.join(TMP_METHODS_DIR, patch.name)

    if os.path.exists(out_put_dir):
        logging.info(f"Methods already exist for the patch: {patch_uid}")

        all_files = os.listdir(out_put_dir)

        # Filter and sort the files for target and source files
        target_files = sorted([f for f in all_files if f.startswith('target-')], key=lambda x: int(x.split('-')[1].split('.')[0]))
        source_files = sorted([f for f in all_files if f.startswith('source-')], key=lambda x: int(x.split('-')[1].split('.')[0]))

        # Append the absolute paths to the respective lists
        source_method_dirs = [os.path.abspath(os.path.join(out_put_dir, f)) for f in target_files]
        target_method_dirs = [os.path.abspath(os.path.join(out_put_dir, f)) for f in source_files]

        if not source_method_dirs or not target_method_dirs:
            raise ValueError

        return source_method_dirs, target_method_dirs

    os.makedirs(out_put_dir)

    bug = get_dictionary(bugs.loc[patch["bug_uid"]])
    repo_dir = checkout_bug(bug)
    one_file = False

    if bug["benchmark"] == "QuixBugs":
        one_file = True

    try:
        if one_file:
            source_method_dirs, target_method_dirs = get_java_modified_methods_git_repo(out_put_dir, TMP_CHECKOUTS_DIR, os.path.join(PROJECT_DIR, patch["location"]))

        else:
            source_method_dirs, target_method_dirs = get_java_modified_methods_git_repo(out_put_dir, repo_dir, os.path.join(PROJECT_DIR, patch["location"]))
            
    except (javalang.parser.JavaSyntaxError, UnicodeDecodeError, unidiff.errors.UnidiffParseError):        
        logging.info(f"Could not parse the patch while getting the method: {patch_uid}")
        shutil.rmtree(out_put_dir)
        shutil.rmtree(repo_dir, onerror=rmtree)

        return None

    if one_file:
        os.remove(repo_dir)
        
    else:
        shutil.rmtree(repo_dir, onerror=rmtree)

    if not source_method_dirs or not target_method_dirs:
        raise ValueError

    logging.info(f"Successfully fetched methods of the patch: {patch_uid}")

    return source_method_dirs, target_method_dirs

# Returns diff
def get_raw_patch(patch: pd.Series) -> str:
    return read_patch(patch["location"])

def get_single_hunk_method(patch: pd.Series):
    _, target_method_dirs = get_method(patch)

    if len(target_method_dirs) != 1:
        raise "The patch is not single hunk."

    return read_patch(target_method_dirs[0])

def are_single_hunks(patch: pd.Series, developer_patches: pd.DataFrame) -> bool:
    if get_patch_edit_numbers(patch["location"])["hunk"] != 1:
        return False
    
    if get_patch_edit_numbers(developer_patches.loc[f"{patch['bug_uid']}-developer"]["location"])["hunk"] != 1:
        return False
    
    return True

def is_single_hunk(patch: pd.Series):
    if get_patch_edit_numbers(patch["location"])["hunk"] != 1:
        return False
    
    return True

# Get All Methods in the Source
def get_source_methods(bug):
    all_methods = []

    for root, _, files in os.walk(get_bug_repo_src(bug)):
        for file in files:
            if file.endswith(".java"):
                file_path = os.path.join(root, file)
                methods, positions = get_java_file_methods(file_path)

                method_info = [
                    {
                        'path': file_path,
                        'method': method, 
                        'position': pos
                    }
                    
                    for method, pos in zip(methods, positions)
                ]

                all_methods += method_info

        methods_df = pd.DataFrame(all_methods)
        pickle_path = os.path.join(TMP_RESULTS_DIR, f'{bug.name}.pkl')
        methods_df.to_pickle(pickle_path)

        return pickle_path


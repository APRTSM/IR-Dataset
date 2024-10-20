import re
import subprocess
import os
import javalang
import shutil
import json
import logging
from unidiff import PatchSet
import pandas as pd
from dataclasses import dataclass
import unidiff
import collections
from .config import *


""" Bash """
def execute_bash_command(command, dir=None, error_allowed=False):
    if dir:
        result = subprocess.run(command, cwd=dir, shell=True, capture_output=True)

    else:
        result = subprocess.run(command, shell=True, capture_output=True)

    stdout = result.stdout.decode("latin-1")
    stderr = result.stderr.decode("latin-1")

    if not error_allowed:
        assert result.returncode == 0, stderr

        return stdout


    return stdout, stderr

def rmtree(func, dir, info):
    command = f"rm -rf {dir}"

    execute_bash_command(command)


""" Data List """
# Get object corresponding to the existing features
def get_record(records, record_info):
    records_copy = records.copy()

    for key, value in record_info.items():
        for record in records:
            if not key in record or record[key] != value:
                try:
                    records_copy.remove(record) 

                except:
                    pass
    
    if not len(records_copy) == 1:
        logging.info(f"Could not find a record for the given info: {record_info}, List of Matching Records: {records_copy}")

        return None
    
    # assert len(records_copy) == 1, f"Invalid record information. {record_info}"

    return records_copy[0]

def get_all(data_dir, file_name):
    with open(os.path.join(data_dir, file_name)) as file:
        return json.load(file)

def commit(data_dir, file_name, dataset):
    with open(os.path.join(data_dir, file_name), "w") as file:                
        file.seek(0)
        file.write(json.dumps(dataset))

def add_object(file_name, item):
    items = get_all(file_name)
    items.append(item)
    
    commit(file_name, items)

def get_objects_by_feature(dataset, feature, value):
    items = []

    for item in dataset:
        if item[feature] == value:
            items.append(item)

    return items

def get_object_by_unique_feature(dataset, feature, value):
    for item in dataset:
        if item[feature] == value:
            return item

def get_object_by_uid(dataset, uid):
    for item in dataset:
        if item["uid"] == uid:
            return item

def get_foreign_key_pairs(dataset, foreign_key_field_name):
    pairs = {}

    for item in dataset:
        try:
            pairs[item[foreign_key_field_name]].append(item)

        except:
            pairs[item[foreign_key_field_name]] = [item]

    return pairs

def get_objects_by_relation(dataset, feature, relation_feature, value):
    items = []

    for item in dataset:
        for relation in item[feature]:
            if relation[relation_feature] == value:
                items.append(item)
            
    return items

def remove_by_uid(dataset, uid):
    for index, item in enumerate(dataset):
        if item["uid"] == uid:
            dataset.pop(index)

            return dataset

def edit_object(dataset, edited_item):
    item = get_object_by_uid(dataset, edited_item["uid"])
    dataset[dataset.index(item)] = edited_item

    return dataset

def get_dictionary(series: pd.Series) -> dict:
    object = series.to_dict()
    object["uid"] = series.name

    return object


""" Files """
def delete_file_type(dir, types):
    for dirpath, _, filenames in os.walk(dir):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            remove = True

            for type in types:

                if filename.endswith(type):
                    remove = False

            if remove:
                os.remove(file_path)

def delete_dirs(root_dir, dirs):
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            remove = False

            for dir in dirs:

                if f"/{dir}/" in file_path:
                    remove = True

            if remove:
                os.remove(file_path)

def remove_empty_lines(input_string):
    return "\n".join(line for line in input_string.splitlines() if line.strip())


""" Patch Files """
def get_diff(source_dir, target_dir, types=[], ignore_dirs=[]):
    tmp_source_dir = os.path.join(TMP_CHECKOUTS_DIR, ".diff_source")
    tmp_target_dir = os.path.join(TMP_CHECKOUTS_DIR, ".diff_target")

    shutil.copytree(source_dir, tmp_source_dir)
    shutil.copytree(target_dir, tmp_target_dir)

    if types:
        delete_file_type(tmp_source_dir, types)
        delete_file_type(tmp_target_dir, types)

    if ignore_dirs:
        delete_dirs(tmp_source_dir, ignore_dirs)
        delete_dirs(tmp_target_dir, ignore_dirs)
        
    command = f"git diff --no-index {tmp_source_dir} {tmp_target_dir}"
    diff, _ = execute_bash_command(command, error_allowed=True)
    
    shutil.rmtree(tmp_source_dir)
    shutil.rmtree(tmp_target_dir)

    return diff

def reset_applied_patch_git_repo(repo_dir):
    execute_bash_command(f"git reset --hard HEAD", repo_dir)

def apply_patch_to_git_repo(repo_dir, patch_dir):
    execute_bash_command(f"git apply --whitespace=fix --ignore-space-change --ignore-whitespace {patch_dir}", repo_dir)

def format_file_patch(location: str, file_location: str = None) -> str:
    with open(location, 'r') as file:
        lines = file.readlines()
    
    modified_lines = []
    last_src_path = None  # To hold the last valid src path
    diff_pattern = re.compile(r'^diff --git a/.+ b/.+')
    index_pattern = re.compile(r'^index \w+\.\.\w+ \d+')

    for line in lines:
        if diff_pattern.match(line) or index_pattern.match(line):
            continue

        if line.startswith("+++ "):
            line = line[:4] + f"b{last_src_path}" + '\n'

        elif line.startswith("--- "):
            if file_location:
                file_name = os.path.basename(file_location)

            else:
                file_name = os.path.basename(line.split('\t')[0].split(' ')[1].strip())

            path_part = f"/{file_name}"  # Remove the timestamp and other parts
            last_src_path = path_part  # Update last known good src path
            line = line[:4] + f"a{last_src_path}" + '\n'

        # Append the modified or original line
        modified_lines.append(line)

    # Write the modified content to a new file in the output directory
    return ''.join(modified_lines)

def format_patch(location: str, source_file: str = "") -> str:
    if not source_file:
        diff = read_patch(location).replace("PATCH_DIFF_ORIG=", "")

        if "--- a/" in diff:
            return diff

    with open(location, 'r') as file:
        lines = file.readlines()
    
    modified_lines = []
    last_src_path = None  # To hold the last valid src path
    diff_pattern = re.compile(r'^diff --git a/.+ b/.+')
    index_pattern = re.compile(r'^index \w+\.\.\w+ \d+')

    index = 0
    while index < len(lines):
        line = lines[index]
        line = line.replace("PATCH_DIFF_ORIG=", "")

        if diff_pattern.match(line) or index_pattern.match(line):
            index += 1
            
            continue

        if line.startswith("+++ "):
            try:
                line = line[:4] + f"b{last_src_path}" + '\n'

            except:
                line = "--- " + modified_lines.pop()
                index -= 1

        if line.startswith("--- "):
            # Find the index of "src" or "source" in the path
            source_index = line.find(f"/{source_file}/")

            if source_index != -1:
                # Extract the path starting from "src" or "source"
                path_part = line[source_index:].split('\t')[0].strip()  # Remove the timestamp and other parts
                
                if path_part.endswith("java") and not path_part.endswith(".java"):
                    path_part = path_part[:-4] + ".java"

                last_src_path = path_part  # Update last known good src path
                line = line[:4] + f"a{last_src_path}" + '\n'
            else:
                path_part = f"/{source_file}/" + line.split('\t')[0].split(' ')[1].strip()  # Remove the timestamp and other parts
                last_src_path = path_part  # Update last known good src path
                line = line[:4] + f"a{last_src_path}" + '\n'
        
        # Append the modified or original line
        modified_lines.append(line)
        index += 1


    # Write the modified content to a new file in the output directory
    return ''.join(modified_lines)

def fix_file_patch(patch_location: str, file_location: str) -> str:
    repo_dir = os.path.dirname(file_location)
    formatted_patch_dir = os.path.join(TMP_DIR, "tmp-patch.patch")
    diff = format_file_patch(patch_location, file_location)

    with open(formatted_patch_dir, 'w') as file:
        file.write(diff)

    command = f"git apply --whitespace=fix --ignore-space-change --ignore-whitespace {formatted_patch_dir}"
    _, stderr = execute_bash_command(command, repo_dir, error_allowed=True) 
    os.remove(formatted_patch_dir) 

    if stderr.strip() == "":
        return diff

    else:
        return None
    
def fix_repo_patch(patch_location: str, repo_location: str) -> str:
    formatted_patch_dir = os.path.join(TMP_DIR, "tmp-patch.patch")
    changes = [
        "",
        "source",
        "src",
        "src/main/java",
        "src/java",
        "gson/src",
        "modules",
        "core/src",
        "suite",
        "dubbo-cluster/src",
        "hessian-lite/src",
        "dubbo-config/dubbo-config-spring/src",
        "dubbo-config/dubbo-config-api/src",
        "dubbo-remoting/dubbo-remoting-api/src",
        "service-registry/src",
        "foundations/foundation-config/src",
        "oak-core/src",
        "integration/hibernate-base/src",
        "runtime/src",
        "navigation-formats/src",
        "debezium-connector-postgres/src",
        "debezium-connector-mysql/src",
        "dhis-2/dhis-api/src",
        "address-model-lib/src",
        "address-controller/src",
        "pinot-core/src",
        "molgenis-semantic-mapper/src",
        "molgenis-data-csv/src",
        "molgenis-data-security/src",
        "molgenis-data-postgresql/src",
        "molgenis-data-import/src",
        "zipkin2/src",
        "byte-buddy-dep/src",
        "spring-cloud-gcp-storage/src",
        "spring-cloud-gcp-data-spanner/src",
        "activiti-cloud-app-service/src",
        "dubbo-rpc/dubbo-rpc-api/src",
        "code/spi-support/src",
        "cas-client-core/src",
        "amazon-kinesis-client/src",
        "axon-server-connector/src",
        "common/src",
        "apollo-adminservice/src",
        "openhtmltopdf-core/src",
        "yaml/src",
        "BaragonAgentService/src",
        "api/src",
        "omod-1.9/src",
        "pippo-session-parent/pippo-session/src",
        "wffweb/src",
        "jgrapht-core/src",
        "seeds-core/src",
        "ci-droid-tasks-consumer-services/src",
        "cxx-checks/src",
        "vertx-web-client/src"
    ]

    if "bears-152" in patch_location or "bears-168" in patch_location or "bears-173" in patch_location or "bears-211" in patch_location:
        return None

    for source_folder in changes: 
        diff = format_patch(patch_location, source_folder)

        with open(formatted_patch_dir, 'w') as file:
            file.write(diff)

        command = f"git apply --whitespace=fix --ignore-space-change --ignore-whitespace {formatted_patch_dir}"
        _, stderr = execute_bash_command(command, repo_location, error_allowed=True)

        os.remove(formatted_patch_dir)

        if "patch fragment without header" in stderr:
            diff = "--- " + diff

            with open(formatted_patch_dir, 'w') as file:
                file.write(diff)

            command = f"git apply --whitespace=fix --ignore-space-change --ignore-whitespace {formatted_patch_dir}"
            _, stderr = execute_bash_command(command, repo_location, error_allowed=True)

            os.remove(formatted_patch_dir)

            if "patch fragment without header" in stderr:
                diff = remove_empty_lines(diff[4:])

                with open(formatted_patch_dir, 'w') as file:
                    file.write(diff)

                command = f"git apply --whitespace=fix --ignore-space-change --ignore-whitespace {formatted_patch_dir}"
                _, stderr = execute_bash_command(command, repo_location, error_allowed=True)

                os.remove(formatted_patch_dir)

        if "corrupt patch at" in stderr:
            diff = diff + "\n\n\n\n"

            with open(formatted_patch_dir, 'w') as file:
                file.write(diff)

            command = f"git apply --whitespace=fix --ignore-space-change --ignore-whitespace {formatted_patch_dir}"
            _, stderr = execute_bash_command(command, repo_location, error_allowed=True)

            os.remove(formatted_patch_dir)

        if "No such file or directory" in stderr:
            continue
    
        elif stderr.strip() == "" or "warning" in stderr:
            return diff
        
        elif "patch does not apply" in stderr:
            logging.info("The patch does not apply.")

            return None
        
        elif "already exists in working directory" in stderr:
            logging.info("The patch adds a file that already exists.")

            return None

        elif "git diff header lacks filename information" in stderr:
            logging.info("The patch header lacks filename information.")

            return None
        
        elif "bad git-diff" in stderr:
            logging.info("The patch has bad git-diff format.")

            return None    
        
        elif "corrupt patch at" in stderr:
            logging.info("Could not fix corrupted patch.")

            return None
        
        else:
            raise Exception(f"Unexpected stderr content while fixing the patch. Error: {stderr}")
        
    logging.info("Unexpected source file type for the patch.")
        
    raise Exception("Unexpected source file type for the patch.")    

def format_and_apply_patch_to_file(file_dir, patch_dir):
    repo_dir = os.path.dirname(file_dir)
    formatted_patch_dir = os.path.join(TMP_DIR, "tmp-patch.patch")
    diff = format_file_patch(patch_dir, file_dir)

    with open(formatted_patch_dir, 'w') as file:
        file.write(diff)

    command = f"git apply --whitespace=fix --ignore-space-change --ignore-whitespace {formatted_patch_dir}"
    _, stderr = execute_bash_command(command, repo_dir, error_allowed=True) 
    os.remove(formatted_patch_dir) 

    if stderr.strip() == "":
        logging.info("The file patch applied correctly.")

        return True

    else:
        logging.info("The file patch does not apply.")

        return False

def format_and_apply_patch_to_git_repo(repo_dir, patch_dir):
    _, stderr = execute_bash_command(f"git apply --whitespace=fix --ignore-space-change --ignore-whitespace {patch_dir}", repo_dir, error_allowed=True)
    formatted_patch_dir = os.path.join(TMP_DIR, "tmp-patch.patch")

    if stderr.strip() == "" or "warning" in stderr:
        logging.info("The patch applied without a change.")

        return True
    
    if "patch does not apply" in stderr:
        logging.info(f"The patch does not apply. It is not formatted.")

        return False

    for source_folder in ["source", "src", "src/main/java", "src/java"]: 
        diff = format_patch(patch_dir, source_folder)

        with open(formatted_patch_dir, 'w') as file:
            file.write(diff)

        _, stderr = execute_bash_command(f"git apply --whitespace=fix --ignore-space-change --ignore-whitespace {formatted_patch_dir}", repo_dir, error_allowed=True)
        
        os.remove(formatted_patch_dir)

        if stderr.strip() == "" or "warning" in stderr:
            logging.info(f"The patch is formatted. Source Folder: {source_folder}")

            return True
        
        if "patch does not apply" in stderr:
            logging.info(f"The patch does not apply. It is formatted. Source Folder: {source_folder}")

            return False
        

    return False

def get_modified_files(patch_dir):
    modified_files = []
    with open(patch_dir) as file:
        patch = file.read()

    patch = PatchSet(patch)

    for patched_file in patch:
        modified_files.append(patched_file.path)

    return modified_files

def get_modified_classes_java(repo_dir, modified_files):
    modified_classes = []
    
    for modified_file in modified_files:
        file_dir = os.path.join(repo_dir, modified_file)

        with open(file_dir) as file:
            code_content = file.read()

        class_name = file_dir.split("/")[-1][:-5]
        pattern = r'package(.*?);'
        match = re.search(pattern, code_content, re.DOTALL)
        modified_classes.append(match.group(1).strip() + '.' + class_name)

    return modified_classes

def get_modified_files_git_repo(output_dir, checkout_dir, patch_dir):
    with open(patch_dir) as f:
        patch = PatchSet(f.read())

    patch_name = os.path.basename(patch_dir)[:-6]
    for i, patchedFile in enumerate(patch):  # different files
        source_start = []  # collect all star lines and find methods in class
        target_start = []
        for hunk in patchedFile:
            bias = -1
            target_start_2nd = -1
            source_start_2nd = -1
            curHunkCnt = [0,0]
            for j, x in enumerate(hunk):
                if x.line_type == '-':
                    source_start.append(x.source_line_no-1)
                    curHunkCnt[0] += 1
                elif x.line_type == '+':
                    target_start.append(x.target_line_no-1)
                    curHunkCnt[1] += 1
                elif sum(curHunkCnt) == 0:
                    if x.target_line_no is not None:
                        target_start_2nd = x.target_line_no-1
                    if x.source_line_no is not None:
                        source_start_2nd = x.source_line_no - 1
            if target_start.__len__() == 0 or curHunkCnt[1] == 0:
                target_start.append(target_start_2nd)
            elif source_start.__len__() == 0 or curHunkCnt[0] == 0:
                source_start.append(source_start_2nd)


        export_dir = os.path.join(output_dir, patch_name)
        
        if not os.path.exists(export_dir):
            os.makedirs(export_dir)

        original_file_dir =  os.path.join(output_dir, patch_name, f"source_file_{i}.java")
        changed_file_dir = os.path.join(output_dir, patch_name, f"target_file_{i}.java")

        shutil.copy(os.path.join(checkout_dir, patchedFile.source_file[2:]), original_file_dir)
        shutil.copy(os.path.join(checkout_dir, patchedFile.source_file[2:]), changed_file_dir)

        return original_file_dir, changed_file_dir
    
def read_patch(location):
    with open(location) as file:
        diff = file.read()

    return diff

keys = []
@dataclass
class FormattedPatch():
    modules: list[str]
    default_formats = {
        'module': '%s',
        'file_diffs': '%s',
        'hunk': 'Hunk %d',
        'line_numbers': '@@  %s  @@',
        '-line': '-%s',
        '+line': '+%s',
    }
    formats = default_formats.copy()
    
    @classmethod
    def turn_off(self, keys):
        print(keys)
        for key in keys:
            FormattedPatch.formats[key] = ''
            
    @classmethod     
    def reset(self, keys = None):
        if keys == None:
            keys = FormattedPatch.default_formats.keys()
        for key in keys:
            FormattedPatch.formats[key] = FormattedPatch.default_formats[key]
    
    def __init__(self, location):
        self.patchset = unidiff.PatchSet.from_filename(location)   
        
        self.modules = []
        for file in self.patchset:
            file_diff = repr(file)
            module_name_marker_idx = file_diff.find('.')
            module_name_start = file_diff.rfind('/', 0, module_name_marker_idx) + 1
            module_name_end = file_diff.find('\t', module_name_marker_idx)
            self.modules.append(file_diff[module_name_start: module_name_end])
        
        self.print_config = collections.defaultdict(lambda: True)
    def __str__(self):
        patch = ''
        for module, patched_file in zip(self.modules, self.patchset):
            if self.formats['module']:
                patch += self.formats['module'] % module + '\n'
                
            line_numbers = []
            hunks = []
            for hunk in patched_file:
                lines = str(hunk).splitlines()
                line_numbers.append(lines[0].strip('@@').strip())
                hunks.append('\n'.join(lines[1:]))

            for i, hunk in enumerate(hunks):
                hunk_to_print = []
                
                for line in hunk.splitlines():
                    format_diff_line = None
                    
                    if line.startswith('-'):
                        if not self.formats['-line']:
                            continue
                        else:
                            format_diff_line = '-'
                    elif line.startswith('+'):
                        if not self.formats['+line']:
                            continue
                        else:
                            format_diff_line = '+'
                    else:
                        hunk_to_print.append(line)
                        
                    if format_diff_line:
                        format = self.formats['+line'] if format_diff_line == '+' else self.formats['-line']
                        line = ' ' + line[1:]
                        indent = 0
                        for c in line:
                            if c == ' ':
                                indent += 1
                            elif c == '\t':
                                indent += 4
                            if not c.isspace():
                                break

                        format_character_count = len(format) - 2
                        line = line.strip()
                        line = line.rjust(len(line) + indent - format_character_count)
                        line = format % line
                        hunk_to_print.append(line)
                        
                if self.formats['hunk']:    
                    patch += self.formats['hunk'] % (i + 1 ) + '\n'
                if self.formats['line_numbers']:
                    patch += self.formats['line_numbers'] % line_numbers[i] + '\n'
                patch += '\n'.join(hunk_to_print) + '\n'
        return patch

def get_patch_edit_numbers(location):
    file_counts = []
    hunk_counts = []
    source_line_counts = []
    target_line_counts = []

    try:
        patchset = unidiff.PatchSet.from_filename(location)

    except unidiff.errors.UnidiffParseError as e:
        if "Unexpected new file found" in str(e):
            file_sum = 0
            hunk_sum = 0
            source_sum = 0
            target_sum = 0
            
        else:
            raise e

    else:
        file_counts.append(len(patchset))
        hunk_count = sum(len(file) for file in patchset) # Sum the hunks for all files
        hunk_counts.append(hunk_count)
        hunks = [hunk for file in patchset for hunk in file] # Flatten hunks from all files
        source_line_counts.append(sum(hunk.source_length for hunk in hunks))
        target_line_counts.append(sum(hunk.target_length for hunk in hunks))

        file_sum = sum(file_counts)
        hunk_sum = sum(hunk_counts)
        source_sum = sum(source_line_counts)
        target_sum = sum(target_line_counts)

    counts = {
        'file': file_sum,
        'hunk': hunk_sum,
        'source': source_sum,
        'target': target_sum
    }

    return counts


""" Java Code """
def get_java_modified_methods_git_repo(output_dir, checkout_dir, patch_dir): # Later devide this function to functions    
    def annotate_unsupport_code(code):
        for i, line in enumerate(code):
            if line.startswith("package ") or line.startswith("import "):
                code[i] = '//' + code[i]
        return code

    def get_ast(functions):
        func = annotate_unsupport_code(functions)
        tokens = javalang.tokenizer.tokenize("".join(func))
        parser = javalang.parser.Parser(tokens)
        tree = parser.parse_member_declaration()
        return tree
    
    replaceString = re.compile("[\"].*?[\"]")

    def get_end_line(start_line, file_back, upper_limit):
        file = file_back.copy()
        left_bracket = 0
        right_bracket = 0
        for i in range(start_line, upper_limit):
            anno_index = file[i].find('//')
            file[i] = file[i][:anno_index] if anno_index != -1 else file[i]
            file[i] = replaceString.sub("",file[i]) ##
            left_bracket += file[i].count('{')
            right_bracket += file[i].count('}')
            if right_bracket == left_bracket and right_bracket:
                return i
        if right_bracket == left_bracket and right_bracket == 0:
            return start_line
        else:
            return -1

    def get_function_positions(tree, class_file):
        position = []  # start from 0
        methods = []
        for x in tree.body:
            if isinstance(x, javalang.tree.ClassDeclaration):
                for y in x.body:
                    if isinstance(y,javalang.tree.ClassDeclaration):
                        methods.extend(y.methods)
                    elif isinstance(y,javalang.tree.MethodDeclaration) or isinstance(y, javalang.tree.ConstructorDeclaration):
                        methods.append(y)
            elif isinstance(x, javalang.tree.MethodDeclaration) or isinstance(x, javalang.tree.ConstructorDeclaration):
                methods.append(x)
        if methods.__len__() == 0:
            methods.extend(tree.methods)
        for i, method in enumerate(methods):
            start_line = method.position.line - 1
            if i + 1< methods.__len__():
                upper_limit = methods[i+1].position.line - 1
            else:
                upper_limit = class_file.__len__() -1
            end_line = get_end_line(start_line, class_file,upper_limit)
            if end_line == -1:
                continue
            position.append((start_line, end_line))
        position = list(set(position))
        position.sort()
        return position

    with open(patch_dir) as f:
        patch = PatchSet(f.read())

    source_methods = []
    target_methods = []
    buggy_methods = []
    patched_methods = []
    patch_name = os.path.basename(patch_dir)[:-6]
    for i, patchedFile in enumerate(patch):  # different files
        source_start = []  # collect all star lines and find methods in class
        target_start = []
        for hunk in patchedFile:
            bias = -1
            target_start_2nd = -1
            source_start_2nd = -1
            curHunkCnt = [0,0]
            for j, x in enumerate(hunk):
                if x.line_type == '-':
                    source_start.append(x.source_line_no-1)
                    curHunkCnt[0] += 1
                elif x.line_type == '+':
                    target_start.append(x.target_line_no-1)
                    curHunkCnt[1] += 1
                elif sum(curHunkCnt) == 0:
                    if x.target_line_no is not None:
                        target_start_2nd = x.target_line_no-1
                    if x.source_line_no is not None:
                        source_start_2nd = x.source_line_no - 1
            if target_start.__len__() == 0 or curHunkCnt[1] == 0:
                target_start.append(target_start_2nd)
            elif source_start.__len__() == 0 or curHunkCnt[0] == 0:
                source_start.append(source_start_2nd)

        original_file = os.path.join(checkout_dir, patchedFile.source_file[2:])

        with open(original_file) as file:
            buggy_class = file.readlines()

        apply_patch_to_git_repo(checkout_dir, patch_dir)

        changed_file = os.path.join(checkout_dir, patchedFile.source_file[2:])

        with open(changed_file) as file:
            patched_class = file.readlines()

        reset_applied_patch_git_repo(checkout_dir)

        buggy_tree = get_ast(buggy_class)
        patched_tree = get_ast(patched_class)
        buggy_funtions_position = get_function_positions(buggy_tree, buggy_class)
        patched_funtions_position = get_function_positions(patched_tree, patched_class)
        buggy_methods_pos = set()
        patched_methods_pos = set()
        for start in source_start:
            for pos in buggy_funtions_position:
                if pos[0] <= start and start <= pos[1]:
                    buggy_methods_pos.add(pos)
                    break
        for start in target_start:
            for pos in patched_funtions_position:
                if pos[0] <= start and start <= pos[1]:
                    patched_methods_pos.add(pos)
        for x in buggy_methods_pos:
            buggy_methods.append("".join(buggy_class[x[0]:x[1]+1]))
        for x in patched_methods_pos:
            patched_methods.append("".join(patched_class[x[0]:x[1]+1]))

        buggy_method_dir = os.path.join(output_dir, f"source-{i}.java")
        patched_method_dir = os.path.join(output_dir, f"target-{i}.java")
        
        with open(buggy_method_dir, 'w') as file:
            file.write("".join(buggy_methods))

        with open(patched_method_dir, 'w') as file:
            file.write("".join(patched_methods))

        source_methods.append(buggy_method_dir)
        target_methods.append(patched_method_dir)

    return source_methods, target_methods    

""" Result Processing """
def get_response_result(response):
    yes_pattern = re.compile(r'\byes\b', re.IGNORECASE)
    no_pattern = re.compile(r'\bno\b', re.IGNORECASE)
    type_patterns = {}
    for type in ['1','2','3','4']:
        type_patterns[type] = re.compile(rf'\b(type {type}|type-{type}|t{type})\b', re.IGNORECASE)
    clone_pattern = re.compile(r'\b(are clones|are code clones)\b',  re.IGNORECASE)
    not_clone_pattern = re.compile(r"\b(are not clones|aren't clones|are not code clones|aren't code clones)\b",  re.IGNORECASE)
    
    features = {}
    features['yes'] = bool(yes_pattern.search(response))
    features['no'] = bool(no_pattern.search(response))
    features['clone'] = bool(clone_pattern.search(response))
    features['not_clone'] = bool(not_clone_pattern.search(response))
    features['1'] = bool(type_patterns['1'].search(response))
    features['2'] = bool(type_patterns['2'].search(response))
    features['3'] = bool(type_patterns['3'].search(response))
    features['4'] = bool(type_patterns['4'].search(response))
    
    feature_list = []
    if features['yes']:
        feature_list.append('yes')
    elif features['no']:
        feature_list.append('no')
    
    for type in ['1','2','3','4']:
        if features[type]:
            feature_list.append('t'+type)
    
    return feature_list

 
if __name__ == '__main__':
    pass
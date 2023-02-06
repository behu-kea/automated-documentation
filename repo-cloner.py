import shutil

import git
import os
from fnmatch import fnmatch
import javalang
import openai
import dotenv
from javalang.tree import MethodDeclaration

MIN_METHOD_SIZE_TO_DOCUMENT = 3
REPO_URL = "https://github.com/behu-kea/spring-petclinic.git"

code_directory = 'code-to-document'
shutil.rmtree(code_directory)

dotenv.load_dotenv()

destination_folder = code_directory
repo = git.Repo.clone_from(REPO_URL, destination_folder)
repo.git.checkout("-b", "automatic-documentation")
pattern = "*.java"

java_file_directories = []
for path, subdirs, files in os.walk(destination_folder):
    for name in files:
        if fnmatch(name, pattern):
            file_directory = os.path.join(path, name)
            java_file_directories.append(file_directory)


def get_completion(prompt):
    openai.api_key = os.getenv("OPENAI_KEY")
    return openai.Completion.create(
        model="text-davinci-003",
        prompt=prompt,
        max_tokens=400,
        temperature=0
    )


def get_method_name_with_parameters(node):
    method_name = node.name
    parameters = [
        " ".join(["@" + ann.name for ann in param.annotations]) + " " + param.type.name + " " + param.name
        for param in node.parameters
    ]
    return "{}({})".format(method_name, ", ".join(parameters))

def insert_string_at_line_number(string_to_insert, line_number, original_string):
    lines = original_string.split("\n")
    #print(line_number)
    lines.insert(line_number, string_to_insert)

    return "\n".join(lines)

def save_to_file(content, filename):
    with open(filename, 'w') as file:
        file.write(content)


start = 20
#for file_directory in java_file_directories[start:start + 1]:
for file_directory in java_file_directories:
    print("started commenting" + file_directory)
    with open(file_directory, "r") as file:
        java_code = file.read()
        tree = javalang.parse.parse(java_code)

        method_counter = 0
        # Go through 4 methods. We cannot get the nodes from here, because they change position as we add the comments
        for method in tree.filter(javalang.tree.MethodDeclaration):
            tree = javalang.parse.parse(java_code)
            _, method_info = [x for x in tree.filter(javalang.tree.MethodDeclaration)][method_counter]

            has_long_method = len(method_info.body) > MIN_METHOD_SIZE_TO_DOCUMENT
            if has_long_method:
                method_name_with_parameters = get_method_name_with_parameters(method_info)

                start_line, start_column = method_info.position

                prompt = f"""Amazingly professional high-quality documentation for only the method {method_name_with_parameters} in the following format:
    /*
    * Method name
    *
    * Description: method description
    *
    * Parameters:
    * 		@param parameter name - parameter description
    *
    * Return type: return type - return type description
    *
    * Usage: method code usage
    *
    */
    
                Java code to document:
                {java_code}
                """
                automated_generated_comment = get_completion(prompt)['choices'][0]['text']
                # todo: the start_line is sometimes not good
                java_code = insert_string_at_line_number(automated_generated_comment, start_line - 1, java_code)

            method_counter += 1

        # Save javacode to file_directory

        save_to_file(java_code, file_directory)
        print("Comments saved to: " + file_directory)

repo.git.add(all=True)
repo.git.commit("-m", "Added automatic documentation")
repo.remote().push("automatic-documentation")

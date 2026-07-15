import json
import os
import re
import subprocess


# Send the list of references to the ruby script to parse
def parse_all_refs(raw):
    json_input = json.dumps(raw)
    path = os.path.dirname(os.path.abspath(__file__))

    # Run and receive output from format.rb
    process = subprocess.Popen(
        ["bundle", "exec", "ruby", path + "/format.rb"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stdout, stderr = process.communicate(input=json_input)

    # Check for errors
    if process.returncode != 0:
        print(f"Error: {stderr}")
        return None

    # Flatten and format list
    refs = json.loads(stdout)
    refs = [ref[0] for ref in refs]

    return fix_all_refs(refs)


# Fix some parsing issues
# NOTE: Would be more efficient to do all this in the Ruby script
def fix_all_refs(refs):
    return [tidy_ref(ref) for ref in refs]


# TIdy and restructure reference JSON
def tidy_ref(ref):
    new = {}

    for k, v in ref.items():
        # Puts a space after initials
        if k == "author":
            new[k] = fix_name(v)
        # Extracts year from dates that include text or non-standard formatting
        elif k == "date" and v:
            new[k] = format_year(v)
        # Sometimes references are extracted with a single '.' at the end
        elif k == "doi":
            new[k] = v[0].removesuffix(".")
        elif isinstance(v, list) and len(v) > 0:
            new[k] = v[0]
        else:
            new[k] = v

    return new


# Helper function for seperating initials, appending particles to family name and removing names that are only punctuation
def fix_name(auth):
    for a in auth:
        if "family" in a:
            a["family"] = a["family"]
        if "given" in a:
            a["given"] = re.sub(r"(?<=[A-Z]\.)(?=[A-Z])", " ", a["given"])
        if "particle" in a:
            a["family"] = a["particle"] + " " + a["family"]
        if "literal" in a:
            test = a.get("literal")
            if not test.isalpha():
                auth.remove(a)

    return auth


# Helper function for extracting year from date
def format_year(year):
    # Extracts year from list if applicable
    target = year[0] if isinstance(year, list) and year else year

    # Extracts year from date and returns as int
    if target and (match := re.search(r"\d{4}", str(target))):
        return int(match.group())

    return None

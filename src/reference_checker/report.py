import csv
import os
from collections import Counter
from datetime import datetime

from weasyprint import HTML

REF_ELEMENTS = [
    "author",
    "date",
    "title",
    "container-title",
    "volume",
    "pages",
    "issue",
    "doi",
]


# TODO: Need an option for spreadsheet/csv report
def create_report(refs, targets, scores, settings, file_name):
    threshold = 0.8
    path = get_save_path(file_name)
    # Generate normal report
    report = gen_report(refs, targets, scores, file_name, threshold)

    # Generate reports
    if settings.get("csv") is True:
        csv_report(refs, targets, scores, path)
    if settings.get("pdf") is True:
        pdf_report(report, path)
    if settings.get("html") is True:
        html_report(report, path)
    if settings.get("gui") is True:
        return report

    return


# Create report as a string
def gen_report(refs, targets, scores, file_name, threshold):

    counts = Counter()
    colours = {"real": "#009E73", "unsure": "#E69F00", "fake": "#D55E00"}

    body_text = []
    # For each reference
    for i, (ref, target, score) in enumerate(zip(refs, targets, scores)):
        colour = colours.get(score.get("verdict"))
        body_text.append(f"<h2>REFERENCE {i + 1}</h2>")

        # Check for empty references
        if not score:
            body_text.append(
                f"<h3>VERDICT</h3><p><span style='color: {colours.get('fake')}';>● <b>FAKE</b></span>, no matches found, <b>CONFIDENCE SCORE</b>: 0, <b>SOURCE</b>: None</p>"
            )
            counts["fake"] += 1
            continue

        # Get target with best score
        true_target = get_target(target, score.get("source"))
        # For every element in reference
        for ele in REF_ELEMENTS:
            # Get colour
            if score.get(ele) >= threshold:
                e_colour = colours.get("real")
            else:
                e_colour = colours.get("fake")

            # Append element name and score
            block = (
                f"<p><span style='color: {e_colour};'>●</span> <b>{ele.upper()}</b>: "
            )

            # Append elements
            if ele == "author":
                block += f"{get_names(ref.get('author'))}"
            else:
                block += f"{ref.get(ele)}"

            # Append expected element if low score
            if score.get(ele) < threshold:
                if ele == "author":
                    block += f", <b>EXPECTED</b>: {get_names(true_target.get(ele))}"
                else:
                    block += f", <b>EXPECTED</b>: {true_target.get(ele)}"

            block += "</p>"
            body_text.append(block)

        # Count verdict
        counts[score.get("verdict")] += 1

        # Append verdict info
        body_text.append("<h3>VERDICT</h3>")
        body_text.append(
            f"<p><span style='color: {colour};'><b>● {score.get('verdict').upper()}</b></span>, <b>CONFIDENCE SCORE</b>: {score.get('score'):.2f}, <b>SOURCE</b>: {score.get('source')}</p>"
        )

    body = " ".join(body_text) + "</body>"
    # Append heading info and style to report
    head = "<head><meta charset='utf-8'><style>body {font-family: sans-serif;}</style></head>"
    head += "<body><h1>REPORT</h1><p><i>NOTE: Human review of references marked as unsure or fake may be needed to confirm hallucinations</i></p>"
    head += f"<p><b>{file_name + ', ' if file_name else ''}</b><b>TOTAL REFS</b>: {len(refs)}, <b style='color: {colours.get('real')};'>REAL</b>: {counts['real']}, <b style='color: {colours.get('unsure')};'>UNSURE</b>: {counts['unsure']}, <b style='color: {colours.get('fake')};'>FAKE</b>: {counts['fake']}</p>"

    return head + body


# Write report as a pdf file
def pdf_report(report, path):
    HTML(string=report).write_pdf(path + ".pdf")


# Write report as a html file
def html_report(report, path):
    with open(path + ".html", "w") as f:
        f.write(report)


# Generate special CSV layout
def csv_report(refs, targets, scores, path):
    # Add report header
    report = [
        ["id", "score", "verdict"]
        + REF_ELEMENTS
        + ["extracted_ref", "target_ref", "source"]
    ]
    counts = Counter()

    for i, (ref, target, score) in enumerate(zip(refs, targets, scores)):
        source = score.get("source")
        verdict = score.get("verdict")

        row = [i, score.get("score"), verdict]
        row.extend((score.get(f) or 0) >= 0.8 for f in REF_ELEMENTS)
        row.extend([get_ref(ref), get_ref(get_target(target, source)), source])

        report.append(row)
        counts[verdict] += 1

    # Write files
    write_csv(f"{path}.csv", report)
    write_csv(
        f"{path}_summary.csv",
        [
            ["total", "real", "unsure", "fake"],
            [len(refs), counts["real"], counts["unsure"], counts["fake"]],
        ],
    )


def write_csv(file_path, data):
    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(data)


def get_save_path(file_name):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    # Remove extension from filename
    if file_name is not None:
        file = "_" + file_name.removesuffix(".pdf")
    else:
        file = ""

    path = os.path.join(
        os.path.expanduser("~"),
        "Documents/refreport/",
        f"{timestamp}{file}",
    )
    os.makedirs(os.path.dirname(path), exist_ok=True)

    return path


# Get the correct target that the score is associated with
def get_target(targets, source):
    return next((t for t in targets if t.get("source") == source), {})


# Neatly format every author name
def get_names(authors):
    if not authors:
        return None

    msg = ""
    for i, a in enumerate(authors):
        if "literal" in a:
            return a.get("literal")

        # End and append "et al." if applicable
        if "others" in a:
            return msg + " et al."

        # Process name normally if exists
        msg += f"{(a.get('given') or 'n/a ')} {(a.get('family') or 'n/a ')}"

        # Append comma if this is not the last author
        if i < len(authors) - 1:
            msg += ", "

    return msg


def get_ref(ref):
    author = get_names(ref.get("author")) or ""
    elements = [
        str(ref.get(f)) if ref.get(f) is not None else "" for f in REF_ELEMENTS[1:]
    ]

    return ", ".join([author] + elements)

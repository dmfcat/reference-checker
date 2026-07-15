import re

import pymupdf
import pymupdf.layout
import pymupdf4llm


def extract_all(file_path):
    return extract(file_path)


# Extract all references from PDF return list of lists
def extract(file_path):
    print("--- FILE ---")
    print(file_path)
    synonyms = ["references", "bibliography", "citations", "works cited"]

    # Open the document
    doc = pymupdf.open(file_path)
    toc = reversed(doc.get_toc())

    # Get page number where references start
    ref_page = 1
    for i, heading in enumerate(toc):
        if heading[1].lower() in synonyms:
            ref_page = heading[2]
            break

    # Convert ref section to md, intelligently accounting for columns and removing headers and footers
    md_text = pymupdf4llm.to_markdown(
        doc,
        header=False,
        footer=False,
        ignore_images=True,
        use_ocr=False,
        pages=list(range(ref_page - 1, doc.page_count)),
    )

    doc.close()

    # Remove all text that appears before and after the reference section
    ref_section = re.compile(
        r"##\s{1}\*\*(references|bibliography|citations|works cited){1}\*\*",
        flags=re.IGNORECASE,
    )

    filtered = md_text
    ref_match = ref_section.search(str(md_text))
    if ref_match:
        _, end = ref_match.span()
        filtered = md_text[end:]

        end_pattern = re.compile(r"\n##\s+")
        end_match = end_pattern.search(str(filtered))
        if end_match:
            start, _ = end_match.span()
            temp = filtered[:start]
            filtered = temp

    # Remove Unicode characters (e.g. zero width spaces and other garbage `\u200b`)
    filtered = re.sub("\u200b", "", str(filtered))
    filtered = filtered.replace(" _", " ").replace("_ ", " ")

    refs = [line for line in filtered.splitlines() if line.strip()]

    return fix_broken_refs(refs)


# Sometimes references are split in half
def fix_broken_refs(refs):
    new = []
    # Sometimes names start with a lowercase particle
    particles = (
        "de",
        "van",
        "von",
    )  # NOTE: More things could be included here

    for ref in refs:
        if ref.startswith(particles):
            new.append(ref)

        first_letter = ref[0]
        # References usually being with (an upper case name or a number or '[' or a dash '-')
        if (
            first_letter.isupper()
            or first_letter.isdigit()
            or first_letter == "["
            or first_letter == "-"
        ):
            new.append(ref)
        else:
            if new:
                new[-1] += ref
            else:
                new.append(ref)

    return new

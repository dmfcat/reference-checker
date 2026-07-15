import json
import re
import sqlite3
import unicodedata
from pathlib import Path

import numpy as np
from jellyfish import jaro_winkler_similarity as jaro_winkler
from rapidfuzz import fuzz
from stop_words import get_stop_words

import report


def verify_all(refs, targets, settings):
    res = []
    for ref, target in zip(refs, targets):
        temp = {"score": 0}
        best = {}
        for t in target:
            new = verify(ref, t)
            if new.get("score", 0.0) > temp.get("score", 0.0):
                temp["score"] = new.get("score", 0.0)
                best = new
                best["source"] = t.get("source")

        res.append(best)

    # Cache items if database enabled
    if settings.get("local") is True:
        store_all_refs(targets, res)

    return res


# Create score dictionary
def verify(ref1, ref2):
    res = {
        "author": verify_author(ref1.get("author"), ref2.get("author")),
        "date": verify_year(ref1.get("date"), ref2.get("date")),
        "title": verify_title(ref1.get("title"), ref2.get("title")),
        "volume": verify_generic(ref1.get("volume"), ref2.get("volume")),
        "pages": verify_pages(ref1.get("pages"), ref2.get("pages")),
        "doi": verify_generic(ref1.get("doi"), ref2.get("doi")),
        "container-title": verify_journal(
            ref1.get("container-title"),
            ref2.get("container-title"),
            ref2.get("alt-container-title"),
        ),
        "issue": verify_generic(ref1.get("issue"), ref2.get("issue")),
    }

    # Append score and verdict
    res["score"] = float(calculate_score(res, ref2))
    res["verdict"] = calculate_verdict(res.get("score", 0))

    return res


def verify_author(auth1, auth2):
    result = check_missing(auth1, auth2)
    if result is not None:
        return result

    names, target_names = tokenise_names(auth1), tokenise_names(auth2)
    is_et_al = any("others" in a for a in auth1)

    f_weight, g_weight = 0.7, 0.3
    threshold = 0.9
    total_score = 0
    matches = 0

    # Iterate over all extracted names
    for fname, gnames in names:
        name_score = 0
        # Iterate over all target names
        for target_fname, target_gnames in target_names:
            # Skip if no name found
            if not target_fname or not target_gnames:
                continue

            # Check if family name matches
            f_score = jaro_winkler(fname, target_fname)
            if f_score >= threshold:
                # Check if given names match
                g_score = compare_given_names(gnames, target_gnames, threshold)
                # Calculate and record score if a match is found
                if g_score is not None:
                    name_score = max(
                        name_score, (f_score * f_weight) + (g_score * g_weight)
                    )

        if name_score > 0:
            total_score += name_score
            matches += 1

    # Return average score
    if is_et_al:
        total_refs = max(matches, 1)
    else:
        total_refs = len(target_names) if target_names else 1

    return min(total_score / total_refs, 1.0)


def compare_given_names(names, targets, threshold):
    if not names or not targets:
        return 0.0

    scores = []
    # Iterate over every given name
    for giv, tar_giv in zip(names, targets):
        # Check for initials
        if len(giv) == 1 or len(tar_giv) == 1:
            res = 0.9 if giv[0] == tar_giv[0] else 0.0
        else:
            res = jaro_winkler(giv, tar_giv)

        scores.append(res)

    # Return average only if match
    avg = sum(scores) / len(scores)
    return avg if avg >= threshold else None


def verify_journal(jour1, jour2, alt_jour):
    result = check_missing(jour1, jour2)
    if result is not None:
        return result

    threshold = 0.7

    # Filter stop words and clean both journal names
    jour = remove_stop_words(jour1)
    target_jour = remove_stop_words(jour2)

    # Filter stop words and clean alt journal names
    seen = {target_jour}
    filt_alt_jour = []
    for j in alt_jour or []:
        temp = remove_stop_words(j)
        # Add to list if doesn't already exist
        if temp and temp not in seen:
            filt_alt_jour.append(temp)
            seen.add(temp)

    # Fuzzy match on journal names and abbreviations
    res = [(fuzz.ratio(jour, target_jour))]
    for j in filt_alt_jour:
        res.append(fuzz.ratio(jour, j))

    score = max(res) / 100

    return score if score > threshold else 0


def remove_stop_words(jour):
    return " ".join(
        word for word in clean(jour).split() if word not in get_stop_words("en")
    )


def verify_title(title1, title2):
    threshold = 0.7
    result = check_missing(title1, title2)
    if result is not None:
        return result

    score = fuzz.ratio(clean(title1), clean(title2)) / 100

    return score if score > threshold else 0


# Compare year (returns True if year within 1)
def verify_year(year1, year2):
    result = check_missing(year1, year2)
    if result is not None:
        return result

    return int(abs(year1 - year2) <= 1)


# Compare pages
def verify_pages(page1, page2):
    res = check_missing(page1, page2)
    if res is not None:
        return res

    return int(clean_pages(page1) == clean_pages(page2))


# Clean pages, return only the indivual numbers
def clean_pages(p):
    nums = re.findall(r"\d+", p)
    # Expand cases like 1234-35 to 1234-1235, if the second number is greater than the first, it gets appended to the end of the first
    if len(nums) > 1 and len(nums[1]) < len(nums[0]):
        nums[1] = nums[0][: -len(nums[1])] + nums[1]
    return set(nums)


# Compare other fields (DOI, issue, volume, etc...)
def verify_generic(item1, item2):
    result = check_missing(item1, item2)
    if result is not None:
        return result

    return int(clean(item1.replace(" ", "")) == clean(item2.replace(" ", "")))


# Check if any items are missing and return associated value
def check_missing(extracted, target):
    # None in both fields (this is technically a match)
    if not extracted and not target:
        return 1

    # None in extracted ref (info not included in ref that does exist)
    if not extracted:
        return 0.2

    # None in target ref (Info included in ref that doesn't exist)
    if not target:
        return 0

    return None


# Apply weights and calculated Jaccard similarity
def calculate_score(scores, target):
    # Weights
    weights = {
        "author": 4.0,
        "date": 2.5,
        "title": 5.0,
        "container": 5.0,
        "doi": 0.5,
        "volume": 0.5,
        "page": 0.5,
        "issue": 0.5,
    }

    e_vec = []
    t_vec = []

    # Apply weights to vectors
    for k, w in weights.items():
        e_vec.append(scores.get(k, 0) * w)
        t_vec.append((1 if k in target else 0) * w)

    e_vec = np.array(e_vec)
    t_vec = np.array(t_vec)

    # Weighted Jaccard similarity
    intersection = np.sum(np.minimum(e_vec, t_vec))
    union = np.sum(np.maximum(e_vec, t_vec))
    return intersection / union if union != 0 else 0


# Return a verdict depending on the score
def calculate_verdict(score):
    real_thresh, fake_thresh = 0.80, 0.60
    if score >= real_thresh:
        return "real"
    elif score >= fake_thresh:
        return "unsure"

    return "fake"


# Remove capitalisation, accents, symbols/punctuation and excess whitespace from a string
def clean(s):
    # Return early if string is empty or None
    if not s:
        return s

    s = s.lower()
    s = unicodedata.normalize("NFD", s)
    s = re.sub(r"[^a-zA-Z0-9 ]", "", s)
    s = " ".join(s.split())
    return s


# Reorganise, clean and tokenise all names associated with an author
def tokenise_names(auth):
    names = []
    for a in auth:
        if "others" not in a:
            # Handle hyphenated given names
            given = (a.get("given") or "").replace("-", " ")
            names.append(
                (
                    clean(a.get("family", "")),
                    [clean(name) for name in given.split()],
                )
            )

    return names


# Add all refs to DB if applicable
def store_all_refs(refs, scores):
    # Open DB
    conn = sqlite3.connect((Path(__file__).parent / "../data/localpapers.db").resolve())
    cursor = conn.cursor()

    # Loop through all refs
    for ref, score in zip(refs, scores):
        best_ref = report.get_target(ref, score.get("source"))
        doi = best_ref.get("doi")
        # Skip ref if no DOI or ref already from the db
        if not doi or score.get("source") == "Local Database":
            continue

        # Check if DOI exists in database, insert if not
        cursor.execute("SELECT 1 FROM papers WHERE doi = ? LIMIT 1", (doi,))
        if not cursor.fetchone():
            # Extract elements
            author = json.dumps(best_ref.get("author", ""))
            date = best_ref.get("date", "")
            title = best_ref.get("title", "")
            volume = best_ref.get("volume", "")
            pages = best_ref.get("pages", "")
            doi = best_ref.get("doi")
            container_title = best_ref.get("container-title", "")
            alt_container_title = json.dumps(best_ref.get("alt-container-title", ""))
            issue = best_ref.get("issue", "")

            # Insert elements
            cursor.execute(
                "INSERT INTO papers (author, date, title, volume, pages, doi, container_title, alt_container_title, issue) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    author,
                    date,
                    title,
                    volume,
                    pages,
                    doi,
                    container_title,
                    alt_container_title,
                    issue,
                ),
            )

    conn.commit()
    conn.close()

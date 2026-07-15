import json
import os
import sqlite3
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
from habanero import Crossref


# Append author family names into a string
def get_authors(authors):
    res = []
    for a in authors:
        res.append(a.get("family") or "")

    return " ".join(res)


# Set time for sleep based off API used
def get_sleep_time(settings):
    if settings.get("sem") or settings.get("cross"):
        return 1

    return 0


def query_all(refs, settings, callback):
    # Get sleep time for staggering APIs
    sleep_time = get_sleep_time(settings)

    # Setup database and web APIs
    conn = sskey = cr = None
    load_dotenv(verbose=True)
    if settings.get("local") is True:
        db_path = (Path(__file__).parent / "../data/localpapers.db").resolve()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        check_db_exists(cursor)
        conn.commit()

    if settings.get("sem") is True:
        sskey = os.getenv("API_KEY")
        if not sskey:
            print("ERROR: No API key for Semantic Scholar, add API_KEY to .env")
            settings["sem"] = False

    if settings.get("cross") is True:
        email = os.getenv("EMAIL")
        if not email:
            print("ERROR: No e-mail for Crossref, add EMAIL to .env")
            cr = Crossref()
        else:
            cr = Crossref(mailto=email)

        cr.timeout = 30

    targets = []
    total = len(refs)

    for i, ref in enumerate(refs):
        targets.append(query(ref, settings, conn, sskey, cr))

        # Update progress bar
        progress_value = int(((i + 1) / total) * 90) + 5
        callback(progress_value)

        # Sleep as long as not on last ref
        if total - 1 != i:
            time.sleep(sleep_time)

    # Close database
    if settings.get("local"):
        conn.close()

    return targets


def query(ref, settings, conn, sskey, cr):
    # Get query info, then query APIs
    title = ref.get("title", "")
    authors = get_authors(ref.get("author") or [])
    doi = ref.get("doi", "")

    targets = []

    # Local search
    if settings.get("local") is True and conn:
        re = db_search(title, authors, doi, conn)
        targets.append(re)

    # Semantic Scholar search
    if settings.get("sem") is True and sskey:
        targets.append(ss_search(title, authors, sskey))

    # Crossref search
    if settings.get("cross") is True and cr:
        targets.append(cr_search(title, authors, doi, cr))

    # Return targets or empty dict if none
    return targets if targets else [{}]


# Search local db
def db_search(title, authors, doi, conn):
    cursor = conn.cursor()

    # Query DOI
    if doi:
        cursor.execute(
            "SELECT * FROM papers WHERE doi = ? COLLATE NOCASE LIMIT 1", (doi,)
        )
        result = cursor.fetchone()
        if result:
            return parse_db(result)

    t_tokens = [f"%{t}%" for t in (title or "").split() if t]
    a_tokens = [f"%{a}%" for a in (authors or "").split() if a]

    t_clause = " AND ".join(["title LIKE ?"] * len(t_tokens))
    a_clause = " AND ".join(["author LIKE ?"] * len(a_tokens))

    t_params = [f"%{t}%" for t in t_tokens]
    a_params = [f"%{a}%" for a in a_tokens]

    # Query author + title
    if t_tokens and a_tokens:
        query = f"SELECT * FROM papers WHERE {t_clause} AND {a_clause} LIMIT 1"
        cursor.execute(query, t_params + a_params)
        result = cursor.fetchone()
        if result:
            return parse_db(result)

    # Query just title
    if t_tokens:
        query = f"SELECT * FROM papers WHERE {t_clause} LIMIT 1"
        cursor.execute(query, t_params)
        result = cursor.fetchone()
        if result:
            return parse_db(result)

    # Return empty dict if no match
    return {}


# Convert results from db queries back to json
def parse_db(res):
    return {
        "author": json.loads(res[1]) if isinstance(res[1], str) else res[1],
        "date": res[2],
        "title": res[3],
        "volume": res[4],
        "pages": res[5],
        "doi": res[6],
        "container-title": res[7],
        "alt-container-title": json.loads(res[8])
        if isinstance(res[8], str)
        else res[8],
        "issue": res[9],
        "source": "Local Database",
    }


# Search Semantic Scholar, return as soon as match found (NOTE: returns only sufficiently close matches)
def ss_search(title, authors, sskey):
    url = "http://api.semanticscholar.org/graph/v1/paper/search/match"
    headers = {"x-api-key": sskey}

    # Query using title and authors
    query_params = {
        "query": f"{title} {authors}".strip(),
        "fields": "title,year,authors,publicationVenue,externalIds,journal",
    }
    res = requests.get(url, params=query_params, headers=headers).json()
    if res.get("data"):
        return filter_ss(res.get("data")[0])

    # Fallback, query with just title
    time.sleep(1)
    query_params = {
        "query": f"{title}".strip(),
        "fields": "title,year,authors,publicationVenue,externalIds,journal",
    }
    res = requests.get(url, params=query_params, headers=headers).json()
    if res.get("data"):
        return filter_ss(res.get("data")[0])

    # Return empty dict if nothing found
    return {}


# Filter metadata from Semantic Scholar
def filter_ss(metadata):
    return {
        "author": [
            split_name(auth.get("name")) for auth in metadata.get("authors", [])
        ],
        "date": metadata.get("year"),
        "title": metadata.get("title"),
        "volume": (metadata.get("journal") or {}).get("volume"),
        "pages": (metadata.get("journal") or {}).get("pages"),
        "doi": (metadata.get("externalIds") or {}).get("DOI"),
        "container-title": (metadata.get("publicationVenue") or {}).get("name"),
        "alt-container-title": (metadata.get("publicationVenue") or {}).get(
            "alternate_names"
        ),
        "issue": metadata.get("issue"),
        "source": "Semantic Scholar",
    }


# Split given and family names, semantic scholar always gives given names followed by family name
def split_name(name):
    parts = (name or "").split()
    if not parts:
        return {"given": None, "family": None}

    family = parts[-1]
    # All names apart from family are added to given name, if only one name assume it's family
    if len(parts) > 1:
        given = " ".join(parts[:-1])
    else:
        given = None

    return {"family": family, "given": given}


# Search Crossref, returns as soon as match found
def cr_search(title, authors, doi, cr):
    # Query using DOI is exists
    if doi:
        if res := cr_doi_search(doi, cr):
            return res
        else:
            time.sleep(1)

    # Query using title and authors
    res = cr.works(
        query=f"{title} {authors}".strip(),
        warn=True,
        limit=1,
        select="title,author,container-title,short-container-title,published-print,page,issue,volume,DOI",
    )

    if res.get("message", {}).get("items"):
        return filter_cr(res.get("message", {}).get("items")[0])

    # Query using just title
    time.sleep(1)
    res = cr.works(
        query=title,
        warn=True,
        limit=1,
        select="title,author,container-title,short-container-title,published-print,page,issue,volume,DOI",
    )
    if res.get("message", {}).get("items"):
        return filter_cr(res.get("message", {}).get("items")[0])

    # Return empty dict if nothing found
    return {}


# Search crossref using doi, returns only doi match
def cr_doi_search(doi, cr):
    res = cr.works(ids=doi, warn=True)
    return filter_cr(res.get("message")) if res and "message" in res else {}


# Filter metadata from Crossref
def filter_cr(metadata):
    return {
        "author": [
            {"family": auth.get("family"), "given": auth.get("given")}
            for auth in metadata.get("author", [])
        ],
        "date": get_cr_year(metadata),
        "title": metadata.get("title")[0] if metadata.get("title") else None,
        "volume": metadata.get("volume"),
        "pages": metadata.get("page"),
        "doi": metadata.get("DOI"),
        "container-title": metadata.get("container-title")[0]
        if metadata.get("container-title")
        else None,
        "alt-container-title": metadata.get("short-container-title"),
        "issue": metadata.get("issue"),
        "source": "Crossref",
    }


# Crossref date can be stored in multiple places
def get_cr_year(metadata):
    locations = ["published-print", "published-online", "issued"]

    for loc in locations:
        year = metadata.get(loc, {}).get("date-parts")
        if year and year[0]:
            return year[0][0]

    return None


# Create db if it doesn't exist
def check_db_exists(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS "papers" (
    	"id"	INTEGER,
    	"author"	TEXT,
    	"date"	INTEGER,
    	"title"	TEXT,
    	"volume"	TEXT,
    	"pages"	TEXT,
    	"doi"	TEXT,
    	"container_title"	TEXT,
    	"alt_container_title"	TEXT,
    	"issue"	TEXT,
    	PRIMARY KEY("id")
        )
    """)

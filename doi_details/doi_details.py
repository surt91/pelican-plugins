# -*- coding: utf-8 -*-
"""
DOI details Plugin for Pelican
==============================

This plugin adds details for articles referenced by a DOI
"""
from time import sleep
from xml.etree import ElementTree

import requests

from pelican import signals


def doi2json(doi):
    # -LH "Accept: application/vnd.citationstyles.csl+json" https://doi.org/10.1103/PhysRevE.96.062101
    url = 'https://doi.org/{}'.format(doi)
    r = requests.get(url, headers={'Accept': 'application/vnd.citationstyles.csl+json'})

    try:
        json = r.json()
    except:
        print("error for doi", doi, ":", r)
        json = {}

    return json


def arxiv2json(arxiv):
    # we should obey arxives rate limits: 4 requests per second
    # https://arxiv.org/help/api/tou
    sleep(0.25)

    # https://export.arxiv.org/api/query?id_list=1512.08554
    url = 'https://export.arxiv.org/api/query?id_list={}'.format(arxiv)

    r = requests.get(url)
    root = ElementTree.fromstring(r.content)

    for child in root:
        if "entry" in child.tag:
            entry = root.find(child.tag)

    for child in entry:
        if "title" in child.tag:
            title = entry.find(child.tag).text
        if "published" in child.tag:
            year = entry.find(child.tag).text.split("-")[0]
        if "author" in child.tag:
            authors_tag = child.tag
        if "primary_category" in child.tag:
            prime_cat = entry.find(child.tag).attrib["term"]

    authors = []
    for author in entry.findall(authors_tag):
        for child in author:
            authors.append(author.find(child.tag).text)

    authors = ", ".join(authors)

    long = "arxiv:{} [{}]".format(arxiv, prime_cat)

    data = {
        "title": title,
        "year": year,
        "authors": authors,
        "long": long,
    }

    return data


def details(generator):
    for article in generator.articles:
        try:
            doi = article.doi
        except AttributeError:
            continue

        json = doi2json(doi)

        article.doi_title = json["title"]
        article.doi_journal = json["container-title"]
        article.doi_year = json["published-online"]["date-parts"][0][0]
        article.doi_authors = ", ".join(" ".join([author["given"], author["family"]]) for author in json["author"])
        article.doi_volume = json["volume"]
        try:
            article.doi_number = json["article-number"]
        except KeyError:
            article.doi_number = json["page"]
        article.doi_cites = json["is-referenced-by-count"]


def publication_list(peli):
    try:
        pubs = peli.settings["PUBLICATIONS"]
    except KeyError:
        return

    peli.settings["publication_details"] = []

    for pub in pubs:
        try:
            doi = pub["doi"]
        except AttributeError:
            continue

        json = doi2json(doi)

        try:
            doi_number = json["article-number"]
        except KeyError:
            doi_number = json["page"]

        arxiv = pub.get("arxiv", None)
        if arxiv:
            arxiv_data = arxiv2json(arxiv)
            arxiv_long = arxiv_data["long"]
        else:
            arxiv_long = None

        pdf = pub.get("pdf", None)

        pub_info = {
            "doi": doi,
            "arxiv": arxiv,
            "comment": pub.get("comment", None),
            "related": pub.get("related", None),
            "supplementary": pub.get("supplementary", None),
            "arxiv_long": arxiv_long,
            "pdf": pdf,
            "title": json["title"],
            "journal": json["container-title"],
            "year": json["published-online"]["date-parts"][0][0],
            "authors": ", ".join(" ".join([author["given"], author["family"]]) for author in json["author"]),
            "volume": json["volume"],
            "number": doi_number,
            "num_citations": json["is-referenced-by-count"],
        }

        peli.settings["publication_details"].append(pub_info)


def preprint_list(peli):
    try:
        pubs = peli.settings["PREPRINTS"]
    except KeyError:
        return

    peli.settings["preprint_details"] = []

    for pub in pubs:
        try:
            arxiv = pub["arxiv"]
        except AttributeError:
            continue

        arxiv_data = arxiv2json(arxiv)
        arxiv_long = arxiv_data["long"]

        pdf = pub.get("pdf", None)

        pre_info = {
            "arxiv": arxiv,
            "arxiv_long": arxiv_long,
            "pdf": pdf,
            "title": arxiv_data["title"],
            "year": arxiv_data["year"],
            "authors": arxiv_data["authors"],
            "related": pub.get("related", None),
            "supplementary": pub.get("supplementary", None),
        }

        peli.settings["preprint_details"].append(pre_info)


def register():
    signals.initialized.connect(publication_list)
    signals.initialized.connect(preprint_list)
    signals.article_generator_finalized.connect(details)

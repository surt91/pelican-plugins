# -*- coding: utf-8 -*-
"""
DOI details Plugin for Pelican
==============================

This plugin adds details for articles referenced by a DOI
"""

import requests

from pelican import signals


def details(generator):
    for article in generator.articles:
        try:
            doi = article.doi
        except AttributeError:
            continue

        # -LH "Accept: application/vnd.citationstyles.csl+json" https://doi.org/10.1103/PhysRevE.96.062101
        url = 'https://doi.org/{}'.format(doi)
        r = requests.get(url, headers={'Accept': 'application/vnd.citationstyles.csl+json'})
        json = r.json()

        print(json)

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


def register():
    signals.article_generator_finalized.connect(details)

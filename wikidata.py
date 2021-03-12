import requests
import roman
import re
from flask import current_app, session
from requests_oauthlib import OAuth1Session


def query_wikidata(query):
    url = "https://query.wikidata.org/sparql"
    params = {
        "query": query,
        "format": "json"
    }
    result = requests.get(url=url, params=params, headers={'User-agent': 'WikiMI QAM 1.0'})
    data = result.json()
    return data


def query_by_type(query, lang="pt-br"):
    new_query = query.replace("LANGUAGE", lang)
    data = query_wikidata(new_query)
    result = data["results"]["bindings"]

    images = []
    for image in result:
        images.append({
            "qid": image["item_qid"]["value"],
            "label": image["item_label"]["value"],
            "imagem": image["imagem"]["value"],
            "category": image["category"]["value"] if 'category' in image else ''
        })

    return images


def query_metadata_of_work(query, lang="pt-br"):
    data = query_wikidata(query)
    if "results" in data and "bindings" in data["results"]:
        result = data["results"]["bindings"][0]
        format_dates_in_result(result, lang)
        get_values_lists(result)
        if "obra" in result and len(result["obra"]) > 0:
            result["obra_qid"] = [result["obra"][0].replace("http://www.wikidata.org/entity/", "")]
        if "category" in result and len(result["obra"]) > 0:
            result["category"] = result["category"][0]
    if not result or result == [{}]:
        result = ""
    return result


def query_brands_metadata(query, qid):
    data = query_wikidata(query)
    result = data["results"]["bindings"]
    for brand_entity in result:
        get_values_lists(brand_entity, sep=";%;")
        if not brand_entity:
            return None
        if 'marca_stat_id' in brand_entity:
            brand_entity['marca_stat_id'][0] = "https://www.wikidata.org/wiki/"+qid+"#"+brand_entity['marca_stat_id'][0].replace('-', '$', 1)
        else:
            brand_entity['marca_stat_id'] = ['']
        if "marca_descr" not in brand_entity:
            brand_entity["marca_descr"] = ""
        if "marca_label" not in brand_entity:
            brand_entity["marca_label"] = ""
        if "marca_qid" not in brand_entity:
            brand_entity["marca_qid"] = ""
    return result


def api_category_members(category):
    url = 'https://commons.wikimedia.org/w/api.php'
    params = {
        'action': 'query',
        'generator': 'categorymembers',
        'gcmtype': 'file',
        'gcmtitle': category,
        'gcmlimit': 'max',
        'format': 'json'
    }
    result = requests.get(url=url, params=params, headers={'User-agent': 'WikiMI CQREV 1.0'})
    data = result.json()

    category_images = []
    if "query" in data and "pages" in data["query"]:
        for page in data["query"]["pages"]:
            category_images.append(data["query"]["pages"][page]["title"][5:])

    return category_images


def format_dates_in_result(result, lang="pt-br"):
    if "data" in result:
        datas = result["data"]["value"].split(";")
        novas_datas = []
        for data in datas:
            novas_datas.append(format_dates(data, lang))
        result["data"]["value"] = ";".join(novas_datas)


def format_dates(time, lang="pt-br"):
    year, month, day, precision = list(map(int, re.findall(r'\d+', time)))
    if precision == 7:
        if lang == "en":
            date = "%dth century" % (int(year/100)+1)
        else:
            if year % 100 == 0:
                date = "Século %s" % (roman.toRoman(math.floor(year/100)))
            else:
                date = "Século %s" % (roman.toRoman(math.floor(year / 100) + 1))
    elif precision == 8:
        if lang == "en":
            date = "%ds" % (int(year/10)*10)
        else:
            date = "Década de %d" % (int(year/10)*10)
    elif precision == 9:
        date = "%d" % year
    elif precision == 10:
        date = "%d/%d" % (month, year)
    elif precision == 11:
        if lang == "en":
            date = "%d/%d/%d" % (month, day, year)
        else:
            date = "%d/%d/%d" % (day, month, year)
    else:
        date = ""
    return date


def get_values_lists(result, sep=";"):
    for metadata_key, metadata_dict in result.items():
        result[metadata_key] = list(filter(None, metadata_dict["value"].split(sep)))


def api_post_request(params):
    app = current_app
    url = 'https://www.wikidata.org/w/api.php'
    client_key = app.config['CONSUMER_KEY']
    client_secret = app.config['CONSUMER_SECRET']
    oauth = OAuth1Session(client_key,
                          client_secret=client_secret,
                          resource_owner_key=session['owner_key'],
                          resource_owner_secret=session['owner_secret'])
    return oauth.post(url, data=params, timeout=4)


def post_search_entity(term, lang="pt-br"):
    url = 'https://www.wikidata.org/w/api.php'
    params = {
        'action': 'wbsearchentities',
        'search': term,
        'language': lang,
        'format': 'json',
        'limit': 50,
        'uselang': lang,
    }
    result = requests.get(url=url, params=params, headers={'User-agent': 'WikiMI QaM 1.0'})
    data = result.json()

    return data


def filter_by_instancia(qids, lang="pt-br"):
    if lang == "pt-br" or lang == "pt":
        lang = "pt-br,pt"
    data = query_wikidata("SELECT DISTINCT ?item_qid ?item_label ?item_descr WHERE { SERVICE wikibase:label {bd:serviceParam wikibase:language '"+lang+"'. ?item rdfs:label ?item_label. ?item schema:description ?item_descr.} VALUES ?item {"+qids+"} VALUES ?instancia {wd:Q431289 wd:Q1412386 wd:Q167270 wd:Q5} ?item wdt:P31 ?instancia. BIND(SUBSTR(STR(?item),32) AS ?item_qid) }")
    results = data["results"]["bindings"]
    query = []
    for item in results:
        if "item_qid" in item:
            qid = item["item_qid"]["value"]
        else:
            qid = ""
        if "item_label" in item:
            label = item["item_label"]["value"]
        else:
            label = ""
        if "item_descr" in item:
            descr = item["item_descr"]["value"]
        else:
            descr = ""
        query.append({"qid": qid,
                      "label": label,
                      "descr": descr})
    return query


def query_quantidade(query):
    data = query_wikidata(query)
    try:
        valor = int(data["results"]["bindings"][0]["number_works"]["value"])
    except:
        valor = 0
    return valor

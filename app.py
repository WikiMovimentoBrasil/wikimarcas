import yaml
import os
import json
import requests
from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from flask_babel import Babel
from wikidata import query_by_type, query_metadata_of_work, query_brands_metadata, post_search_entity, filter_by_tesauros, api_category_members, api_post_request
from oauth_wikidata import get_username, get_token
from requests_oauthlib import OAuth1Session

__dir__ = os.path.dirname(__file__)
app = Flask(__name__)
app.config.update(yaml.safe_load(open(os.path.join(__dir__, 'config.yaml'))))

BABEL = Babel(app)


@app.route('/login')
def login():
    next_page = request.args.get('next')
    if next_page:
        session['after_login'] = next_page

    client_key = app.config['CONSUMER_KEY']
    client_secret = app.config['CONSUMER_SECRET']
    base_url = 'https://www.wikidata.org/w/index.php'
    request_token_url = base_url + '?title=Special%3aOAuth%2finitiate'

    oauth = OAuth1Session(client_key,
                          client_secret=client_secret,
                          callback_uri='oob')
    fetch_response = oauth.fetch_request_token(request_token_url)

    session['owner_key'] = fetch_response.get('oauth_token')
    session['owner_secret'] = fetch_response.get('oauth_token_secret')

    base_authorization_url = 'https://www.wikidata.org/wiki/Special:OAuth/authorize'
    authorization_url = oauth.authorization_url(base_authorization_url,
                                                oauth_consumer_key=client_key)
    return redirect(authorization_url)


@app.route("/oauth-callback", methods=["GET"])
def oauth_callback():
    base_url = 'https://www.wikidata.org/w/index.php'
    client_key = app.config['CONSUMER_KEY']
    client_secret = app.config['CONSUMER_SECRET']

    oauth = OAuth1Session(client_key,
                          client_secret=client_secret,
                          resource_owner_key=session['owner_key'],
                          resource_owner_secret=session['owner_secret'])

    oauth_response = oauth.parse_authorization_response(request.url)
    verifier = oauth_response.get('oauth_verifier')
    access_token_url = base_url + '?title=Special%3aOAuth%2ftoken'
    oauth = OAuth1Session(client_key,
                          client_secret=client_secret,
                          resource_owner_key=session['owner_key'],
                          resource_owner_secret=session['owner_secret'],
                          verifier=verifier)

    oauth_tokens = oauth.fetch_access_token(access_token_url)
    session['owner_key'] = oauth_tokens.get('oauth_token')
    session['owner_secret'] = oauth_tokens.get('oauth_token_secret')
    next_page = session.get('after_login')

    return redirect(next_page)

# Função para pegar a língua de preferência do usuário
@BABEL.localeselector
def get_locale():
    if request.args.get('lang'):
        session['lang'] = request.args.get('lang')
    return session.get('lang', 'pt')


# Função para mudar a língua de exibição do conteúdo
@app.route('/set_locale')
def set_locale():
    next_page = request.args.get('return_to')
    lang = request.args.get('lang')

    session["lang"] = lang
    return redirect(next_page)


def pt_to_ptbr(lang):
    if lang == "pt" or lang == "pt-br":
        return "pt-br,pt"
    else:
        return lang


# Página inicial
@app.route('/')
@app.route('/home')
@app.route('/inicio')
def inicio():
    username = get_username()
    lang = pt_to_ptbr(get_locale())
    return render_template('inicio.html',
                           username=username,
                           lang=lang)


@app.route('/about')
@app.route('/sobre')
def sobre():
    username = get_username()
    lang = pt_to_ptbr(get_locale())
    return render_template('sobre.html',
                           username=username,
                           lang=lang)


@app.route('/tutorial')
def tutorial():
    username = get_username()
    lang = pt_to_ptbr(get_locale())
    return render_template('example.html',
                           username=username,
                           lang=lang)


@app.route('/colecao/<type>')
def objeto(type):
    username = get_username()
    lang = pt_to_ptbr(get_locale())
    with open(os.path.join(app.static_folder, 'queries.json'), encoding="utf-8") as category_queries:
        all_queries = json.load(category_queries)

    try:
        selected_query = all_queries[type]["query"]
        selection = query_by_type(selected_query)
        if lang == "en":
            descriptor = all_queries[type]["descriptor"]["en"]
        else:
            descriptor = all_queries[type]["descriptor"]["pt-br"]

        return render_template("colecao.html",
                               collection=selection,
                               username=username,
                               lang=lang,
                               descriptor=descriptor)
    except:
        return redirect(url_for('inicio'))


# Página de visualização da obra e inserção de qualificadores
@app.route('/item/<qid>')
def item(qid):
    username = get_username()
    lang = pt_to_ptbr(get_locale())

    with open(os.path.join(app.static_folder, 'queries.json')) as category_queries:
        all_queries = json.load(category_queries)

    metadata_query = all_queries["Metadados"]["query"].replace("LANGUAGE", lang).replace("QIDDAOBRA", qid)
    brands_query = all_queries["Marcas"]["query"].replace("LANGUAGE", lang).replace("QIDDAOBRA", qid)
    work_metadata = query_metadata_of_work(metadata_query, lang=lang)
    work_depicts = query_brands_metadata(brands_query, qid)

    if "category" in work_metadata:
        category_images = api_category_members(work_metadata["category"])
    else:
        category_images = []

    return render_template('item.html',
                           metadata=work_metadata,
                           depicts_metadata=work_depicts,
                           category_images=category_images,
                           username=username,
                           lang=lang,
                           qid=qid)

##############################################################
# CONSULTAS E REQUISIÇÕES
##############################################################

# Requisição de adicionar qualificador à item retratado
@app.route('/add_stat', methods=['GET', 'POST'])
def add_statement():
    if request.method == 'POST':
        data = request.get_json()
        qid = data['id']
        pid = data['tipo']  # Tipo de qualificador
        snaktype = 'value'
        token = get_token()

        params = {
            "action": "wbcreateclaim",
            "format": "json",
            "entity": qid,
            "property": pid,
            "snaktype": snaktype,
            "token": token
        }

        if pid == 'P1684':
            claim = data['claim']
            params["value"] = "{\"text\":\"" + str(claim) + "\",\"language\":" + get_locale() + "}",
        elif pid == 'unknownvalue':
            params["snaktype"] = 'somevalue'
        elif pid == 'P1716':
            claim = data['claim'].replace("Q", "")
            params["value"] = "{\"entity-type\":\"item\",\"numeric-id\":" + str(claim) + "}"
        else:
            return jsonify("204")

        results = api_post_request(params)

        if pid == 'P1684':
            stat_id = get_claim(qid, pid, claim)
            new_params = {
                "action": "wbsetqualifier",
                "format": "json",
                "claim": stat_id,
                "property": 'P3831',
                "value": "{\"entity-type\":\"item\",\"numeric-id\":431289}",
                "snaktype": "value",
                "token": token
            }

            api_post_request(new_params)

        return jsonify(results.status_code)
    else:
        return jsonify("204")


def get_claim(qid, pid, val):
    params = {
        "action": "wbgetclaims",
        "format": "json",
        "entity": qid,
        "property": pid
    }

    results = requests.get("https://www.wikidata.org/w/api.php", params=params).json()
    if "claims" in results and 'P1684' in results['claims']:
        for p1684_val in results['claims']['P1684']:
            if 'mainsnak' in p1684_val and 'datavalue' in p1684_val['mainsnak'] and p1684_val['mainsnak']['datavalue']['value']['text'] == val:
                return p1684_val['id']
    return ''


# Requisição para procurar entidades e filtrá-las pelos tesauros
@app.route('/search', methods=['GET', 'POST'])
def search_entity():
    if request.method == "POST":
        data = request.get_json()
        term = data['term']
        lang = get_locale()

        data = post_search_entity(term, lang)

        items = []
        for item in data["search"]:
            items.append(item["id"])

        if items and items.__len__() > 0:
            return jsonify(items), 200
        else:
            return jsonify([]), 204


if __name__ == '__main__':
    app.run()
    # https://w.wiki/32TE
    # https://w.wiki/32bR

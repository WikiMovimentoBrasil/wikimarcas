import yaml
import os
import json
import requests
from flask import Flask, render_template, request, redirect, session, url_for, jsonify, g
from flask_babel import Babel, gettext
from wikidata import query_by_type, query_metadata_of_work, query_brands_metadata, post_search_entity,\
    api_category_members, api_post_request, filter_by_instancia, query_quantidade, query_next_qid
from oauth_wikidata import get_username, get_token
from requests_oauthlib import OAuth1Session
from datetime import datetime

__dir__ = os.path.dirname(__file__)
app = Flask(__name__)
app.config.update(yaml.safe_load(open(os.path.join(__dir__, 'config.yaml'))))

BABEL = Babel(app)


@app.before_request
def init_profile():
    g.profiling = []


@app.before_request
def global_user():
    g.user = get_username()


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
    redirected = redirect(next_page)
    redirected.delete_cookie('session', '/item')
    return redirected


def pt_to_ptbr(lang):
    if lang == "pt" or lang == "pt-br":
        return "pt-br"
    else:
        return lang


##############################################################
# PÁGINAS
##############################################################
# Página de erro
@app.errorhandler(400)
@app.errorhandler(401)
@app.errorhandler(403)
@app.errorhandler(404)
@app.errorhandler(405)
@app.errorhandler(406)
@app.errorhandler(408)
@app.errorhandler(409)
@app.errorhandler(410)
@app.errorhandler(411)
@app.errorhandler(412)
@app.errorhandler(413)
@app.errorhandler(414)
@app.errorhandler(415)
@app.errorhandler(416)
@app.errorhandler(417)
@app.errorhandler(418)
@app.errorhandler(422)
@app.errorhandler(423)
@app.errorhandler(424)
@app.errorhandler(429)
@app.errorhandler(500)
@app.errorhandler(501)
@app.errorhandler(502)
@app.errorhandler(503)
@app.errorhandler(504)
@app.errorhandler(505)
def page_not_found(e):
    return render_template('error.html')

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
    with open(os.path.join(app.static_folder, 'queries.json'), encoding="utf-8") as category_queries:
        all_queries = json.load(category_queries)

    quantidade = query_quantidade(all_queries["Quantidade_de_objetos"]["query"])
    return render_template('sobre.html',
                           username=username,
                           lang=get_locale(),
                           number_works=quantidade)


@app.route('/tutorial')
def tutorial():
    username = get_username()
    lang = pt_to_ptbr(get_locale())
    return render_template('tutorial.html',
                           username=username,
                           lang=lang)


@app.route('/apps')
def apps():
    username = get_username()
    lang = pt_to_ptbr(get_locale())
    return render_template('apps.html',
                           username=username,
                           lang=lang)


@app.route('/colecao/<type>')
def colecao(type):
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


# Página de visualização do objeto e inserção de qualificadores
@app.route('/item/<qid>')
def item(qid):
    username = get_username()
    lang = pt_to_ptbr(get_locale())

    with open(os.path.join(app.static_folder, 'queries.json')) as category_queries:
        all_queries = json.load(category_queries)

    metadata_query = all_queries["Metadados"]["query"].replace("LANGUAGE", lang).replace("QIDDAOBRA", qid)
    brands_query = all_queries["Marcas"]["query"].replace("LANGUAGE", lang).replace("QIDDAOBRA", qid)
    all_objects_query = all_queries["Todos"]["query"].replace("LANGUAGE", lang).replace("QIDDAOBRA", qid)
    next_qid_query = all_queries["Next_qid"]["query"].replace("QIDDAOBRA", qid)
    work_metadata = query_metadata_of_work(metadata_query, lang=lang)
    work_depicts = query_brands_metadata(brands_query, qid)
    next_qid = query_next_qid(next_qid_query)
    if not next_qid:
        next_qid = query_next_qid(all_objects_query)

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
                           qid=qid,
                           next_qid=next_qid)


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
        username = get_username()
        today = datetime.today().strftime('%Y-%m-%dT%H:%M:%S')
        if pid != 'nonvisible':
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
                params["value"] = "{\"text\":\"" + str(claim) + "\",\"language\":\"" + pt_to_ptbr(get_locale()) + "\"}",
            elif pid == 'unknownvalue':
                params["snaktype"] = 'somevalue'
                params["property"] = 'P1716'
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

            return jsonify("200")
        else:
            with open(os.path.join(app.static_folder, 'moreimages.json'), encoding="utf-8") as need_more_images:
                values = json.load(need_more_images)
                if qid in values:
                    values[qid].append({"user": username, "data": today})
                else:
                    values[qid] = [{"user": username, "data": today}]
            with open(os.path.join(app.static_folder, 'moreimages.json'), 'w', encoding="utf-8") as need_more_images:
                json.dump(values, need_more_images, ensure_ascii=False)
            return jsonify(gettext(u'Obrigado! Sua declaração de que esta obra necessita de mais imagens foi inserida no nosso banco de dados com sucesso!'))
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
        lang = pt_to_ptbr(get_locale())

        data = post_search_entity(term, lang)

        items = []
        if "search" in data:
            for item in data["search"]:
                items.append(item["id"])
                # items.append({"qid": item["id"],
                #               "label": item["label"] if 'label' in item else '',
                #               "descr": item["description"] if 'description' in item else ''})

        query = filter_by_instancia("wd:"+" wd:".join(items), lang=lang)

        return jsonify(query), 200


if __name__ == '__main__':
    app.run()
    # https://w.wiki/32TE
    # https://w.wiki/32bR

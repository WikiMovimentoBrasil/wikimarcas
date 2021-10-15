<img src="https://img.shields.io/github/issues/WikiMovimentoBrasil/wikimarcas?style=for-the-badge"/> <img src="https://img.shields.io/github/license/WikiMovimentoBrasil/wikimarcas?style=for-the-badge"/> <img src="https://img.shields.io/github/languages/top/WikiMovimentoBrasil/wikimarcas?style=for-the-badge"/>
# Wiki Museu do Ipiranga - Qual a marca?

This tool is a metadata application to be hosted in Toolforge. It invites Wikimedia users to identify the brands depicted in works of art present in the Museu Paulista collection.

The tool presents the works of the Museu Paulista collection in categories, giving the users autonomy to navigate through the items.
Once in a category, the users see a list of images of the works, to visually help them make their choice on which work to contribute.

Inside the item page, users are presented with a metadata table and some descriptors, defined by the property retrata (P180), and a zoomable image of the item to help them identify the brands of the items depicted.

This tool is available live at: https://wikimarcas.toolforge.org/

## Installation

There are several packages need to this application to function. All of them are listed in the <code>requeriments.txt</code> file. To install them, use

```bash
pip install -r requirements.txt
```

You also need to set the configuration file. To do this, you need [a Oauth consumer token and Oauth consumer secret](https://meta.wikimedia.org/wiki/Special:OAuthConsumerRegistration/propose).
Your config file should look like this:
```bash
SECRET_KEY: "YOUR_SECRET_KEY"
BABEL_DEFAULT_LOCALE: "pt"
APPLICATION_ROOT: "wikimarcas/"
OAUTH_MWURI: "https://meta.wikimedia.org/w/index.php"
CONSUMER_KEY: "YOUR_CONSUMER_KEY"
CONSUMER_SECRET: "YOUR_CONSUMER_SECRET"
LANGUAGES: ["pt","en"]
```

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

Please make sure to update tests as appropriate.

## License
[GNU General Public License v3.0](https://github.com/WikiMovimentoBrasil/wikimarcas/blob/master/LICENSE)

## Credits
This application was developed in the context of the Novo Museu do Ipiranga Project, organized by the Wiki Movimento Brasil User Group and the Museu
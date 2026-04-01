from flask import *
import os
import markdown
from markupsafe import Markup
from flask_pyoidc.provider_configuration import *
from flask_pyoidc.flask_pyoidc import OIDCAuthentication
from boto3 import client
from botocore.config import Config

app = Flask(__name__)

# Load default configuration and any environment variable overrides
_root_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
app.config.from_pyfile(os.path.join(_root_dir, 'config.env.py'))

# Load file based configuration overrides if present
_pyfile_config = os.path.join(_root_dir, 'config.py')
if os.path.exists(_pyfile_config):
    app.config.from_pyfile(_pyfile_config)

app.config.update(
    PREFERRED_URL_SCHEME = app.config.get('URL_SCHEME', 'https'),
    SECRET_KEY = app.config['SECRET_KEY'],
    SERVER_NAME = app.config['SERVER_NAME'],
    WTF_CSRF_ENABLED = False
)

from game_night.auth import require_gamemaster, require_read_key
from game_night.database import *
connect_db(app.config)
from game_night.game import Game


app.jinja_env.lstrip_blocks = True
app.jinja_env.trim_blocks = True
app.url_map.strict_slashes = False

@app.template_filter('markdown')
def _markdown_filter(text):
    if not text:
        return ''
    return Markup(markdown.markdown(text, extensions=['extra', 'sane_lists']))

_config = ProviderConfiguration(
    app.config['OIDC_ISSUER'],
    client_metadata=ClientMetadata(
        client_id=app.config['OIDC_CLIENT_ID'],
        client_secret=app.config['OIDC_CLIENT_SECRET'],
        post_logout_redirect_uris=[app.config['OIDC_LOGOUT_URI']]
    )
)
_auth = OIDCAuthentication({'default': _config}, app)

_s3 = client(
    's3', aws_access_key_id = app.config['S3_KEY'],
    aws_secret_access_key = app.config['S3_SECRET'],
    endpoint_url = app.config['S3_ENDPOINT'],
    config = Config(
        request_checksum_calculation='when_required',
        response_checksum_validation='when_required'
    )
)

@app.route('/api')
@require_read_key
def api():
    return jsonify(list(get_games(request.args)))

@app.route('/api/count')
@require_read_key
def api_count():
    return jsonify(get_count(request.args))

@app.route('/api/key', methods = ['GET', 'POST'])
@require_gamemaster
def api_key():
    return jsonify(generate_api_key())

@app.route('/api/keys')
@require_gamemaster
def api_keys():
    return jsonify(list(get_api_keys()))

@app.route('/api/newest')
@require_read_key
def api_newest():
    return jsonify(list(get_newest_games(request.args)))

@app.route('/api/owners')
@require_read_key
def api_owners():
    return jsonify(list(get_owners(request.args)))

@app.route('/api/random')
@app.route('/api/random/<int:sample_size>')
@require_read_key
def api_random(sample_size = 1):
    sample = list(get_random_games(request.args, sample_size))
    return jsonify(sample[0] if len(sample) == 1 else sample)

@app.route('/api/submitters')
@require_read_key
def api_submitters():
    return jsonify(list(get_submitters(request.args)))

@app.route('/delete/<game_name>', methods = ['POST'])
@_auth.oidc_auth('default')
def delete(game_name):
    if not delete_game(game_name, session['userinfo']['preferred_username']):
        abort(404)
    return redirect('/')

def _get_template_variables():
    return {
        'gamemaster': is_gamemaster(session['userinfo']['preferred_username']),
        'image_url': app.config['IMAGE_URL'],
        'owners': get_owners(), 'players': get_players(),
        'submitters': get_submitters()
    }

@app.route('/')
@_auth.oidc_auth('default')
def index():
    return render_template(
        'index.html', games = get_games(request.args),
        **_get_template_variables()
    )

@app.route('/game/<game_name>')
@_auth.oidc_auth('default')
def game(game_name):
    g = get_game(game_name)
    if not g:
        abort(404)
    return render_template(
        'game.html', expansions = list(get_game_names(g['name'])), game = g,
        **_get_template_variables()
    )

@app.route('/random')
@_auth.oidc_auth('default')
def random():
    return render_template(
        'index.html', games = get_random_games(request.args, 1),
        **_get_template_variables()
    )

@app.route('/submissions')
@_auth.oidc_auth('default')
def submissions():
    return render_template(
        'submissions.html',
        games = get_submissions(
            request.args,
            session['userinfo']['preferred_username']
        ), **_get_template_variables()
    )

@app.route('/submit', methods = ['GET', 'POST'])
@_auth.oidc_auth('default')
def submit():
    if request.method == 'GET':
        return render_template(
            'submit.html',
            form = Game(session['userinfo']['preferred_username']),
            game_names = get_game_names(), **_get_template_variables()
        )
    game = Game()
    if not game.validate():
        return render_template(
            'submit.html',
            error = next(iter(game.errors.values()))[0], form = game,
            game_names = get_game_names(), **_get_template_variables()
        )
    game = game.data
    game = {k: v.strip() if type(v) == str else v for k,v in game.items()}
    filename = game['image'].filename
    extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'jpg'
    game['image_extension'] = extension

    _s3.upload_fileobj(
        game['image'], app.config['S3_BUCKET'], f"{game['name']}.{extension}",
        ExtraArgs = {
            'ACL': 'public-read', 'ContentType': game['image'].content_type
        }
    )
    insert_game(game, session['userinfo']['preferred_username'])
    flash('Game successfully submitted.')
    return redirect('/')

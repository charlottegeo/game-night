from flask import session
from wtforms.validators import DataRequired, Regexp, ValidationError
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import IntegerField, StringField
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
from wtforms.validators import ValidationError

def _validate_expansion(form, field):
    from game_night.database import game_exists
    if field.data and not game_exists(field.data):
        raise ValidationError(f'"{field.data}" is not an expansion')

from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
from wtforms.validators import ValidationError

def _validate_link(form, field):
    try:
        #I had to add a user agent because boardgamegeek was blocking it
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.1;) Gecko/20100101 Firefox/61.2',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        req = Request(field.data, headers=headers)
        urlopen(req, timeout=5) 
    except HTTPError as e:
        if e.code == 403:
            pass
        else:
            raise ValidationError(f'URL is unreachable (HTTP Error: {e.code})')
    except URLError as e:
        raise ValidationError(f'URL is unreachable ({e.reason})')
    except Exception:
        raise ValidationError('URL is unreachable')

def _validate_name(form, field):
    from game_night.database import game_exists
    if game_exists(field.data):
        raise ValidationError(f'"{field.data}" already exists')

def _validate_owner(form, field):
    from game_night.database import is_gamemaster
    if not is_gamemaster(session['userinfo']['preferred_username']) and field.data not in ['CSH', session['userinfo']['preferred_username']]:
        raise ValidationError('Only gamemasters can enter any owner')

class Game(FlaskForm):

    expansion = StringField('expansion', validators = [_validate_expansion])
    image = FileField('image', validators = [
        FileRequired(), FileAllowed(['jpg', 'jpeg', 'png', 'webp'], 'Images only!')
    ])
    link = StringField('link', validators = [
        DataRequired(), Regexp('https://boardgamegeek.com/.*'), _validate_link
    ])
    max_players = IntegerField('max_players', validators = [DataRequired()])
    min_players = IntegerField('min_players', validators = [DataRequired()])
    name = StringField('name', validators = [DataRequired(), _validate_name])
    owner = StringField('owner', validators = [DataRequired(), _validate_owner])

    def __init__(self, submitter = None):
        if submitter:
            super().__init__(
                expansion = '', link = '', max_players = 1, min_players = 1,
                name = '', owner = submitter
            )
        else:
            super().__init__()

    def validate(self):
        if not FlaskForm.validate(self):
            return False
        if self.max_players.data < self.min_players.data:
            self.max_players.errors.append('Max players < min players')
            return False
        return True

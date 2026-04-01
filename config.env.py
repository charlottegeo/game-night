import secrets
import os
from os import environ as env

URL_SCHEME = env.get("URL_SCHEME", "https")
SECRET_KEY = env.get("SECRET_KEY", default="".join(secrets.token_hex(16)))
SERVER_NAME = env.get("SERVER_NAME", "localhost:5000")
MONGODB_DATABASE = env.get("MONGODB_DATABASE", "")
MONGODB_PASSWORD = env.get("MONGODB_PASSWORD", "")
MONGODB_USER = env.get("MONGODB_USER", "")
MONGODB_HOST = env.get("MONGODB_HOST", "mongo.csh.rit.edu")
MONGODB_SSL = env.get("MONGODB_SSL", False)
OIDC_ISSUER = env.get("OIDC_ISSUER", "https://sso.csh.rit.edu/auth/realms/csh")
OIDC_CLIENT_ID = env.get("OIDC_CLIENT_ID", "game-night")
OIDC_CLIENT_SECRET = env.get("OIDC_CLIENT_SECRET", "")
OIDC_LOGOUT_URI = env.get("OIDC_LOGOUT_URI", "http://localhost:5000/logout")
S3_BUCKET = env.get("S3_BUCKET")
S3_KEY = env.get("S3_KEY")
S3_SECRET = env.get("S3_SECRET")
S3_ENDPOINT = env.get("S3_ENDPOINT", "https://s3.csh.rit.edu")
IMAGE_URL = env.get("IMAGE_URL", "https://assets.csh.rit.edu/game-night")

import random, os, hashlib
from flask import Flask, request
from flask_cors import CORS, cross_origin
from urllib.parse import urlparse, urlunparse
from pathlib import Path

app = Flask(__name__)

def require_env(key):
    value = os.getenv(key)
    if not value:
        raise ValueError(f"Environment variable '{key}' is not set.")
    return value

origin = urlparse(require_env('ANNA_I_URL'))
CORS(app, resources={
    '/api/*': {'origins': origin.scheme + '://' + origin.netloc}
})

@app.route('/api/products/')
def api():
    query = request.args.get('q')
    if not query:
        return []

    name = query.title() if len(query) > 3 else query.upper()
    num_items = ord(name[0]) - ord('A') + 1 # A=1 B=2 etc
    if num_items < 1 or num_items > 26:
        return []

    path = Path(__file__).parent / 'static/products'
    files = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f)) and not f.startswith('.')]
    files.sort()

    hash = hashlib.md5(query.encode()).digest()
    seed = int.from_bytes(hash)
    random.seed(seed)
    random.shuffle(files)

    products = [{
        'name' : f[3:].split('.')[0].replace('X', name).replace('_', ' '),
        'pic' : f,
    } for f in files[:num_items]]
    products.sort(key=lambda product: product['name'])
    return products

import random, os, hashlib
from flask import Flask, request
from flask_cors import CORS
from urllib.parse import urlparse
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

static_dir = Path(app.static_folder)
product_pics_dir = static_dir / 'products'
relpath = static_dir.name + '/products/'

@app.route('/api/products/')
def api_products():
    query = request.args.get('q')
    if not query or len(query) < 3:
        return []

    name = query.title() if len(query) > 3 else query.upper()
    num_items = ord(name[0]) - ord('A') + 1 # A=1 B=2 etc
    if num_items < 1 or num_items > 26:
        return []

    files = [f for f in os.listdir(product_pics_dir)
        if os.path.isfile(os.path.join(product_pics_dir, f))
        and not f.startswith('.')
    ]
    files.sort()

    hash = hashlib.md5(query.encode()).digest()
    seed = int.from_bytes(hash)
    random.seed(seed)
    random.shuffle(files)

    products = [{
        'pic' : relpath + f,
        'name' : f[3:].split('.')[0]
            .replace('X', name)
            .replace(name + '~', name.title())
            .replace('_', ' '),
    } for f in files[:num_items]]
    products.sort(key=lambda product: product['name'])
    return products

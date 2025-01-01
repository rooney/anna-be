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
product_images_dir = static_dir / 'products'
relpath = static_dir.name + '/products/'


def unfilename(filename, name):
    return filename[3:].split('.')[0] \
        .replace('X', name) \
        .replace('~' + name + '~', name.lower()) \
        .replace(name + '~', name.title()) \
        .replace('_', ' ')


def brandify(name):
    return name.title() if len(name) > 3 else name.upper()


def product(image_filename, product_name):
    return {
        'name' : unfilename(image_filename, product_name),
        'image' : relpath + image_filename,
    }

@app.route('/api/products/')
def api_products():
    query = request.args.get('q')
    if not query or len(query) < 3:
        return []

    query = query.strip()
    name = brandify(query)
    num_items = ord(name[0]) - ord('A') + 1 # A=1 B=2 etc
    if num_items < 1 or num_items > 26:
        return []

    files = [f for f in os.listdir(product_images_dir)
        if os.path.isfile(os.path.join(product_images_dir, f))
        and not f.startswith('.')
    ]
    files.sort()

    haystack = name.lower().replace('-', ' ')
    for f in files:
        needle = unfilename(f, '').lower().replace('-', ' ')
        if needle in haystack:
            return [product(f, brandify(haystack.replace(needle, '').strip()))]
        
    if ' ' in haystack:
        return []

    hash = hashlib.md5(query.encode()).digest()
    seed = int.from_bytes(hash)
    random.seed(seed)
    random.shuffle(files)

    products = [product(f, name) for f in files[:num_items]]
    products.sort(key=lambda product: product['name'])
    return products

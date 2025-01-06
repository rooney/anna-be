import hashlib, os, random, re
from flask import Flask, request
from flask_cors import CORS
from pathlib import Path
from PIL import Image
from types import SimpleNamespace
from urllib.parse import urlparse

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
product_images_relpath = static_dir.name + '/products/'
files = [f for f in os.listdir(product_images_dir)
    if os.path.isfile(os.path.join(product_images_dir, f))
    and not f.startswith('.')
]
files.sort()


def product(brand, item):
    return {
        'name' : hydrate(item.filename, brand),
        'image' : {
            'src' : item.relpath,
            'width' : item.width,
            'height' : item.height,
        },
    }

def hydrate(filename, brand):
    return filename[4:].split('.')[0] \
        .replace('X', brand) \
        .replace('~' + brand + '~', brand.lower()) \
        .replace('~' + brand, brand.lower()) \
        .replace(brand + '~', brand.title()) \
        .replace('_', ' ')

def pattern_from(filename):
    regex = '(\\S+)'
    scrub = filename.strip().replace('-', ' ').replace('(', '').replace(')', '')
    pattern = hydrate(scrub, '(regex)').lower().replace('(regex)', regex)
    if '~' in filename:
        print(pattern)
        pattern = [part for part in pattern.split(' ') if regex in part][0]

    return re.compile(pattern)

def image_info(filename):
    with Image.open(product_images_dir / filename) as image:
        width, height = image.size
        return SimpleNamespace(
            filename=filename,
            relpath=product_images_relpath + filename,
            pattern=pattern_from(filename),
            width=width,
            height=height,
        )
files = [image_info(f) for f in files]


def catalog_for(brand):
    if brand == 'dhc':
        return [files[f] for f in [12, 58, 32, 5, 8]]

    if len(brand) < 3:
        return []

    if ' ' in brand:
        return []

    num_items = ord(brand[0]) - ord('a') + 1 # A=1 B=2 etc
    if num_items < 1 or num_items > 26:
        return []

    catalog = files[:]
    random.seed(int.from_bytes(hashlib.md5(brand.encode()).digest()))
    random.shuffle(catalog)
    return catalog[:num_items]


@app.route('/api/products/')
def api_products():
    query = request.args.get('q')
    if not query:
        return []

    query = query.strip().lower().replace('-', ' ')
    brand = query
    reverse_matches = set([])
    if len(query) > 3:
        for f in files:
            found = f.pattern.search(query)
            if found:
                brand = found.group(1)
                reverse_matches.add(f.filename)

    catalog = catalog_for(brand)
    matches = [item for item in catalog if item.filename in reverse_matches]
    if not matches and brand != query:
        return []

    brand = brand.title() if len(brand) > 3 else brand.upper()
    products = [product(brand, item) for item in matches or catalog]
    products.sort(key=lambda p: p['name'])
    return products

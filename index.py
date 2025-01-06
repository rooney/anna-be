import random, os, hashlib
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

def image_info(filename):
    with Image.open(product_images_dir / filename) as image:
        width, height = image.size
        return SimpleNamespace(
            filename=filename,
            relpath=product_images_relpath + filename,
            keyword=hydrate(filename, brand='').lower().replace('-', ' '),
            width=width,
            height=height,
        )
files = [image_info(f) for f in files]


@app.route('/api/products/')
def api_products():
    query = request.args.get('q')
    if not query:
        return []

    query = query.strip().lower().replace('-', ' ')
    if len(query) < 3:
        return []

    supermatch = None
    for item in files:
        if item.keyword in query:
            supermatch = item
            brand = query.replace(supermatch.keyword, '')
            break
    else:
        brand = query
                
    num_items = ord(brand[0]) - ord('a') + 1 # A=1 B=2 etc
    if num_items < 1 or num_items > 26:
        return []
    
    if brand == 'dhc':
        catalog = [files[f] for f in [12, 58, 32, 5, 8]]
    else:
        catalog = files[:]
        print('BRAND', brand)
        random.seed(int.from_bytes(hashlib.md5(brand.encode()).digest()))
        random.shuffle(catalog)
        catalog = catalog[:num_items]

    brand = brand.title() if len(brand) > 3 else brand.upper()
    if supermatch is not None:
        print('seper', supermatch)
        for item in catalog:
            print(item)
            if item == supermatch:
                return [product(brand, supermatch)]

    if ' ' in query:
        return []
    
    products = [product(brand, item) for item in catalog]
    products.sort(key=lambda p: p['name'])
    return products

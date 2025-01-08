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
image_files = [f for f in os.listdir(product_images_dir)
    if os.path.isfile(os.path.join(product_images_dir, f))
    and not f.startswith('.')
]
image_files.sort()


def product(brand, item):
    name = brandify(item.filename, brand)
    return {
        'name' : name,
        'tags' : tagify(name),
        'image' : {
            'src' : item.relpath,
            'width' : item.width,
            'height' : item.height,
        },
    }

def denoise(string):
    return string.replace('-', ' ').replace('(', '').replace(')', '')

def tagify(string):
    return denoise(string).lower()

def wordify(string):
    return tagify(string).replace(' ', '')

def brandify(filename, brand):
    brand = brand.title() if len(brand) > 3 else brand.upper()
    return filename[4:].split('.')[0] \
        .replace('X', brand) \
        .replace('~' + brand + '~', brand.lower()) \
        .replace('~' + brand, brand.lower()) \
        .replace(brand + '~', brand.title()) \
        .replace('_', ' ')

def regexify(filename):
    regex = '(.+)'
    pattern = brandify(denoise(filename), '(regex)').lower().replace('(regex)', regex)
    if '~' in filename:
        pattern = [part for part in pattern.split(' ') if regex in part][0]
    return re.compile(pattern)


def image_info(filename):
    with Image.open(product_images_dir / filename) as image:
        width, height = image.size
        return SimpleNamespace(
            filename=filename,
            relpath=product_images_relpath + filename,
            regex=regexify(filename),
            width=width,
            height=height,
        )
image_files = [image_info(file) for file in image_files]


def catalog_for(brand):
    if brand == 'dhc':
        return [product('DHC', image_files[i]) for i in [12, 58, 32, 5, 8]]

    if len(brand) < 3:
        return []

    if ' ' in brand:
        return []

    num_items = ord(brand[0]) - ord('a') + 1 # A=1 B=2 etc
    if num_items < 1 or num_items > 26:
        return []

    catalog = image_files[:]
    random.seed(int.from_bytes(hashlib.md5(brand.encode()).digest()))
    random.shuffle(catalog)
    return [product(brand, item) for item in catalog[:num_items]]


def subs_of(string):
    max_length = len(string)
    for length in range(3, max_length):
        for i in range(max_length - length + 1):
            yield string[i:(i + length)]


def lookup(query):
    worded = wordify(query)
    part = re.compile(query.replace(' ', '.*'))
    full = re.compile(r'\b' + query + r'\b')

    if (len(worded) < 3):
        return []
    
    if len(worded) == 3:
        return catalog_for(worded)

    for brand in subs_of(worded):
        catalog = catalog_for(brand)

        full_matches = [item for item in catalog if full.search(item['tags'])]
        if full_matches:
            return full_matches
        
        part_matches = [item for item in catalog if part.search(wordify(item['tags']))]
        if part_matches:
            return part_matches
    
    return catalog_for(query)


@app.route('/api/products/')
def api_products():
    query = request.args.get('q')
    if not query:
        return []

    products = lookup(query.strip())
    products.sort(key=lambda item: item['name'])
    return products


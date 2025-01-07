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
imagefiles = [f for f in os.listdir(product_images_dir)
    if os.path.isfile(os.path.join(product_images_dir, f))
    and not f.startswith('.')
]
imagefiles.sort()

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
imagefiles = map(image_info, imagefiles)


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

def brandify(filename, brand):
    return filename[4:].split('.')[0] \
        .replace('X', brand) \
        .replace('~' + brand + '~', brand.lower()) \
        .replace('~' + brand, brand.lower()) \
        .replace(brand + '~', brand.title()) \
        .replace('_', ' ')

def regexify(filename):
    regex = '(\\S+)'
    pattern = brandify(denoise(filename), '(regex)').lower().replace('(regex)', regex)
    if '~' in filename:
        pattern = [part for part in pattern.split(' ') if regex in part][0]
    return re.compile(pattern)

def catalog_for(brand):
    if brand == 'DHC':
        return [imagefiles[f] for f in [12, 58, 32, 5, 8]]

    if len(brand) < 3:
        return []

    if ' ' in brand:
        return []

    num_items = ord(brand[0]) - ord('A') + 1 # A=1 B=2 etc
    if num_items < 1 or num_items > 26:
        return []

    catalog = imagefiles[:]
    random.seed(int.from_bytes(hashlib.md5(brand.encode()).digest()))
    random.shuffle(catalog)
    return catalog[:num_items]

def lookup(query):
    query = tagify(query)
    brand = query
    reverse_matches = set([])
    if len(query) > 3:
        for f in imagefiles:
            found = f.regex.search(query)
            if found:
                reverse_matches.add(f.filename)
                capture = found.group(1)
                if len(capture) < len(brand):
                    brand = capture

    brand = brand.title() if len(brand) > 3 else brand.upper()
    catalog = catalog_for(brand)
    matches = [item for item in catalog if item.filename in reverse_matches]
    products = [product(brand, item) for item in matches or catalog]
    fullmatches = [item for item in products if query in item['tags']]
    if fullmatches:
        return fullmatches

    if ' ' in query:
        parts = query.split(' ')
        regex = '.*'.join(parts)
        already_found = set([item['name'] for item in products])
        related = [item for part in parts for item in lookup(part)
            if re.search(regex, item['tags'])
            and item['name'] not in already_found
        ]
        products.extend(related)
    return products


@app.route('/api/products/')
def api_products():
    query = request.args.get('q')
    if not query:
        return []

    products = lookup(query.strip())
    products.sort(key=lambda item: item['name'])
    return products


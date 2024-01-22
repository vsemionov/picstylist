import os
from pathlib import Path

import numpy as np
import tensorflow as tf
import tensorflow_hub as hub
from PIL import Image

MAX_SIZE = 1024

os.environ['TFHUB_CACHE_DIR'] = str(Path(__file__).parent / '..' / 'model')
hub_model = hub.load('https://tfhub.dev/google/magenta/arbitrary-image-stylization-v1-256/2')


def load_image(image_path):
    image = Image.open(image_path).convert('RGB')
    width, height = image.size
    long_edge = max(width, height)
    if long_edge > MAX_SIZE:
        scale = MAX_SIZE / long_edge
        width, height = max(int(width * scale), 1), max(int(height * scale), 1)
        image = image.resize((width, height))
    return tf.constant(image, dtype=tf.float32)[tf.newaxis, :] / 255


def tensor_to_image(tensor):
    array = np.array(tensor * 255, dtype=np.uint8)[0]
    return Image.fromarray(array)


def save_image(image, result_stem):
    path = f'{result_stem}.jpg'
    image.save(path)
    return path


def fast_style_transfer(content_path, style_path, result_stem):
    content_image = load_image(content_path)
    style_image = load_image(style_path)

    stylized_image = hub_model(content_image, style_image)[0]

    return save_image(tensor_to_image(stylized_image), result_stem)

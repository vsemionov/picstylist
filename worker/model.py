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


def save_image(image, result_path):
    image.save(result_path)


def fast_style_transfer(base_path, content_filename, style_filename, result_filename):
    content_path = os.path.join(base_path, content_filename)
    style_path = os.path.join(base_path, style_filename)
    result_path = os.path.join(base_path, result_filename)
    content_image = load_image(content_path)
    style_image = load_image(style_path)
    stylized_image = hub_model(content_image, style_image)[0]
    save_image(tensor_to_image(stylized_image), result_path)

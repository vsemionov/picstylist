import os
from pathlib import Path

import numpy as np
import tensorflow as tf
import tensorflow_hub as hub
from PIL import Image

from worker import iterative


MAX_SIZE = 400


os.environ['TFHUB_CACHE_DIR'] = str(Path(__file__).parent.parent / 'models')
fast_model = hub.load('https://tfhub.dev/google/magenta/arbitrary-image-stylization-v1-256/2')


def _load_image(image_path):
    image = Image.open(image_path).convert('RGB')
    size = image.size
    long_edge = max(size)
    if long_edge > MAX_SIZE:
        scale = MAX_SIZE / long_edge
        size = [max(round(s * scale), 1) for s in size]
        image = image.resize(size, resample=Image.Resampling.BILINEAR)
    return image


def load_image(image_path):
    return tf.constant(_load_image(image_path), dtype=tf.float32)[tf.newaxis, :] / 255


def to_image(tensor):
    array = np.array(tensor * 255, dtype=np.uint8)
    return Image.fromarray(array)


def blend_images(content, output, alpha):
    if alpha == 1:
        return output
    if output.shape != content.shape:
        content = tf.image.resize(content, output.shape[:-1])
    return alpha * output + (1 - alpha) * content


def save_image(image, result_path):
    image.save(result_path)
    return image.size


def fast_style_transfer(base_path, content_filename, style_filename, strength, result_filename):
    content_input = load_image(base_path / content_filename)
    style_input = load_image(base_path / style_filename)
    model_output = fast_model(content_input, style_input)[0][0]
    output = blend_images(content_input[0], model_output, strength / 100)
    return save_image(to_image(output), base_path / result_filename)


def iterative_style_transfer(base_path, content_filename, style_filename, strength, result_filename):
    content_image = _load_image(base_path / content_filename)
    style_image = _load_image(base_path / style_filename)
    output = iterative.style_transfer(content_image, style_image, strength)
    return save_image(output, base_path / result_filename)

import os
from pathlib import Path

import numpy as np
import tensorflow as tf
import tensorflow_hub as hub
from PIL import Image


MAX_SIZE = 512


os.environ['TFHUB_CACHE_DIR'] = str(Path(__file__).parent.parent / 'model')
hub_model = hub.load('https://tfhub.dev/google/magenta/arbitrary-image-stylization-v1-256/2')


def load_image(image_path):
    image = Image.open(image_path).convert('RGB')
    width, height = image.size
    long_edge = max(width, height)
    if long_edge > MAX_SIZE:
        scale = MAX_SIZE / long_edge
        width, height = max(int(width * scale), 1), max(int(height * scale), 1)
        image = image.resize((width, height), resample=Image.Resampling.BICUBIC)
    return tf.constant(image, dtype=tf.float32)[tf.newaxis, :] / 255


def to_image(tensor):
    array = np.array(tensor * 255, dtype=np.uint8)
    return Image.fromarray(array)


def blend_images(content, output, alpha):
    if alpha == 1:
        return output
    if output.shape != content.shape:
        content = tf.image.resize(content, output.shape[:-1], method=tf.image.ResizeMethod.BICUBIC)
    return alpha * output + (1 - alpha) * content


def save_image(image, result_path):
    image.save(result_path)
    return image.size


def fast_style_transfer(base_path, content_filename, style_filename, strength, result_filename):
    content_input = load_image(base_path / content_filename)
    style_input = load_image(base_path / style_filename)
    model_output = hub_model(content_input, style_input)[0][0]
    output = blend_images(content_input[0], model_output, strength / 100)
    return save_image(to_image(output), base_path / result_filename)

import numpy as np
import tensorflow as tf
from PIL import Image

from . import weights


MAX_SIZE = 400


model = weights.get_hub_model()


def to_tensor(image):
    return tf.constant(image) / 255


def to_image(tensor):
    array = np.array(tensor * 255, dtype=np.uint8)
    return Image.fromarray(array)


def blend_images(content, output, alpha):
    if alpha == 1:
        return output
    if output.shape != content.shape:
        content = tf.image.resize(content, output.shape[:-1])
    return alpha * output + (1 - alpha) * content


def style_transfer(content_image, style_image, strength):
    content_image = to_tensor(content_image)[tf.newaxis, :]
    style_image = to_tensor(style_image)[tf.newaxis, :]
    output = model(content_image, style_image)[0][0]
    output = blend_images(content_image[0], output, strength / 100)
    return to_image(output)

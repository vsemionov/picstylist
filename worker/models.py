import os
from pathlib import Path
import logging

import numpy as np
import tensorflow as tf
import tensorflow_hub as hub
from PIL import Image


MAX_SIZE = 512


logger = logging.getLogger(__name__)

os.environ['TFHUB_CACHE_DIR'] = str(Path(__file__).parent.parent / 'models')
fast_model = hub.load('https://tfhub.dev/google/magenta/arbitrary-image-stylization-v1-256/2')

vgg = tf.keras.applications.VGG19(include_top=False, weights='imagenet')
vgg.trainable = False

content_layers = ['block5_conv2']
style_layers = ['block1_conv1', 'block2_conv1', 'block3_conv1', 'block4_conv1', 'block5_conv1']
num_content_layers = len(content_layers)
num_style_layers = len(style_layers)

style_weight = 1e-2
content_weight = 1e4
total_variation_weight = 30
total_steps = 500


class StyleContentModel(tf.keras.models.Model):
    def __init__(self):
        super().__init__()
        outputs = [vgg.get_layer(name).output for name in (style_layers + content_layers)]
        self.vgg = tf.keras.Model([vgg.input], outputs)
        self.vgg.trainable = False

    @staticmethod
    def gram_matrix(tensor):
        result = tf.linalg.einsum('bijc,bijd->bcd', tensor, tensor)
        input_shape = tf.shape(tensor)
        num_locations = tf.cast(input_shape[1] * input_shape[2], tf.float32)
        return result / num_locations

    def call(self, inputs, training=None, mask=None):
        inputs = inputs * 255
        preprocessed_input = tf.keras.applications.vgg19.preprocess_input(inputs)
        outputs = self.vgg(preprocessed_input)

        style_outputs, content_outputs = (outputs[:num_style_layers], outputs[num_style_layers:])
        style_outputs = [self.__class__.gram_matrix(style_output) for style_output in style_outputs]
        content_dict = {content_name: value for content_name, value in zip(content_layers, content_outputs)}
        style_dict = {style_name: value for style_name, value in zip(style_layers, style_outputs)}

        return {'content': content_dict, 'style': style_dict}


extractor = StyleContentModel()


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


def style_content_loss(outputs, style_targets, content_targets):
    style_outputs = outputs['style']
    style_loss = tf.add_n([tf.reduce_mean((style_outputs[name] - style_targets[name])**2)
        for name in style_outputs.keys()])
    style_loss *= style_weight / num_style_layers

    content_outputs = outputs['content']
    content_loss = tf.add_n([tf.reduce_mean((content_outputs[name] - content_targets[name])**2)
        for name in content_outputs.keys()])
    content_loss *= content_weight / num_content_layers

    return style_loss + content_loss


def fast_style_transfer(base_path, content_filename, style_filename, strength, result_filename):
    content_input = load_image(base_path / content_filename)
    style_input = load_image(base_path / style_filename)
    model_output = fast_model(content_input, style_input)[0][0]
    output = blend_images(content_input[0], model_output, strength / 100)
    return save_image(to_image(output), base_path / result_filename)


def iterative_style_transfer(base_path, content_filename, style_filename, strength, result_filename):
    @tf.function()
    def train_step():
        with tf.GradientTape() as tape:
            outputs = extractor(image)
            loss = style_content_loss(outputs, style_targets, content_targets)
            loss += total_variation_weight * tf.image.total_variation(image)

        grad = tape.gradient(loss, image)
        optimizer.apply_gradients([(grad, image)])
        image.assign(tf.clip_by_value(image, 0, 1))

    content_image = load_image(base_path / content_filename)
    style_image = load_image(base_path / style_filename)

    style_targets = extractor(style_image)['style']
    content_targets = extractor(content_image)['content']

    image = tf.Variable(content_image)
    optimizer = tf.keras.optimizers.Adam(learning_rate=0.02, beta_1=0.99, epsilon=1e-1)

    steps = int(total_steps * strength / 100)
    for n in range(1, steps + 1):
        train_step()
        if n % 100 == 0 and n > 0 or n == steps:
            logger.info('Step %d/%d', n, steps)

    tf.keras.backend.clear_session()

    output = blend_images(content_image[0], image[0], strength / 100)
    return save_image(to_image(output), base_path / result_filename)

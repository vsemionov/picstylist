import os
from pathlib import Path
from typing import Optional

import numpy as np
import tensorflow as tf
import tensorflow_hub as hub
from PIL import Image

os.environ['TFHUB_CACHE_DIR'] = str(Path(__file__).parent.parent / 'model')
hub_model = hub.load('https://tfhub.dev/google/magenta/arbitrary-image-stylization-v1-256/2')

vgg_model = tf.keras.applications.VGG19(include_top=False, weights='imagenet')
vgg_model.trainable = False
content_layers = ['block5_conv2']
style_layers = ['block1_conv1', 'block2_conv1', 'block3_conv1', 'block4_conv1', 'block5_conv1']
style_weight = 1e-2
content_weight = 1e4
total_variation_weight = 30
opt = tf.keras.optimizers.Adam(learning_rate=0.02, beta_1=0.99, epsilon=1e-1)


def load_image(image_path):
    max_size = 128
    image = Image.open(image_path).convert('RGB')
    width, height = image.size
    long_edge = max(width, height)
    if long_edge > max_size:
        scale = max_size / long_edge
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


def vgg_layers(layer_names):
    outputs = [vgg_model.get_layer(name).output for name in layer_names]
    return tf.keras.Model([vgg_model.input], outputs)


def gram_matrix(input_tensor):
    result = tf.linalg.einsum('bijc,bijd->bcd', input_tensor, input_tensor)
    input_shape = tf.shape(input_tensor)
    num_locations = tf.cast(input_shape[1] * input_shape[2], tf.float32)
    return result / num_locations


class StyleContentModel(tf.keras.models.Model):
    def __init__(self, style_layers, content_layers):
        super(StyleContentModel, self).__init__()
        self.vgg = vgg_layers(style_layers + content_layers)
        self.style_layers = style_layers
        self.content_layers = content_layers
        self.num_style_layers = len(style_layers)
        self.vgg.trainable = False

    def call(self, inputs, *args, **kwargs):
        inputs = inputs * 255.0
        preprocessed_input = tf.keras.applications.vgg19.preprocess_input(inputs)
        outputs = self.vgg(preprocessed_input)
        style_outputs, content_outputs = (outputs[:self.num_style_layers], outputs[self.num_style_layers:])

        style_outputs = [gram_matrix(style_output) for style_output in style_outputs]

        content_dict = {content_name: value for content_name, value in zip(self.content_layers, content_outputs)}

        style_dict = {style_name: value for style_name, value in zip(self.style_layers, style_outputs)}

        return {'content': content_dict, 'style': style_dict}


extractor: Optional[StyleContentModel] = None


def init():
    global extractor
    extractor = StyleContentModel(style_layers, content_layers)


def clip_0_1(image):
    return tf.clip_by_value(image, clip_value_min=0.0, clip_value_max=1.0)


def style_content_loss(outputs, style_targets, content_targets):
    style_outputs = outputs['style']
    content_outputs = outputs['content']
    style_loss = tf.add_n([tf.reduce_mean((style_outputs[name] - style_targets[name]) ** 2)
                           for name in style_outputs.keys()])
    style_loss *= style_weight / len(style_layers)

    content_loss = tf.add_n([tf.reduce_mean((content_outputs[name] - content_targets[name]) ** 2)
                             for name in content_outputs.keys()])
    content_loss *= content_weight / len(content_layers)
    loss = style_loss + content_loss
    return loss


@tf.function()
def train_step(image, style_targets, content_targets):
    with tf.GradientTape() as tape:
        outputs = extractor(image)
        loss = style_content_loss(outputs, style_targets, content_targets)
        loss += total_variation_weight * tf.image.total_variation(image)

    grad = tape.gradient(loss, image)
    opt.apply_gradients([(grad, image)])
    image.assign(clip_0_1(image))


def classic_model(content_image, style_image):
    style_targets = extractor(style_image)['style']
    content_targets = extractor(content_image)['content']
    image = tf.Variable(content_image)
    for n in range(1000):
        train_step(image, style_targets, content_targets)
        if n % 10 == 0:
            print('.', end='', flush=True)

    return image


def style_transfer(base_path, content_filename, style_filename, strength, result_filename):
    content_input = load_image(base_path / content_filename)
    style_input = load_image(base_path / style_filename)
    model_output = classic_model(content_input, style_input)[0]
    output = blend_images(content_input[0], model_output, strength / 100)
    return save_image(to_image(output), base_path / result_filename)

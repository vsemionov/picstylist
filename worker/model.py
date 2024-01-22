import os
import time
from pathlib import Path

import numpy as np
import tensorflow as tf
import tensorflow_hub as hub
from PIL import Image

import grpc
from tensorflow_serving.apis import predict_pb2, prediction_service_pb2_grpc


MAX_SIZE = 1024


def prepare_model():
    model_dir = Path(__file__).parent / '..' / 'model'
    model_path = model_dir / '0001'
    if model_path.exists():
        return
    os.environ['TFHUB_CACHE_DIR'] = str(model_dir)
    hub.load('https://tfhub.dev/google/magenta/arbitrary-image-stylization-v1-256/2')
    for path in model_dir.glob('**/saved_model.pb'):
        path.parent.rename(model_path)
        break


def load_image(image_path):
    image = Image.open(image_path).convert('RGB')
    width, height = image.size
    long_edge = max(width, height)
    if long_edge > MAX_SIZE:
        scale = MAX_SIZE / long_edge
        width, height = max(int(width * scale), 1), max(int(height * scale), 1)
        image = image.resize((width, height))
    return tf.constant(image, dtype=tf.float32)[tf.newaxis, :] / 255


def array_to_image(tensor):
    array = (tensor * 255).astype(np.uint8)[0]
    return Image.fromarray(array)


def save_image(image, result_stem):
    path = f'{result_stem}.jpg'
    image.save(path)
    return path


def call_model(content_image, style_image):
    request = predict_pb2.PredictRequest()
    request.model_spec.name = 'fast_style_transfer'
    request.model_spec.signature_name = 'serving_default'
    request.inputs['placeholder'].CopyFrom(tf.make_tensor_proto(content_image))
    request.inputs['placeholder_1'].CopyFrom(tf.make_tensor_proto(style_image))

    options = [
        ('grpc.max_send_message_length', 128 * 1024 * 1024),
        ('grpc.max_receive_message_length', 128 * 1024 * 1024)
    ]
    channel = grpc.insecure_channel(f'tfserving:8500', options=options)
    predict_service = prediction_service_pb2_grpc.PredictionServiceStub(channel)
    t0 = time.time()
    response = predict_service.Predict(request, timeout=30)
    print(f'Prediction took {time.time() - t0:.1f} seconds')
    outputs_proto = response.outputs['output_0']
    y = tf.make_ndarray(outputs_proto)
    return y


def fast_style_transfer(content_path, style_path, result_stem):
    content_image = load_image(content_path)
    style_image = load_image(style_path)

    stylized_image = call_model(content_image, style_image)[0]

    return save_image(array_to_image(stylized_image), result_stem)

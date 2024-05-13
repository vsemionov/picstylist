import os
from pathlib import Path


def get_vgg_model():
    from torchvision.models import vgg19, VGG19_Weights
    return vgg19(weights=VGG19_Weights.IMAGENET1K_V1)


def get_hub_model():
    import tensorflow_hub as hub
    os.environ['TFHUB_CACHE_DIR'] = str(Path.home() / '.cache' / 'tfhub')
    return hub.load('https://tfhub.dev/google/magenta/arbitrary-image-stylization-v1-256/2')


def download_all():
    get_vgg_model()
    get_hub_model()

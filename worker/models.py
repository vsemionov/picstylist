from PIL import Image

from . import fast, iterative


FAST_MAX_SIZE = 512
ITER_MAX_SIZE = 400


def load_image(image_path, max_size):
    image = Image.open(image_path).convert('RGB')
    size = image.size
    long_edge = max(size)
    if long_edge > max_size:
        scale = max_size / long_edge
        size = [max(round(s * scale), 1) for s in size]
        image = image.resize(size, resample=Image.Resampling.BILINEAR)
    return image


def save_image(image, result_path):
    image.save(result_path)
    return image.size


def style_transfer(module, max_size, base_path, content_filename, style_filename, strength, result_filename):
    content_image = load_image(base_path / content_filename, max_size)
    style_image = load_image(base_path / style_filename, max_size)
    output = module.style_transfer(content_image, style_image, strength)
    return save_image(output, base_path / result_filename)


def fast_style_transfer(*args, **kwargs):
    return style_transfer(fast, FAST_MAX_SIZE, *args, **kwargs)


def iterative_style_transfer(*args, **kwargs):
    return style_transfer(iterative, ITER_MAX_SIZE, *args, **kwargs)

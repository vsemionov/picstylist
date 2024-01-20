import os

import worker.model


def style_image(content_path, style_path, output_name):
    try:
        return worker.model.fast_style_transfer(content_path, style_path, output_name)
    finally:
        try:
            os.remove(content_path)
            os.remove(style_path)
        except OSError:
            pass

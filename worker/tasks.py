import os

import worker.model


def style_image(content_path, style_path, result_stem):
    try:
        return worker.model.fast_style_transfer(content_path, style_path, result_stem)
    finally:
        for path in [content_path, style_path]:
            try:
                os.remove(path)
            except OSError:
                pass

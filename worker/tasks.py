import os
import logging


logger = logging.getLogger(__name__)


def style_image(content_path, style_path, result_stem):
    try:
        import worker.model
        logger.info(f'Processing')
        return worker.model.fast_style_transfer(content_path, style_path, result_stem)
    finally:
        for path in [content_path, style_path]:
            try:
                os.remove(path)
            except OSError:
                pass

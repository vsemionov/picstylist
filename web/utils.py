from functools import wraps

from flask import make_response


def no_cache(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        response = make_response(view(*args, **kwargs))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response

    return wrapped_view

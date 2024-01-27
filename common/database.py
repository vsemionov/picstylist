import sqlite3


def connect(database):
    db = sqlite3.connect(database, detect_types=sqlite3.PARSE_DECLTYPES)
    db.row_factory = sqlite3.Row
    return db

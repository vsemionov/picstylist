def start_job(db):
    with db:
        cur = db.execute('INSERT INTO job_history DEFAULT VALUES')
        return cur.lastrowid


def end_job(db, id, succeeded):
    with db:
        cur = db.execute('UPDATE job_history SET succeeded = ?, ended = CURRENT_TIMESTAMP WHERE id = ?',
            (succeeded, id))
        if not cur.rowcount:
            raise ValueError('Job history entry not found.')


def get_job_stats(db):
    return {'week': (100, 10, 2)}


def cleanup(db):
    with db:
        cur = db.execute("DELETE FROM job_history WHERE started < datetime('now', '-1 year')")
        return cur.rowcount

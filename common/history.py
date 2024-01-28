def start_job(db):
    with db:
        cur = db.execute('INSERT INTO job_history DEFAULT VALUES')
        return cur.lastrowid


#######################
def start_job(db, dt):
    import random
    with db:
        cur = db.execute('INSERT INTO job_history (started, succeeded) VALUES (?, ?)',
                         (dt, random.choice([True, False, None])))
        return cur.lastrowid


def end_job(db, id, succeeded):
    with db:
        cur = db.execute('UPDATE job_history SET succeeded = ?, ended = CURRENT_TIMESTAMP WHERE id = ?',
            (succeeded, id))
        if not cur.rowcount:
            raise ValueError('Job history entry not found.')


def get_job_stats(db):
    periods = ['hour', '_4_hours', 'day', 'week', 'month', '_3_months', 'year']
    modifiers = ['-1 hour', '-4 hours', '-1 day', '-7 days', '-1 month', '-3 months', '-1 year']
    rows = []
    for succeeded in [True, False, None]:
        cols = []
        params = []
        for period, modifier in zip(periods, modifiers):
            cols.append(f"COUNT(*) FILTER (WHERE started > datetime('now', ?)) as {period}")
            params.append(modifier)
        cur = db.execute(f"SELECT {', '.join(cols)} FROM job_history WHERE succeeded IS ?", params + [succeeded])
        row = cur.fetchone()
        rows.append(row)
    return {period.replace('_', ' ').strip(): [row[period] for row in rows] for period in periods}


def cleanup(db):
    with db:
        cur = db.execute("DELETE FROM job_history WHERE started < datetime('now', '-1 year')")
        return cur.rowcount

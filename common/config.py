JOBS_DIR = 'jobs'
DATABASE = 'db.sqlite3'

DEFAULT_QUEUE = 'default'
SYSTEM_QUEUE = 'system'

HEALTH_CHECK_INTERVAL = 15 * 60
HEALTH_CHECK_VALIDITY = 30 * 60
HEALTH_CHECK_JOB_ID = 'health_check'

IMAGE_CHECK_INTERVAL = 15 * 60
IMAGE_CHECK_VALIDITY = 30 * 60
IMAGE_CHECK_JOB_ID = 'image_check'

LOG_FORMAT = '%(levelname)s in %(name)s: %(message)s'

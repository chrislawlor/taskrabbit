USERNAME = "guest"
PASSWORD = "guest"
HOST = "rabbit"
PORT = 5672
VHOST = "/"
EXCHANGE = "taskrabbit"
DEFAULT_LOG_LEVEL = "INFO"

# Sets kombu Consumer prefetch count
# See https://docs.celeryproject.org/projects/kombu/en/stable/userguide/consumers.html#reference  # noqa
CONSUMER_PREFETCH_COUNT = 500

URL = f"amqp://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/{VHOST}"

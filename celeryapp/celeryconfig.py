from kombu import Queue

task_default_exchange = "tasks"
task_default_exchange_type = "topic"

task_queues = (
    Queue("arithmetic", routing_key="arithmetic.#"),
    Queue("geometry", routing_key="geometry.#"),
)
task_default_queue = "arithmetic"
task_default_routing_key = "arithmetic.default"

# fmt: off
task_routes = {
    "tasks.slope": {
        "queue": "geometry",
        "routing_key": "geometry.euclidean",
    }
}
# fmt: on

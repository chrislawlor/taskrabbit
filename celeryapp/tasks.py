from celery import Celery

app = Celery("celeryapp", broker="amqp://guest:guest@rabbit//")
app.config_from_object("celeryconfig")


@app.task
def add(x, y):
    return x + y


@app.task
def multiply(x, y):
    return x * y


@app.task
def slope(x1, y1, x2, y2):
    return (y2 - y1) / (x2 - x1)


if __name__ == "__main__":
    for i in range(50):
        add.delay(i, i)

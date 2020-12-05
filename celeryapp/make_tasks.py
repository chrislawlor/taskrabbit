from tasks import add, multiply, slope


for i in range(10_000):
    add.delay(i, i)
    multiply.delay(i, i)
    slope.delay(i, i, i + 1, i + 2)

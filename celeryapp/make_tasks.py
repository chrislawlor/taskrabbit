from tasks import add, multiply, subtract

for i in range(20):
    add.delay(i, i)
    multiply.delay(i, i)
    subtract.delay(i, i)

from tasks import add, multiply

for i in range(30):
    add.delay(i, i)
    multiply.delay(i, i)

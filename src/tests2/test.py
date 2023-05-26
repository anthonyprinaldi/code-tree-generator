def func1(x):
    return x ** 2

def func2(x):
    def func1(x):
        return x * 2
    
    return func1(x) ** 2


x = func1(2)
y = func2(2)

print(x)

print(y)
from module1.temp import ONE
import module1.temp
from examine2 import test_func

test_func(1, 2, 3)

module1.temp.TWO.get(5)

print(module1.temp.ONE)
print(ONE)

num1 = 1.5
num2 = 6.3

# Add two numbers
sum = num1 + num2

# Display the sum
print('The sum of {0} and {1} is {2}'.format(num1, num2, sum))

# Note: change this value for a different result
if sum > 10:
    num = 8
else:
    num = 4

num_sqrt = num ** 0.5
print('The square root of %0.3f is %0.3f'%(num ,num_sqrt))

class TestClass(object):
    def __init__(self, a):
        self.a = a
    def __str__(self):
        return 'Wow ' + str(self.a)
    def method1(self):
        print('method1')

obj = TestClass(10)
print(obj)
obj.method1()
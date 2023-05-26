import sys
from typing import Union
from examine3 import num1

def test_func(a: Union[float, int] ,b: Union[float, int] , c: Union[float, int] = 10) -> None:
    print((a + b) / c)

test_func(1, 2, 3)

test_func(1, 2, 4)

print(num1)
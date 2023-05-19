import sys
from typing import Union

def test_func(a: Union[float, int] ,b: Union[float, int] , c: Union[float, int] = 10) -> None:
    print((a + b) / c)

test_func(1, 2, 3)

test_func(1, 2, 4)
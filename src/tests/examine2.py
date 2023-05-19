import sys

def test_func(a: float ,b: float , c:float = 10) -> None:
    print((a + b) / c)

test_func(1, 2, 3)

test_func(1, 2, 4)
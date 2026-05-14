"""
i am a docstring
"""

class TestClass:
    """
    i am a docstring
    """
    def __init__(self, x: int):
        """
        i am a docstring
        """
        x *= 2
        self.x = x
        self.x += 1
        self.a, self.b = self.method_a(), self.method_b()
        self.e = self.f = self.g = self.h = 'test'

    def method_a(self):
        return self.x + 1

    def method_b(self):
        return self.x * 2

class YetAnotherTestClass:
    def __init__(self):
        self.test_class = TestClass(55)
    class_var = 5

    def test_method(self):
        a = 53 ** 0
        print(a * 10, self.test_class.x)

        class Foo:
            xxx = 3
        print(Foo.xxx)


t = TestClass(42)
print(t.x, t.a, t.b)
print(t.e, t.f, t.g, t.h)
y = YetAnotherTestClass()
y.test_method()

print(YetAnotherTestClass.class_var)

global_x = [1]
global_x.append(3)


def f():
    global global_x
    global_x.extend([4, 5])
f()
print(global_x)

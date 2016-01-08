__author__ = 'sarangis'

from src.ir.types import *

class Value:
    def __init__(self):
        pass

class Argument(Value):
    def __init__(self, name):
        Value.__init__(self)
        self.__name = name

    @property
    def name(self):
        return self.__name

    def __str__(self):
        return self.__name

    __repr__ = __str__
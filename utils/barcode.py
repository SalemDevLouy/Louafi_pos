import time
import random


def generate_barcode() -> str:
    # generate a compact, mostly-unique barcode using time and random
    return f"B{int(time.time()*1000)}{random.randint(10,99)}"

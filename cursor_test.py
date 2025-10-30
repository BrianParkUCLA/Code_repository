# Test file for Cursor Tab suggestions
# Try typing after each comment to see if suggestions appear

import numpy as np
import pandas as pd

# Test 1: Basic Python
def calculate_sum(a, b):
    # Type here to test suggestions
    return a + b

# Test 2: List comprehension
numbers = [1, 2, 3, 4, 5]
squared = [x**2 for x in numbers]

# Test 3: DataFrame operations
df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})

# Test 4: Type hints
def process_data(data: list) -> dict:
    # Type here to test suggestions
    result = {}
    for item in data:
        result[item] = len(str(item))
    return result

# Test 5: Class definition
class DataProcessor:
    def __init__(self):
        self.data = []
    
    def add_item(self, item):
        # Type here to test suggestions
        self.data.append(item)
    
    def get_sum(self):
        # Type here to test suggestions
        return sum(self.data)

# Test 6: Error handling
try:
    # Type here to test suggestions
    result = 10 / 0
except ZeroDivisionError:
    # Type here to test suggestions
    print("Division by zero error")

# Test 7: Context-aware suggestions
if True:
    # Type here to test suggestions
    string = "Hello World"
    pass

# Test 8: String operations
text = "Hello World"
# Type here to test suggestions

from cv_parser import parse_cv_sync
import time

text = """
Nagaraj Bhagwat
Senior SDV Architect
20 years automotive software experience
AUTOSAR Adaptive
AUTOSAR Classic
"""

start = time.time()

result = parse_cv_sync(text)

print("TIME:", time.time()-start)
print(result)

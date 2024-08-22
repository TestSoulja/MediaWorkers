import os
import pandas as pd
from datetime import datetime
import numpy as np
import os.path
import os
from os.path import getsize, join

s = os.path.abspath(__file__)
c = s.replace(os.path.basename(os.path.abspath(__file__)), "")

print("_________________________________________________________________________________________________")


file_count = sum(len(files) for _, _, files in os.walk(r'C:\Users\super\YandexDisk'))
print(file_count)
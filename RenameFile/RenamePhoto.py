import os
import pathlib

s = os.path.abspath(__file__)
c = s.replace(os.path.basename(os.path.abspath(__file__)), "")

n = 4319

path = pathlib.Path(c+"/Enter")
for i, path in enumerate(path.glob('*.png')):
    new_name = c + "/Exit/"+ str(n) + '.png'
    path.rename(new_name)
    n += 1

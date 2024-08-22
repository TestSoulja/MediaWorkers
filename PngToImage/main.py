import os
from pdf2jpg import pdf2jpg

s = os.path.abspath(__file__)
c = s.replace(os.path.basename(os.path.abspath(__file__)), '')


inputpath = c+'Enter/1.pdf'
outputpath = c+"Exit/1.png"
result = pdf2jpg.convert_pdf2jpg(inputpath,outputpath, pages="ALL")
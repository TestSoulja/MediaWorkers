from PIL import Image
from colorama import Fore
import os.path

directory = r'D:\_Test\End'
files = os.listdir(directory)

counter = 0

for filename in os.listdir(directory):
    # print(filename)
    # print(directory+'\\'+filename)

    image = Image.open(directory+'\\'+filename)
    new_image = image.resize((64, 64))
    new_image.save(r'D:\_Test\End'+'\\'+filename)
    
    print(Fore.YELLOW + f'\r[+] Сохраняю: {round(counter*100/len(files), 2)}/{100}', end='')
    counter += 1

print("OK")
    



# 1080

# 1920

# 17
# 0.45
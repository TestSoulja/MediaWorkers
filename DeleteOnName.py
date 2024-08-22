import base64
import os

print("---------------------------------------------------------")
s = os.path.abspath(__file__)
c = s.replace(os.path.basename(os.path.abspath(__file__)), "")

def main():
    directory = r'C:\Users\super\YandexDisk\Разобрать\voice_messages'
    main = []
    counter = 0
    
    for filename in os.listdir(directory):
        
        if "thumb" in filename:
            f1 = os.path.join(directory, filename)
            main.append(f1)
            counter += 1
    
    for i in main:
        os.remove(i)
    
    print(counter)
    
main()

print("ok")
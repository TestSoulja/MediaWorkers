import base64
import os

print("---------------------------------------------------------")
s = os.path.abspath(__file__)
c = s.replace(os.path.basename(os.path.abspath(__file__)), "")

def main():
    counter = 0
    counternew = 0
    counter1 = 0
    directory = r'D:\YandexDisk\Kit\Photo'
    # directory = r'/Users/s.ekker/Yandex.Disk.localized/Bunny/Photo'
    main = []
    
    for filename in os.listdir(directory):
        counter1 += 1
    
    for filename in os.listdir(directory):
        counternew += 1
        print(str(round(counternew*100/counter1,1))+"/100  "+str(counter))
        lists = []
        f = os.path.join(directory, filename)

        if f not in main:
            with open(f, 'rb') as fa:
                data = fa.read()
        
            for filename in os.listdir(directory):
                f1 = os.path.join(directory, filename)

                with open(f1, 'rb') as fa1:
                    data1 = fa1.read()

                if data == data1 and f != f1:
                    lists.append(f1)
                    main.append(f1)
                
        for i in lists:
            if os.path.isfile(i) == True:
                counter += 1
            os.remove(i)


main()


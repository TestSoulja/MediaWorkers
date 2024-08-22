import moviepy.editor as moviepy
import os

s = os.path.abspath(__file__)
c = s.replace(os.path.basename(os.path.abspath(__file__)), '')

counter = 0

directory = c+ 'Enter'
for filename in os.listdir(directory):
    f = os.path.join(directory, filename)
    if os.path.isfile(f):
        clip = moviepy.VideoFileClip(c+"Enter/"+ filename)
        clip.write_videofile(c+"Exit/"+ str(counter)+".mp4")
        counter +=1
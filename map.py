'''
Copy and pasted from:
https://stackoverflow.com/questions/34902477/drawing-circles-on-image-with-matplotlib-and-numpy
'''
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle

image_file = './maps/map1.png'
img = plt.imread(image_file)

# Make some example data
x = np.random.rand(5)*img.shape[1]
y = np.random.rand(5)*img.shape[0]

# Create a figure. Equal aspect so circles look circular
fig, ax = plt.subplots(figsize=(10,6))
ax.set_aspect('equal')

# Show the image
ax.imshow(img)

# Now, loop through coord arrays, and create a circle at each x,y pair
for xx,yy in zip(x,y):
    circ = Circle((xx,yy),50)
    ax.add_patch(circ)

# Show the image
plt.show()
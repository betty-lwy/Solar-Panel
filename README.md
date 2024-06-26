# Solar-Panel

Boundary: We filtered the original building boundary shp file by only selecting the common type and calculating the centroid of each object. For all other codes that used the shp file, we will use the updated one.

Image info: We run a loop over the folder of a whole year's image, track down the information of each image and the houses we are going to crop out in the image, and then store all the information into one Excel file.

Houses Crop: We crop the houses within each image into a new folder

Completeness Check: We check if the images fully cover the whole area of toronto

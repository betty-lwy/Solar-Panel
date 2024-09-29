import os
import shutil
from tkinter import Tk, Label, Button, Frame
from PIL import Image, ImageTk


class ImageClassifier:
    def __init__(self, year_folders_dict, new_folders_dict):
        self.year_folders_dict = year_folders_dict  # Source folders where images currently are
        self.new_folders_dict = new_folders_dict    # Destination folders where images will be moved, including "no_change"
        self.houses = sorted({f.split('_')[1].split('.')[0] for f in os.listdir(list(year_folders_dict.values())[0]) if not f.startswith('.')})
        
        self.current_index = 0

        self.root = Tk()
        self.root.title("House Image Classifier")

        self.id_label = Label(self.root, text="")
        self.id_label.pack()  

        self.image_frame = Frame(self.root)
        self.image_frame.pack()

        # Create 8 labels for 8 years of images from the source year folders
        self.labels = [Label(self.image_frame) for _ in range(8)]
        for label in self.labels:
            label.pack(side="left", padx=10)

        self.buttons = []
        # Only create buttons for the actual years, skip 'no_change'
        for name, folder in self.new_folders_dict.items():
            if name != 'no_change':  # Skip the 'no_change' folder when creating buttons
                button = Button(self.root, text=name, command=lambda f=folder: self.move_images(f))
                button.pack(side="left")
                self.buttons.append(button)

        # Now add the "No Change" button separately
        no_change_button = Button(self.root, text="No Change", command=self.no_change)
        no_change_button.pack(side="left")
        self.buttons.append(no_change_button)

        self.current_images = []
        self.show_images()

    def show_images(self):
        if self.current_index < len(self.houses):
            house_id = self.houses[self.current_index]
            self.id_label.config(text=f"House ID: {house_id}")
            for i, (year, folder) in enumerate(self.year_folders_dict.items()):
                image_path = os.path.join(folder, f'house_{house_id}.jpg')
                try:
                    image = Image.open(image_path)
                    image.thumbnail((160, 120))
                    self.current_images.append(ImageTk.PhotoImage(image))
                    self.labels[i].config(image=self.current_images[-1])
                except Exception as e:
                    print(f"Error opening image {image_path}: {e}")
                    self.labels[i].config(image='')
        else:
            self.id_label.config(text="No more houses to process.")
            for button in self.buttons:
                button.config(state="disabled")

    def move_images(self, folder):
        if self.current_index < len(self.houses):
            house_id = self.houses[self.current_index]
            for year, year_folder in self.year_folders_dict.items():
                image_name = f'house_{house_id}.jpg'
                image_path = os.path.join(year_folder, image_name)
                destination_path = os.path.join(folder, image_name)
                
                # If the destination file exists, overwrite it
                if os.path.exists(destination_path):
                    os.remove(destination_path)  # Remove the existing file
                
                if os.path.exists(image_path):
                    shutil.move(image_path, folder)  # Move image from year_folders_dict to selected folder in new_folders_dict
                
            self.current_index += 1
            self.show_images()

    def no_change(self):
        # Move images to the "no_change" folder
        if 'no_change' in self.new_folders_dict:
            self.move_images(self.new_folders_dict['no_change'])
        else:
            print("No 'no_change' folder found.")
        self.show_images()

    def on_closing(self):
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == '__main__':
    year_folders_dict = {
        '2011': './Pic_Output/2011/',
        '2012': './Pic_Output/2012/',
        '2013': './Pic_Output/2013/',
        '2014': './Pic_Output/2014/',
        '2015': './Pic_Output/2015/',
        '2016': './Pic_Output/2016/',
        '2017': './Pic_Output/2017/',
        '2018': './Pic_Output/2018/'
    }

    new_folders_dict = {
        '2011': './New_Pics/2011/',
        '2012': './New_Pics/2012/',
        '2013': './New_Pics/2013/',
        '2014': './New_Pics/2014/',
        '2015': './New_Pics/2015/',
        '2016': './New_Pics/2016/',
        '2017': './New_Pics/2017/',
        '2018': './New_Pics/2018/',
        'no_change': './New_Pics/no_change/'  # No Change folder
    }

    classifier = ImageClassifier(year_folders_dict, new_folders_dict)
    classifier.run()


    ## Only picture of year 2018 was moved, since one can easily finds its source by house id.


import os
import pandas as pd
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import ttk, messagebox

class ImageClassifierApp:
    def __init__(self, root, excel_path, image_base_folder, output_excel):
        self.root = root
        self.excel_path = excel_path
        self.image_base_folder = image_base_folder
        self.output_excel = output_excel
        
        # Load and clean Excel data
        if os.path.exists(output_excel):
            self.df = pd.read_excel(output_excel, index_col=0)
        else:
            self.df = pd.read_excel(excel_path, index_col=0)
        
        # Data cleaning steps
        # 1. Remove completely empty rows
        # 2. Remove rows with empty index
        # 3. Convert index to string
        self.df = self.df.dropna(how='all')  # Drop rows where all columns are empty
        self.df = self.df[self.df.index.notna()]  # Remove rows with missing index
        self.df.index = self.df.index.astype(str)  # Convert house_id to string
        
        # Check for duplicate indices
        if self.df.index.duplicated().any():
            messagebox.showwarning("Data Warning", 
                                "Duplicate house IDs found. Only the first occurrence will be used.")
            self.df = self.df[~self.df.index.duplicated(keep='first')]
        
        self.original_df = self.df.copy()
        
        # Find all S markers and create queue
        self.queue = []
        self.history = []
        for house_id in self.df.index:
            for year in self.df.columns:
                if pd.notna(self.df.loc[house_id, year]) and self.df.loc[house_id, year] == 'S':
                    self.queue.append((house_id, year))
        
        # GUI Setup
        self.root.title("House Image Classifier")
        self.current_index = 0
        
        # Image display
        self.img_label = ttk.Label(root)
        self.img_label.pack(pady=10)
        
        # Info label
        self.info_label = ttk.Label(root, text="", font=('Arial', 12))
        self.info_label.pack(pady=5)
        
        # Classification buttons
        btn_frame = ttk.Frame(root)
        btn_frame.pack(pady=10)
        
        self.yes_btn = ttk.Button(btn_frame, text="Yes (House)", command=self.mark_house)
        self.no_btn = ttk.Button(btn_frame, text="No (Non-house)", command=self.mark_non_house)
        self.yes_btn.pack(side=tk.LEFT, padx=5)
        self.no_btn.pack(side=tk.LEFT, padx=5)
        
        # Navigation button
        nav_frame = ttk.Frame(root)
        nav_frame.pack(pady=10)
        
        self.last_btn = ttk.Button(nav_frame, text="Last One", command=self.show_previous)
        self.last_btn.pack(side=tk.LEFT, padx=5)
        
        # Start with first image
        self.show_current_image()
        
        # Handle window closing
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def get_image_path(self, house_id, year):
        """Construct image path using house_id and year"""
        return os.path.join(self.image_base_folder, str(year), house_id)

    def show_current_image(self):
        if self.current_index < len(self.queue):
            house_id, year = self.queue[self.current_index]
            img_path = self.get_image_path(house_id, year)
            
            if os.path.exists(img_path):
                try:
                    img = Image.open(img_path)
                    img = img.resize((400, 400), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    self.img_label.config(image=photo)
                    self.img_label.image = photo
                    self.info_label.config(text=f"House ID: {house_id} | Year: {year}")
                except Exception as e:
                    messagebox.showerror("Image Error", f"Failed to open image: {e}")
                    self.current_index += 1
                    self.show_current_image()
            else:
                messagebox.showwarning("Missing Image", f"Image not found: {img_path}")
                self.current_index += 1
                self.show_current_image()
        else:
            self.save_and_exit()

    def mark_house(self):
        self.update_classification('H')

    def mark_non_house(self):
        self.update_classification('A')

    def update_classification(self, classification):
        house_id, year = self.queue[self.current_index]
        self.df.at[house_id, year] = classification
        self.history.append(self.current_index)
        self.current_index += 1
        self.show_current_image()

    def show_previous(self):
        if self.history:
            prev_index = self.history.pop()
            house_id, year = self.queue[prev_index]
            self.df.at[house_id, year] = 'S'
            self.current_index = prev_index
            self.show_current_image()

    def save_and_exit(self):
        """Handle final save before exiting"""
        if not self.df.equals(self.original_df):
            try:
                output_dir = os.path.dirname(self.output_excel)
                if output_dir:  # Only create directories if path contains a directory
                    os.makedirs(output_dir, exist_ok=True)
                self.df.to_excel(self.output_excel)
                messagebox.showinfo("Saved", f"Progress saved to {self.output_excel}")
            except Exception as e:
                messagebox.showerror("Save Error", f"Failed to save results: {e}")
        self.root.destroy()

    def on_closing(self):
        if self.current_index < len(self.queue):
            self.save_and_exit()
        else:
            self.root.destroy()

if __name__ == "__main__":
    # Configuration - modify these paths as needed
    EXCEL_PATH = "Claire_pretrain.xlsx"
    IMAGE_BASE_FOLDER = "./Claire/" 
    OUTPUT_EXCEL = EXCEL_PATH  # Save results back to original file

    root = tk.Tk()
    app = ImageClassifierApp(root, EXCEL_PATH, IMAGE_BASE_FOLDER, OUTPUT_EXCEL)
    root.mainloop()
import os
import pandas as pd
from tkinter import Tk, Label, Button, Frame, Toplevel
from PIL import Image, ImageTk, ImageDraw, ImageFont

class ImageClassifier:
    def __init__(self, input_csv, output_csv, image_folder):
        self.input_csv = input_csv
        self.output_csv = output_csv
        self.image_folder = image_folder

        self.year_button_default_fg = "black"
        self.year_button_selected_fg = "blue" # Color for selected 'C' year buttons

        try:
            self.df = pd.read_csv(input_csv)
        except FileNotFoundError:
            print(f"Error: Input CSV file '{input_csv}' not found. Please create it or check path.")
            self.df = pd.DataFrame(columns=['image_filename'] + [str(y) for y in range(2011, 2023)] + ['Check'])
        except pd.errors.EmptyDataError:
            print(f"Error: Input CSV file '{input_csv}' is empty.")
            self.df = pd.DataFrame(columns=['image_filename'] + [str(y) for y in range(2011, 2023)] + ['Check'])

        if 'Check' not in self.df.columns and not self.df.empty:
            self.df['Check'] = False
        elif 'Check' in self.df.columns:
            if not pd.api.types.is_bool_dtype(self.df['Check']):
                bool_map = {
                    'True': True, 'False': False, 'true': True, 'false': False,
                    '1': True, '0': False, 1: True, 0: False,
                    'TRUE': True, 'FALSE': False,
                    't': True, 'f': False, 'T': True, 'F': False
                }
                self.df['Check'] = self.df['Check'].astype(str).map(bool_map).fillna(False).astype(bool)
            else:
                self.df['Check'] = self.df['Check'].astype(bool)
        elif self.df.empty and 'Check' not in self.df.columns:
             self.df['Check'] = pd.Series(dtype='bool')

        false_indices = []
        if not self.df.empty:
            false_indices = self.df.index[(self.df['Check'] == False) | pd.isna(self.df['Check'])].tolist()
        self.current_index = false_indices[0] if false_indices else 0
        
        if not false_indices and not self.df.empty:
            print("All images appear to be checked. Displaying from the beginning.")

        self.years = [str(year) for year in range(2011, 2023)]
        self.zoomed_windows = {}
        self.selected_years_for_c = set() # To store years selected to be changed to 'C'

        self.root = Tk()
        self.root.title("House Image Classifier")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        screen_width = self.root.winfo_screenwidth()
        # Target width for each thumbnail, attempting to fit on screen but capped.
        calculated_width_for_image = (screen_width - 100) // len(self.years) if len(self.years) > 0 else 50
        self.image_width = min(100, max(50, calculated_width_for_image))

        self.main_frame = Frame(self.root)
        self.main_frame.pack(padx=10, pady=10, fill="both", expand=True)

        self.id_label = Label(self.main_frame, text="", font=("Arial", 12, "bold"))
        self.id_label.pack(pady=(5,10))

        self.image_frame = Frame(self.main_frame)
        self.image_frame.pack(pady=5) 

        self.year_frames = []
        self.labels = []
        self.status_labels = []
        self.original_images = [] 

        for _ in self.years:
            year_frame = Frame(self.image_frame) 
            year_frame.pack(side="left", padx=3, anchor="n")
            self.year_frames.append(year_frame)
            image_label = Label(year_frame)
            image_label.pack()
            self.labels.append(image_label)
            status_label = Label(year_frame, text="", font=("Arial", 9, "normal"))
            status_label.pack(pady=(2,0))
            self.status_labels.append(status_label)

        self.ha_button_frame = Frame(self.main_frame)
        self.ha_button_frame.pack(pady=(5, 0))
        self.ha_buttons = []
        for i, _ in enumerate(self.years):
            button = Button(self.ha_button_frame, text="", width=4, 
                          command=lambda idx=i: self.toggle_ha_status(idx))
            button.pack(side="left", padx=3)
            self.ha_buttons.append(button)

        self.action_button_frame = Frame(self.main_frame) 
        self.action_button_frame.pack(pady=(5, 10))

        self.last_button = Button(self.action_button_frame, text="< Last", command=self.go_to_last, width=8)
        self.last_button.pack(side="left", padx=10)

        self.change_to_c_buttons = [] 
        for i, year_str_val in enumerate(self.years): # Iterate with index for mapping to button list
            button = Button(self.action_button_frame, text=year_str_val, 
                            # Pass the button index and year string to the command
                            command=lambda year_val=year_str_val, btn_idx=i: self.select_year_for_c_change(year_val, btn_idx), 
                            width=5) 
            button.pack(side="left", padx=2)
            self.change_to_c_buttons.append(button)

        self.next_button = Button(self.action_button_frame, text="Next >", command=self.go_to_next, width=8)
        self.next_button.pack(side="left", padx=10)

        self.current_images_tk = []

        if not self.df.empty:
            self.show_images()
        else:
            self.id_label.config(text="No data in CSV or CSV is empty/not found.")
            self.disable_all_controls()
        
        self.root.update_idletasks()

    def disable_all_controls(self):
        if hasattr(self, 'last_button'): self.last_button.config(state="disabled")
        if hasattr(self, 'next_button'): self.next_button.config(state="disabled")
        if hasattr(self, 'ha_buttons'):
            for btn in self.ha_buttons: btn.config(state="disabled")
        if hasattr(self, 'change_to_c_buttons'):
            for btn in self.change_to_c_buttons: btn.config(state="disabled", relief="raised", fg=self.year_button_default_fg)
        if hasattr(self, 'labels'):
            for label in self.labels: label.config(image='', text="N/A")
        if hasattr(self, 'status_labels'):
            for slabel in self.status_labels: slabel.config(text="")

    def on_closing(self):
        print("Closing application...")
        # Current model saves frequently or on Next/Last.
        # No explicit save here unless a final check is desired.
        for year_key in list(self.zoomed_windows.keys()):
            self.close_zoomed_window(year_key)
        self.root.destroy()

    def _save_df_to_csv_internal(self):
        if not hasattr(self, 'df') or self.df.empty:
            print("Internal Save: DataFrame is empty or not initialized. Nothing to save.")
            return False
        if 0 <= self.current_index < len(self.df):
            for y_col in self.years:
                current_val = self.df.loc[self.current_index, y_col]
                if pd.isna(current_val) or str(current_val).strip().upper() not in ['H', 'A', 'C']:
                    self.df.loc[self.current_index, y_col] = 'A'
        try:
            self.df.to_csv(self.output_csv, index=False)
            return True
        except Exception as e:
            print(f"Error saving DataFrame to {self.output_csv}: {e}")
            return False

    def show_zoomed_image(self, pil_image, year_str, image_filename_str):
        if pil_image is None:
            print(f"Cannot zoom, original image for {year_str} - {image_filename_str} is missing.")
            return
        if year_str in self.zoomed_windows:
             self.close_zoomed_window(year_str)
        zoom_window = Toplevel(self.root)
        zoom_window.title(f"Zoomed Image - {year_str} - {image_filename_str}")
        screen_width_zw = zoom_window.winfo_screenwidth()
        screen_height_zw = zoom_window.winfo_screenheight()
        img_width, img_height = pil_image.size
        aspect_ratio = img_width / img_height if img_height != 0 else 1
        zoomed_width = int(min(screen_width_zw * 0.8, img_width * 3))
        zoomed_height = int(zoomed_width / aspect_ratio) if aspect_ratio != 0 else int(screen_height_zw * 0.8)
        if zoomed_height > screen_height_zw * 0.8:
            zoomed_height = int(screen_height_zw * 0.8)
            zoomed_width = int(zoomed_height * aspect_ratio)
        final_zoomed_width = max(1, zoomed_width)
        final_zoomed_height = max(1, zoomed_height)
        try:
            resized_image = pil_image.resize((final_zoomed_width, final_zoomed_height), Image.Resampling.LANCZOS)
            zoomed_photo = ImageTk.PhotoImage(resized_image)
            zoom_label = Label(zoom_window, image=zoomed_photo)
            zoom_label.image = zoomed_photo
            zoom_label.pack(padx=10, pady=10)
            zoom_label.bind('<Button-1>', lambda e, y=year_str: self.close_zoomed_window(y))
            self.zoomed_windows[year_str] = zoom_window
            zoom_window.update_idletasks()
            x_pos = (screen_width_zw - zoom_window.winfo_width()) // 2
            y_pos = (screen_height_zw - zoom_window.winfo_height()) // 2
            zoom_window.geometry(f'+{x_pos}+{y_pos}')
        except Exception as e_zoom:
            print(f"Error creating zoomed image display for {image_filename_str} - {year_str}: {e_zoom}")
            if year_str in self.zoomed_windows:
                self.zoomed_windows[year_str].destroy()
                del self.zoomed_windows[year_str]

    def close_zoomed_window(self, year_str):
        if year_str in self.zoomed_windows:
            window_to_close = self.zoomed_windows.pop(year_str)
            window_to_close.destroy()

    def _update_ui_for_current_row(self):
        if not(0 <= self.current_index < len(self.df)):
            self.disable_all_controls()
            return
        current_row_data = self.df.loc[self.current_index]
        statuses = [str(current_row_data.get(year, 'A')) for year in self.years]
        for i, year_col in enumerate(self.years):
            status = statuses[i]
            if i < len(self.ha_buttons):
                self.ha_buttons[i].config(text=status if status in ['H', 'A', 'C'] else 'A')
            if i < len(self.status_labels):
                 self.status_labels[i].config(text=f"{year_col}\n{status if status in ['H', 'A', 'C'] else 'A'}")
        self._update_status_colors()
        self._update_action_button_states()

    def _update_status_colors(self):
        if not(0 <= self.current_index < len(self.df)): return
        current_row_data = self.df.loc[self.current_index]
        statuses = [str(current_row_data.get(year, 'A')) for year in self.years]
        red_indices = set()
        if len(statuses) > 1:
            for i in range(1, len(statuses)):
                if statuses[i] != statuses[i-1]:
                    red_indices.add(i)
                    red_indices.add(i-1)
        for i in range(len(self.years)):
            if i < len(self.status_labels):
                color = 'red' if i in red_indices else 'black'
                self.status_labels[i].config(fg=color)

    def _update_action_button_states(self):
        if not(0 <= self.current_index < len(self.df)):
            self.disable_all_controls()
            return
        current_row_data = self.df.loc[self.current_index]
        for i, year_col in enumerate(self.years):
            if i < len(self.change_to_c_buttons):
                button = self.change_to_c_buttons[i]
                is_selected_for_c = year_col in self.selected_years_for_c
                
                # Determine if button should be enabled based on H/H logic
                can_be_c = False
                if i == 0: # First year's 'C' button generally disabled unless specific logic allows
                    can_be_c = False # As per user's previous logic, first 'C' button disabled
                else:
                    prev_status = str(current_row_data.get(self.years[i-1], 'A'))
                    curr_status = str(current_row_data.get(year_col, 'A'))
                    if prev_status == 'H' and curr_status == 'H':
                        can_be_c = True
                
                if can_be_c:
                    button.config(state="normal")
                    if is_selected_for_c:
                        button.config(relief="sunken", fg=self.year_button_selected_fg)
                    else:
                        button.config(relief="raised", fg=self.year_button_default_fg)
                else: # Cannot be 'C'
                    button.config(state="disabled", relief="raised", fg=self.year_button_default_fg)
                    if is_selected_for_c: # If it was selected but now logic disables it, remove from selection
                        self.selected_years_for_c.remove(year_col)
        
        self.last_button.config(state="normal" if self.current_index > 0 else "disabled")
        # Next button logic: if on last image, enable only if 'C's are selected
        if self.current_index >= len(self.df) - 1:
            self.next_button.config(state="normal" if self.selected_years_for_c else "disabled")
        else:
            self.next_button.config(state="normal")

    def toggle_ha_status(self, index_in_years_list):
        if not(0 <= self.current_index < len(self.df)): return
        year_to_toggle = self.years[index_in_years_list]
        current_status = str(self.df.loc[self.current_index, year_to_toggle])
        new_status = 'A'
        if current_status.upper() == 'H': new_status = 'A'
        elif current_status.upper() == 'A': new_status = 'H'
        self.df.loc[self.current_index, year_to_toggle] = new_status
        self._save_df_to_csv_internal() 
        self._update_ui_for_current_row()

    def show_images(self):
        if not(0 <= self.current_index < len(self.df)):
            self.id_label.config(text="All houses processed or index out of bounds.")
            self.disable_all_controls()
            return

        current_row_data = self.df.loc[self.current_index]
        image_filename = str(current_row_data.iloc[0])
        self.id_label.config(text=f"Image ID: {image_filename} (Row: {self.current_index + 1}/{len(self.df)})")

        self.current_images_tk.clear()
        self.original_images.clear()
        self.selected_years_for_c.clear() # Clear 'C' selections for new row

        for i, year_col in enumerate(self.years):
            status = str(current_row_data.get(year_col, 'A'))
            if status.upper() not in ['H', 'A', 'C']:
                status = 'A'
                self.df.loc[self.current_index, year_col] = status
            image_path = os.path.join(self.image_folder, year_col, image_filename)
            try:
                img_pil = Image.open(image_path)
                self.original_images.append(img_pil.copy())
                thumb_img = img_pil.copy()
                aspect_ratio = thumb_img.width / thumb_img.height if thumb_img.height != 0 else 1
                new_width = self.image_width
                new_height = int(new_width / aspect_ratio) if aspect_ratio != 0 else self.image_width
                thumb_img.thumbnail((new_width, max(1, new_height)), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(thumb_img)
                self.current_images_tk.append(photo)
                if i < len(self.labels):
                    self.labels[i].config(image=photo)
                    self.labels[i].image = photo
                    self.labels[i].unbind('<Button-1>')
                    self.labels[i].bind('<Button-1>', 
                        lambda e, y=year_col, idx=len(self.original_images)-1, fn=image_filename: \
                        self.show_zoomed_image(self.original_images[idx] if idx < len(self.original_images) else None, y, fn))
            except FileNotFoundError:
                if i < len(self.labels): self.labels[i].config(image='', text="No Image")
                self.original_images.append(None)
            except Exception as e:
                print(f"Error opening image {image_path}: {e}")
                if i < len(self.labels): self.labels[i].config(image='', text="Error")
                self.original_images.append(None)
        self._update_ui_for_current_row()

    def select_year_for_c_change(self, year_str_value, button_index):
        """Toggles selection of a year to be changed to 'C'."""
        if not(0 <= self.current_index < len(self.df)): return
        if button_index >= len(self.change_to_c_buttons): return

        button = self.change_to_c_buttons[button_index]
        # Only allow selection if the button is enabled (which means H/H condition was met)
        if button.cget("state") == "disabled":
            return

        if year_str_value in self.selected_years_for_c:
            self.selected_years_for_c.remove(year_str_value)
            button.config(relief="raised", fg=self.year_button_default_fg)
        else:
            self.selected_years_for_c.add(year_str_value)
            button.config(relief="sunken", fg=self.year_button_selected_fg)
        
        self._update_action_button_states() # Update Next button state if on last image

    def go_to_last(self):
        if self.current_index > 0:
            if 0 <= self.current_index < len(self.df):
                self.df.loc[self.current_index, 'Check'] = False # Mark current as unchecked
                self._save_df_to_csv_internal() 
            
            for year_key in list(self.zoomed_windows.keys()):
                self.close_zoomed_window(year_key)
            
            self.current_index -= 1
            try: # Reload CSV to reflect saved state and potentially revert other unsaved changes
                self.df = pd.read_csv(self.input_csv)
                if 'Check' not in self.df.columns: self.df['Check'] = False
                if 'Check' in self.df.columns: # Re-apply robust boolean conversion
                    if not pd.api.types.is_bool_dtype(self.df['Check']):
                        bool_map = {'True': True, 'False': False, 'true': True, 'false': False,'1': True, '0': False, 1: True, 0: False, 'T':True, 'F':False}
                        self.df['Check'] = self.df['Check'].astype(str).map(bool_map).fillna(False).astype(bool)
                    else: self.df['Check'] = self.df['Check'].astype(bool)
            except Exception as e:
                print(f"Error reloading CSV in go_to_last: {e}")
            self.show_images()

    def go_to_next(self):
        if not(0 <= self.current_index < len(self.df)): return

        # Apply 'C' changes if any years were selected
        if self.selected_years_for_c:
            for year_to_change_to_c in self.selected_years_for_c:
                self.df.loc[self.current_index, year_to_change_to_c] = 'C'
            self.selected_years_for_c.clear() # Clear selections after applying

        self.df.loc[self.current_index, 'Check'] = True # Mark current row as checked
        self._save_df_to_csv_internal()

        for year_key in list(self.zoomed_windows.keys()):
            self.close_zoomed_window(year_key)

        if self.current_index < len(self.df) - 1:
            self.current_index += 1
            self.show_images()
        else:
            self.show_images() 
            self.id_label.config(text=f"Image ID: {self.df.iloc[self.current_index].iloc[0]} (Row: {self.current_index + 1}/{len(self.df)}) - All processed or at end.")
            # Next button state will be updated by _update_action_button_states called in show_images

    def run(self):
        self.root.mainloop()

if __name__ == '__main__':
    INPUT_CSV_FILE = 'input_test.csv'
    IMAGE_BASE_FOLDER = './image/' 

    if not os.path.exists(INPUT_CSV_FILE) or os.path.getsize(INPUT_CSV_FILE) == 0 :
        print(f"CRITICAL ERROR: Input CSV '{INPUT_CSV_FILE}' is missing or empty. Application cannot start.")
        error_root = Tk()
        error_root.withdraw()
        from tkinter import messagebox
        messagebox.showerror("Startup Error", 
                             f"Input CSV file '{INPUT_CSV_FILE}' is missing or empty.\n"
                             "Please create it and ensure it has data, then restart the application.")
        error_root.destroy()
    else:
        classifier = ImageClassifier(input_csv=INPUT_CSV_FILE,
                                     output_csv=INPUT_CSV_FILE,
                                     image_folder=IMAGE_BASE_FOLDER)
        classifier.run()
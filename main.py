import os
from operator import attrgetter
# tkinter-related imports
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import filedialog
from PIL import ImageTk, Image
from tooltip import create_tooltip
# raw_handler-related imports
from raw_handler import Mod
from raw_handler import Compiler


def select_from_non_selected_mods(*args):
    current_selection = non_selected_mods_listbox.curselection()
    # if the event was due to the listbox being unselected (and thus len(current_selection) not being 1), ignores it
    if len(current_selection) == 1:
        mod = non_selected_mods[current_selection[0]]
        update_mod_info_box(mod)
        select_unselect_button.configure(command=select_button_command, text="Select mod \u21D2", state='normal')


def select_from_selected_mods(*args):
    current_selection = selected_mods_listbox.curselection()
    # if the event was due to the listbox being unselected (and thus len(current_selection) not being 1), ignores it
    if len(current_selection) == 1:
        mod = selected_mods[current_selection[0]]
        update_mod_info_box(mod)

        select_unselect_button.configure(command=unselect_button_command, text="\u21D0 Unselect mod", state='normal')


def update_mod_info_box(mod):
    # updates the text
    mod_info_text.configure(state='normal')
    mod_info_text.delete('1.0', tk.END)

    mod_info_text.insert('1.0',
                         mod.name + "\n" +
                         mod.version + "\n" +
                         "By " + mod.creator + "\n" +
                         "For DF " + mod.df_version + "\n" +
                         "----- " + "\n" +
                         mod.description_string + "\r" +
                         "----- " + "\n" +
                         mod.dependencies_string)

    if mod in missing_mods:
        mod_info_text.insert('1.0',
                             "ATTENTION! This mod is seemingly missing from your mods folder.\n"
                             "=====\n")

    mod_info_text.configure(state='disabled')


def update_selected_mods_listbox():
    # populates the selected_mods listbox
    selected_mods_listvar = tk.StringVar(value=[mod.name + " " + mod.version for mod in selected_mods])
    selected_mods_listbox.configure(listvariable=selected_mods_listvar)

    # marks missing mods
    for i in range(len(selected_mods)):
        if selected_mods[i] in missing_mods:
            selected_mods_listbox.itemconfigure(i, background='red')
        else:
            selected_mods_listbox.itemconfigure(i, background='white')


def update_non_selected_mods_listbox():
    non_selected_mods_listvar = tk.StringVar(value=[mod.name + " " + mod.version for mod in non_selected_mods])
    non_selected_mods_listbox.configure(listvariable=non_selected_mods_listvar)

    # marks missing mods
    for i in range(len(non_selected_mods)):
        if non_selected_mods[i] in missing_mods:
            non_selected_mods_listbox.itemconfigure(i, background='red')
        else:
            non_selected_mods_listbox.itemconfigure(i, background='white')


def load_mods_folder():
    global mods, non_selected_mods, missing_mods

    new_mods = []
    # finds the mods
    for mod_directory in os.scandir(os.getcwd() + "\\mods"):
        try:
            open(mod_directory.path + "\\mod_info.txt", "r", encoding="latin1")
        except FileNotFoundError:
            print(mod_directory.path + " is not a valid mod - it lacks mod_info.txt")
        else:
            mod_info_file = open(mod_directory.path + "\\mod_info.txt", "r", encoding="latin1")
            # populates a Mod object with what's in the mod_info_file, and appends it to the mods list
            mod_name = mod_info_file.readline().replace("name:", "").replace("\n", "")
            mod_version = mod_info_file.readline().replace("version:", "").replace("\n", "")
            # already loaded mods are made to keep their object IDs (so other parts of the code can work)
            is_old_mod = False
            for old_mod in mods:
                if (mod_name, mod_version) == (old_mod.name, old_mod.version):
                    is_old_mod = True
                    old_mod.creator = mod_info_file.readline().replace("creator:", "").replace("\n", "")
                    old_mod.df_version = mod_info_file.readline().replace("df_version:", "").replace("\n", "")
                    old_mod.description_string = mod_info_file.readline().replace("description_string:", "")
                    old_mod.dependencies_string = mod_info_file.readline().replace("dependencies_string:", "")
                    old_mod.path = mod_directory.path
                    new_mods.append(old_mod)
            if not is_old_mod:
                mod_creator = mod_info_file.readline().replace("creator:", "").replace("\n", "")
                mod_df_version = mod_info_file.readline().replace("df_version:", "").replace("\n", "")
                mod_description_string = mod_info_file.readline().replace("description_string:", "")
                mod_dependencies_string = mod_info_file.readline().replace("dependencies_string:", "")
                new_mods.append(Mod(name=mod_name, version=mod_version, creator=mod_creator, df_version=mod_df_version,
                                description_string=mod_description_string, dependencies_string=mod_dependencies_string,
                                path=mod_directory.path))

    # old mods that were not loaded now must be missing
    missing_mods = []
    for old_mod in mods:
        if old_mod not in new_mods and old_mod not in missing_mods:
            missing_mods.append(old_mod)
            new_mods.append(old_mod)
    # and replaces the old mods with the new
    mods = new_mods

    # populates the non_selected_mods and sorts them alphabetically
    non_selected_mods = [mod for mod in mods if mod not in selected_mods]
    non_selected_mods.sort(key=attrgetter('name'))

    # updates/populates the listboxes
    update_non_selected_mods_listbox()
    update_selected_mods_listbox()


# ====== Widget commands ===============================================================================================

def modloader_help_button_command():
    messagebox.showinfo(message='DF Modloader mockup\nVoliol 2021\n'
                                'This is a mockup I made for a mod loader for Dwarf Fortress. ' 
                                'It reads mods from a folder, and compiles them. There are also some additional '
                                'functionality/tokens, see the reddit/forum post where you probably found this. '
                                '\nDue to a lack of time, I will not be maintaining or continuing this project'
                                'any time soon. '
                                'The source code is available for anyone to use or edit, if they feel like picking '
                                'it up.'
                                '\nCompiled mods are put in the output folder.',
                        title="Help - DF Modloader mockup")


def select_button_command():
    mod_index = non_selected_mods_listbox.curselection()[0]
    selected_mods.append(non_selected_mods.pop(mod_index))
    update_selected_mods_listbox()
    update_non_selected_mods_listbox()

    # disables the select_unselect_button
    if mod_index >= len(non_selected_mods):
        select_unselect_button.configure(state='disabled')


def unselect_button_command():
    mod_index = selected_mods_listbox.curselection()[0]
    non_selected_mods.append(selected_mods.pop(mod_index))
    # sorts the non_selected_mods alphabetically by name
    non_selected_mods.sort(key=attrgetter('name'))
    update_selected_mods_listbox()
    update_non_selected_mods_listbox()

    # disables the select_unselect_button
    if mod_index >= len(selected_mods):
        select_unselect_button.configure(state='disabled')


def move_up_button_command():
    mod_index = selected_mods_listbox.curselection()[0]
    if mod_index != 0:
        # moves the selected mod upwards
        selected_mods.insert(mod_index - 1, selected_mods.pop(mod_index))
        update_selected_mods_listbox()
        # and updates the selection (so it follows the mod)
        selected_mods_listbox.selection_clear(0, len(selected_mods))
        selected_mods_listbox.selection_set(mod_index - 1)
        selected_mods_listbox.yview_scroll(-1, 'units')


def move_down_button_command():
    mod_index = selected_mods_listbox.curselection()[0]
    if mod_index != len(selected_mods) - 1:
        # moves the selected mod downwards
        selected_mods.insert(mod_index + 1, selected_mods.pop(mod_index))
        update_selected_mods_listbox()
        # and updates the selection (so it follows the mod)
        selected_mods_listbox.selection_clear(0, len(selected_mods))
        selected_mods_listbox.selection_set(mod_index + 1)
        selected_mods_listbox.yview_scroll(1, 'units')


def move_to_top_button_command():
    mod_index = selected_mods_listbox.curselection()[0]
    if mod_index != 0:
        # moves the selected mod to the top
        selected_mods.insert(0, selected_mods.pop(mod_index))
        update_selected_mods_listbox()
        # and updates the selection (so it follows the mod)
        selected_mods_listbox.selection_clear(0, len(selected_mods))
        selected_mods_listbox.selection_set(0)
        selected_mods_listbox.yview_moveto(0)


def move_to_bottom_button_command():
    mod_index = selected_mods_listbox.curselection()[0]
    if mod_index != len(selected_mods) - 1:
        # moves the selected mod downwards
        selected_mods.insert(len(selected_mods) - 1, selected_mods.pop(mod_index))
        update_selected_mods_listbox()
        # and updates the selection (so it follows the mod)
        selected_mods_listbox.selection_clear(0, len(selected_mods))
        selected_mods_listbox.selection_set(len(selected_mods) - 1)
        selected_mods_listbox.yview_moveto(len(selected_mods) - 1)


def open_mods_folder_button_command():
    os.startfile(os.getcwd() + "\\mods")


def reload_mods_folder_button_command():
    load_mods_folder()


def change_output_folder_button_command():
    global output_path
    output_path = filedialog.askdirectory()
    # updates the tooltip
    create_tooltip(change_output_folder_button, text=output_path)


def compile_button_command():
    print("Compiling started...")
    compiler = Compiler()
    compiler.compile_mods(selected_mods, output_path)
    print("Compiling completed! Look in your output folder!")


# ======================================================================================================================

# initializes the root window
root = tk.Tk()
root.title("DF Modloader")
root.iconbitmap(os.getcwd() + "//icon.ico")

# creates a mainframe+grid within the root
mainframe = ttk.Frame(root, padding="3 3 12 12")
mainframe.grid(column=0, row=0, sticky=(tk.N, tk.W, tk.E, tk.S))
root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=1)

# --- Mod list frame ---------------------------------------------------------------------------------------------------
mod_list_frame = ttk.Frame(mainframe, relief='sunken', borderwidth=5)
mod_list_frame.grid(column=0, row=0, columnspan=2, padx=5, pady=5)

# labels for mod lists
non_selected_mods_label = ttk.Label(mod_list_frame, text="Non-selected mods:")
non_selected_mods_label.grid(column=1, row=0, columnspan=2)
selected_mods_label = tk.Label(mod_list_frame, text="Selected mods:")
selected_mods_label.grid(column=5, row=0)

# listbox for the non-selected mods
non_selected_mods_listbox = tk.Listbox(mod_list_frame, height=15, width=50)
non_selected_mods_listbox.grid(column=1, row=1, rowspan=5, columnspan=2)
non_selected_mods_listbox.bind('<<ListboxSelect>>', select_from_non_selected_mods)

non_selected_mods_scrollbar = tk.Scrollbar(mod_list_frame, orient=tk.VERTICAL, command=non_selected_mods_listbox.yview)
non_selected_mods_listbox.configure(yscrollcommand=non_selected_mods_scrollbar.set)
non_selected_mods_scrollbar.grid(column=0, row=1, rowspan=5)

# buttons for moving the selected mod around
select_unselect_button = tk.Button(mod_list_frame, text="Select mod \u21D2", state='disabled')
select_unselect_button.grid(column=3, row=1, sticky=tk.S)
move_up_button = tk.Button(mod_list_frame, text="\u2191 Move up \u2191", command=move_up_button_command)
move_up_button.grid(column=3, row=3, sticky=tk.S)
move_down_button = tk.Button(mod_list_frame, text="\u2193 Move down \u2193", command=move_down_button_command)
move_down_button.grid(column=3, row=4, sticky=tk.N)
move_to_top_button = tk.Button(mod_list_frame, text="\u21C8 Move to top \u21C8", command=move_to_top_button_command)
move_to_top_button.grid(column=3, row=2, sticky=tk.S)
move_to_bottom_button = tk.Button(mod_list_frame, text="\u21CA Move to bottom \u21CA",
                                  command=move_to_bottom_button_command)
move_to_bottom_button.grid(column=3, row=5, sticky=tk.N)

# listbox for the selected mods
selected_mods_listbox = tk.Listbox(mod_list_frame, height=15, width=50)
selected_mods_listbox.grid(column=5, row=1, rowspan=5)
selected_mods_listbox.bind('<<ListboxSelect>>', select_from_selected_mods)

selected_mods_scrollbar = tk.Scrollbar(mod_list_frame, orient=tk.VERTICAL, command=selected_mods_listbox.yview)
selected_mods_listbox.configure(yscrollcommand=selected_mods_scrollbar.set)
selected_mods_scrollbar.grid(column=6, row=1, rowspan=5)

# button for opening the mods folder
open_mods_folder_button = tk.Button(mod_list_frame, text="Open mods folder", command=open_mods_folder_button_command)
open_mods_folder_button.grid(column=1, row=6)

# button for reloading the mods folder
reload_mods_folder_button = tk.Button(mod_list_frame, text="Reload mods folder",
                                      command=reload_mods_folder_button_command)
reload_mods_folder_button.grid(column=2, row=6)

# button for changing output folder
change_output_folder_button = tk.Button(mod_list_frame, text="Change output folder (hover for current)",
                                        command=change_output_folder_button_command)
change_output_folder_button.grid(column=5, row=6)
create_tooltip(change_output_folder_button, text=os.getcwd() + "\\output")

# --- Mod info ---------------------------------------------------------------------------------------------------------

mod_info_frame = ttk.Frame(mainframe, relief='sunken', borderwidth=5, width=100)
mod_info_frame.grid(column=2, row=0, padx=5, pady=5)

mod_info_label = tk.Label(mod_info_frame, text="Mod info:")
mod_info_label.grid(column=0, row=0)

mod_info_text = tk.Text(mod_info_frame, state='normal', font=(None, 8),
                        height=18, width=40)
mod_info_text.insert('1.0', "No mod chosen.\nClick on a mod in one of the lists to the left to"
                            "\nshow information about it.")
mod_info_text.configure(state='disabled')
mod_info_text.grid(column=0, row=1)

mod_info_text_scrollbar = tk.Scrollbar(mod_info_frame, orient=tk.VERTICAL, command=mod_info_text.yview)
mod_info_text.configure(yscrollcommand=mod_info_text_scrollbar.set)
mod_info_text_scrollbar.grid(column=1, row=1)

# --- Bottom row buttons (Compile and ?/Help)---------------------------------------------------------------------------

compile_button = tk.Button(mainframe, text="Compile/install mods", command=compile_button_command,
                           background='Green', foreground='White')
compile_button.grid(column=1, row=1)

modloader_help_button = tk.Button(mainframe, text="?", command=modloader_help_button_command)
modloader_help_button.grid(column=2, row=1, sticky=tk.E)

# ----------------------------------------------------------------------------------------------------------------------

# initializes the lists of all mods, selected mods, and non-selected mods
mods = []
selected_mods = []
non_selected_mods = []
# missing mods are mods that are not in the mods folder, but have been read once
# (i.e. their folder existed but then disappeared)
missing_mods = []

# loads the mods
load_mods_folder()

# gets the logo image
image = ImageTk.PhotoImage(Image.open('logo.png'))
logo_label = ttk.Label(mainframe)
logo_label['image'] = image
logo_label.grid(column=2, row=1, sticky=tk.S)

# sets the default output path
output_path = os.getcwd() + "\\output"

# runs the main loop
root.mainloop()

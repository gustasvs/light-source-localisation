# light-source-localisation
most of the code needed for light source localisation problem solving using timote motes

this is final project for BST course.

# windows setup

1. connect usb motes.

2. run 
```
usbipd attach --busid 2-4 --wsl Ubuntu
```
on admin powershell

3. lounch `flash.bat` to put code INTO the motes

4. cd into the repos base dir and run `wsl` to open a linux subsystem and then in it run `sudo python3 display.py` 

# linux setup

follow MansOS tutorial and run the `display.py`

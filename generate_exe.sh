#!/bin/bash

current_dir=$(pwd)
echo "Current directory is: $current_dir"

echo "activating virtual environment"
source ./venv/Scripts/activate

echo "running pyinstaller"
pyinstaller --noconfirm --onedir firelearnGUI.py \
  --add-data "C:/Users/wlutz/PycharmProjects/FireLearn-GUI/venv/Lib/site-packages/customtkinter;customtkinter" \
  --add-data "C:/Users/wlutz/PycharmProjects/FireLearn-GUI/data;data"

echo "deactivating virtual environment"

echo ".exe file generation finished"
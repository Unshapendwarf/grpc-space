#!/bin/sh
target_path="/mnt/nvme0n1/data/savepoint"

cd $target_path
echo $PWD, "$(ls | wc -l) items will be removed. Do you want to proceed? [y/n]"

read choice

if [ "$choice" = "y" ] || [ "$choice" = "Y" ]; then
    echo "cleaning."
    rm -rf ./*.pckl ./*.png
    echo "Cleaned. $(ls | wc -l) items in $PWD"

elif [ "$choice" = "n" ] || [ "$choice" = "N" ]; then
    echo "exit without cleaning"
else
    echo "Invalid choice. Please enter y or n."
fi
#!/bin/sh
curr_hostname=$(hostname)
if [ $curr_hostname = "mango3" ] && [ "$USER" = "hong" ]; then
    target_path="/data/hong/savepoint"
elif [ $curr_hostname = "ubuntu"] && ["$USER" = "nvidia"]; then
    target_path="/mnt/nvme0n1/data/savepoint"
else
    echo "Invalid machine"
fi

cd $target_path
echo $curr_hostname-$USER, $PWD: "$(ls | wc -l) items will be removed. Do you want to proceed? [y/n]"

read choice

if [ "$choice" = "y" ] || [ "$choice" = "Y" ]; then
    echo "Cleaning..."
    rm ./*.pckl 
    rm ./*.png
    echo "Done! $(ls | wc -l) items left in $PWD"
elif [ "$choice" = "n" ] || [ "$choice" = "N" ]; then
    echo "Exit without cleaning"
else
    echo "Invalid choice. Please enter y or n."
fi
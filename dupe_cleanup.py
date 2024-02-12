#!/usr/bin/env python3

import os
import shutil
import argparse

def move_contents_to_new_structure(src_dir, dest_dir):
    """
    Move contents of src_dir to dest_dir.
    """
    for item in os.listdir(src_dir):
        src_item = os.path.join(src_dir, item)
        dest_item = os.path.join(dest_dir, item)
        shutil.move(src_item, dest_item)

def process_directory(target_path):
    for root, dirs, _ in os.walk(target_path):
        if 'dupe' in dirs:
            dupe_dir = os.path.join(root, 'dupe')

            # Navigate up to get the directory where the new duplicates structure will be created
            target_dir = os.path.abspath(os.path.join(root, "../.."))

            # Correctly extract the year and month from the root
            month, year = os.path.basename(root), os.path.basename(os.path.dirname(root))
            
            # Construct the new duplicate directory path
            new_dupe_dir = os.path.join(target_dir, "duplicates", year, month)
            os.makedirs(new_dupe_dir, exist_ok=True)

            move_contents_to_new_structure(dupe_dir, new_dupe_dir)

            # Optionally remove the old dupe directory if it's empty
            try:
                os.rmdir(dupe_dir)
            except OSError:
                print(f"Directory not empty: {dupe_dir}")

def main(target_paths):
    for path in target_paths:
        process_directory(path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Move "dupe" directories to new "duplicates" structure.')
    parser.add_argument('target_paths', nargs='+', help='Target directory paths to clean up')
    args = parser.parse_args()
    main(args.target_paths)

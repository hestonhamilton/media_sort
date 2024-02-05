#!/usr/bin/env python3

import os
import shutil
from datetime import datetime
import mimetypes
import sys

duplicate_filepaths = []  # Global list to track duplicate filepaths

def categorize_file(file_path):
    mime_type, _ = mimetypes.guess_type(file_path)
    ext = os.path.splitext(file_path)[1].lower()
    
    # Explicitly categorize certain file extensions
    document_extensions = ['.pdf', '.txt', '.rtf', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx', '.odt', '.csv', '.msg', '.rar', '.zip']
    if ext in document_extensions:
        return 'documents'    
    
    if ext in ['.3g2']:
        return 'videos'
    
    # Continue with MIME type-based categorization   
    if mime_type:
        if mime_type.startswith('image') and ext not in ['.ico', '.psd', '.tif', '.gif']:
            return 'images'
        elif mime_type.startswith('video'):
            return 'videos'
        elif mime_type.startswith('audio'):
            return 'music'
    return 'other'

def get_oldest_date(file_path):
    creation_time = os.path.getctime(file_path)
    modification_time = os.path.getmtime(file_path)
    return min(creation_time, modification_time)

def copy_file(src, dest):
    global duplicate_filepaths
    base, extension = os.path.splitext(dest)
    counter = 1
    original_dest = dest
    is_duplicate = False

    while os.path.exists(dest):
        is_duplicate = True
        dest = f"{base}_{counter}{extension}"
        counter += 1
    shutil.copy2(src, dest)

    if is_duplicate:
        with open('duplicates_log.txt', 'a') as log:
            log.write(f"Duplicate: '{src}' renamed to '{dest}'\n")
        duplicate_filepaths.append(dest)

def sort_files(src_directory, dest_directory):
    for root, _, files in os.walk(src_directory):
        for file in files:
            file_path = os.path.join(root, file)
            category = categorize_file(file_path)
            oldest_time = get_oldest_date(file_path)
            oldest_date = datetime.fromtimestamp(oldest_time)
            year_month = oldest_date.strftime("%Y/%m")
            new_dir = os.path.join(dest_directory, category, year_month)
            os.makedirs(new_dir, exist_ok=True)
            copy_file(file_path, os.path.join(new_dir, file))

def main():
    if len(sys.argv) >= 3:
        src_directory = sys.argv[1]
        dest_directory = sys.argv[2]
    else:
        src_directory = input("Enter the source directory path: ")
        dest_directory = input("Enter the destination directory path: ")

    sort_files(src_directory, dest_directory)

    # Write the sorted list of duplicate filepaths to the log
    with open('duplicates_log.txt', 'a') as log:
        log.write("\nSorted List of Duplicate Filepaths:\n")
        for filepath in sorted(duplicate_filepaths):
            log.write(filepath + '\n')

if __name__ == "__main__":
    main()
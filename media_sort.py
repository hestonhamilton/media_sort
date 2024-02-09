#!/usr/bin/env python3

import os
import shutil
from datetime import datetime
import mimetypes
import sys
import filecmp
import argparse


def are_files_identical(file1, file2):
    # Quick check by comparing file sizes
    if os.path.getsize(file1) != os.path.getsize(file2):
        return False
    # Detailed check by comparing file contents
    return filecmp.cmp(file1, file2, shallow=False)


def categorize_file(file_path):
    mime_type, _ = mimetypes.guess_type(file_path)
    ext = os.path.splitext(file_path)[1].lower()

    # Explicitly categorize certain file extensions
    document_extensions = ['.pdf', '.txt', '.rtf', '.doc', '.docx', '.ppt',
                           '.pptx', '.xls', '.xlsx', '.odt', '.csv', '.msg', '.rar', '.zip']
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
    base, extension = os.path.splitext(dest)
    counter = 1
    is_duplicate = False

    while os.path.exists(dest):
        if are_files_identical(src, dest):
            is_duplicate = True
            break
        dest = f"{base}_{counter}{extension}"
        counter += 1

    # If it's a true duplicate, log it and don't copy
    if is_duplicate:
        return f"True duplicate: '{src}' not copied to '{dest}'"
    # If not a duplicate, or a duplicate name but unique content, copy with a new name
    else:
        shutil.copy2(src, dest)
        return f"File copied: '{src}' to '{dest}'"


def sort_files(src_directory, dest_directory, log_file=None):
    duplicate_messages = []
    for root, _, files in os.walk(src_directory):
        for file in files:
            file_path = os.path.join(root, file)
            category = categorize_file(file_path)
            oldest_time = get_oldest_date(file_path)
            oldest_date = datetime.fromtimestamp(oldest_time)
            year_month = oldest_date.strftime("%Y/%m")
            new_dir = os.path.join(dest_directory, category, year_month)
            os.makedirs(new_dir, exist_ok=True)
            message = copy_file(
                file_path, os.path.join(new_dir, file), log_file)
            duplicate_messages.append(message)

    for message in duplicate_messages:
        log_message(message, log_file)


def check_duplicates_in_directory(target_directory):
    all_files = [os.path.join(dp, f) for dp, dn, filenames in os.walk(
        target_directory) for f in filenames]
    checked = set()
    duplicates = []

    for i, file_path in enumerate(all_files):
        if file_path in checked:
            continue
        for other_file in all_files[i+1:]:
            if are_files_identical(file_path, other_file):
                duplicates.append((file_path, other_file))
                checked.add(other_file)

    for dup in duplicates:
        log_message(f"{dup[0]} and {dup[1]}", log_file)


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='File Sorting and Duplicate Checking Script')
    parser.add_argument(
        '--source', '-s', help='Source directory path', default=None)
    parser.add_argument(
        '--dest', '-d', help='Destination directory path', default=None)
    parser.add_argument(
        '--dupecheck', '-dupe', nargs='+', help='Filepaths to check for duplicates', default=None)
    parser.add_argument(
        '--log', '-l', help='Log path', default=None)

    return parser.parse_args()


def log_message(message, log_file=None):
    if not log_file:
        log_file = 'duplicates_log.txt'  # Default log file name
    with open(log_file, 'a') as log:
        log.write(message + '\n')

def main():
    args = parse_arguments()
    log_file = args.log

    if args.dupecheck:
        for file_path in args.dupecheck:
            check_duplicates_in_directory(file_path, args.log)
    elif args.source and args.dest:
        sort_files(args.source, args.dest, args.log)
    else:
        print("Error: Source and destination directories are required for sorting.")


if __name__ == "__main__":
    main()

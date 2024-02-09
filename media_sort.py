#!/usr/bin/env python3

import os
import shutil
from datetime import datetime
import mimetypes
import sys
import filecmp
import argparse


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


def are_files_identical(file1, file2):
    try:
        if os.path.getsize(file1) != os.path.getsize(file2):
            return False
        return filecmp.cmp(file1, file2, shallow=False)
    except Exception as e:
        log_message(f"Error comparing files '{file1}' and '{file2}': {e}")
        return False


# Only called by sort_files(), which logs the return of copy_file()
def copy_file(src, dest, log_file=None):
    try:
        base, extension = os.path.splitext(dest)
        counter = 1
        is_duplicate = False

        while os.path.exists(dest):
            if are_files_identical(src, dest):
                is_duplicate = True
                break
            dest = f"{base}_{counter}{extension}"
            counter += 1

        if is_duplicate:
            return f"True duplicate: '{src}' not copied to '{dest}'"
        else:
            shutil.copy2(src, dest)
            return f"File copied: '{src}' to '{dest}'"
    except Exception as e:
        return f"Error copying file '{src}' to '{dest}': {e}"


def sort_files(src_directory, dest_directory, log_file=None):
    try:
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
                log_message(message, log_file)

    except Exception as e:
        log_message(
            f"Error accessing directory '{src_directory}': {e}", log_file)


def get_files(path):
    if os.path.isdir(path):
        return [os.path.join(dp, f) for dp, dn, filenames in os.walk(path) for f in filenames]
    elif os.path.isfile(path):
        return [path]
    else:
        return []


def check_duplicates_in_directory(path, log_file=None):
    try:
        all_files = get_files(path)
        checked = set()
        duplicates = set()

        for file_index, file_path in enumerate(all_files):
            if file_path in checked:
                continue
            for other_file in all_files[file_index+1:]:
                if other_file in checked:
                    continue
                if are_files_identical(file_path, other_file):
                    duplicates.add(other_file)
                    checked.add(other_file)
                    log_message(
                        f"Duplicate found: '{other_file}'", log_file)

    except Exception as e:
        log_message(f"Error accessing path '{path}': {e}", log_file)


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='File Sorting and Duplicate Checking Script')
    parser.add_argument(
        '--source', '-s', help='Source directory path', default=None)
    parser.add_argument(
        '--dest', '-d', help='Destination directory path', default=None)
    parser.add_argument(
        '--dupecheck', '--dupe', '-dupe', nargs='+', help='Filepaths to check for duplicates', default=None)
    parser.add_argument(
        '--log', '-l', help='Log path', default=None)

    return parser.parse_args()


def log_message(message, log_file=None):
    try:
        if not log_file:
            log_file = 'duplicates.log'  # Default log file name
        with open(log_file, 'a') as log:
            log.write(message + '\n')
    except Exception as e:
        print(f"Error writing to log file '{log_file}': {e}")


def main():
    try:
        args = parse_arguments()
        log_file = args.log

        if args.dupecheck:
            for file_path in args.dupecheck:
                check_duplicates_in_directory(file_path, args.log)
        elif args.source and args.dest:
            sort_files(args.source, args.dest, args.log)
        else:
            print("Error: Source and destination directories are required for sorting.")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()

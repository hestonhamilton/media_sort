#!/usr/bin/env python3

import os
import shutil
from datetime import datetime
import mimetypes
import filecmp
import argparse


class MediaSorter:
    def __init__(self, source, destination, log_file='duplicates.log'):
        self.source = source
        self.destination = destination
        self.log_file = log_file

    def categorize_file(self, file_path):
        """
        Determine the category of a file based on its MIME type and extension.

        :param file_path: Path of the file to categorize.
        :return: The category of the file as a string.
        """
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

    def get_oldest_date(self, file_path):
        """
        Get the oldest date (either creation or modification) of a file.

        :param file_path: Path of the file.
        :return: The oldest date as a timestamp.
        """
        creation_time = os.path.getctime(file_path)
        modification_time = os.path.getmtime(file_path)
        return min(creation_time, modification_time)

    def are_files_identical(self, file1, file2):
        """
        Check if two files are identical by comparing their size and content.

        :param file1: Path to the first file.
        :param file2: Path to the second file.
        :return: True if files are identical, False otherwise.
        """
        try:
            if os.path.getsize(file1) != os.path.getsize(file2):
                return False
            return filecmp.cmp(file1, file2, shallow=False)
        except Exception as e:
            self.log_message(
                f"Error comparing files '{file1}' and '{file2}': {e}")
            return False

    # Only called by sort_files(), which logs the return of copy_file()

    def copy_file(self, src, dest, log_file=None):
        """
        Copy a file from src to dest, handling duplicates by renaming.

        :param src: Source file path.
        :param dest: Destination file path.
        :param log_file: Path to the log file.
        :return: Log message about the copying result.
        """
        try:
            base, extension = os.path.splitext(dest)
            counter = 1
            is_duplicate = False

            while os.path.exists(dest):
                if self.are_files_identical(src, dest):
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

    def sort_files(self, src_directory, dest_directory, log_file=None):
        """
        Sort files from a source directory into categorized subdirectories in the destination.

        :param src_directory: Source directory path.
        :param dest_directory: Destination directory path.
        :param log_file: Path to the log file.
        """
        try:
            for root, _, files in os.walk(src_directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    category = self.categorize_file(file_path)
                    oldest_time = self.get_oldest_date(file_path)
                    oldest_date = datetime.fromtimestamp(oldest_time)
                    year_month = oldest_date.strftime("%Y/%m")
                    new_dir = os.path.join(
                        dest_directory, category, year_month)
                    os.makedirs(new_dir, exist_ok=True)
                    message = self.copy_file(
                        file_path, os.path.join(new_dir, file), log_file)
                    self.log_message(message, log_file)

        except Exception as e:
            self.log_message(
                f"Error accessing directory '{src_directory}': {e}", log_file)

    def get_files(self, path):
        """
        Get a list of all files in a directory or a single file if the path is a file.

        :param path: Path to a directory or a file.
        :return: List of file paths.
        """
        if os.path.isdir(path):
            self.files = []
            for dp, dn, filenames in os.walk(path):
                if not dp.endswith(os.sep + 'dupe'):
                    self.files.extend([os.path.join(dp, f) for f in filenames])
            return self.files
        elif os.path.isfile(path) and not os.path.dirname(path).endswith(os.sep + 'dupe'): # Excludes ${path}/dupe directories previously created by the script.
            return [path]
        else:
            return []

    def move_duplicate(self, file_path, log_file=None):
        """
        Move a duplicate file to a 'dupe' subdirectory within its current directory.

        :param file_path: Path of the duplicate file to be moved.
        :param log_file: Path to the log file.
        """
        dupe_dir = os.path.join(os.path.dirname(file_path), "dupe")

        # Check if the "dupe" directory exists in dest; create it if it doesn't
        if not os.path.exists(dupe_dir):
            try:
                os.makedirs(dupe_dir)
            except Exception as e:
                self.log_message(
                    f"Error creating directory '{dupe_dir}': {e}", log_file)
                return

        try:
            new_path = os.path.join(dupe_dir, os.path.basename(file_path))
            shutil.move(file_path, new_path)
            self.log_message(
                f"Moved duplicate file: {file_path} to {new_path}", log_file)
        except Exception as e:
            self.log_message(f"Error moving file '{file_path}': {e}", log_file)

    def delete_duplicate(self, file_path, log_file=None):
        """
        Delete a duplicate file from the filesystem.
        :param file_path: Path of the duplicate file to be deleted.
        :param log_file: Path to the log file.
        """
        try:
            os.remove(file_path)
            self.log_message(f"Deleted duplicate file: {file_path}", log_file)
        except Exception as e:
            self.log_message(
                f"Error deleting file '{file_path}': {e}", log_file)

    def check_duplicates_in_directory(self, path, move_dupes=False, delete_dupes=False, log_file=None):
        """
        Check for duplicate files in a directory and optionally move or delete them.

        :param path: Directory path to check for duplicates.
        :param move_dupes: Boolean indicating whether to move duplicates to 'dupe' directory.
        :param delete_dupes: Boolean indicating whether to delete duplicates.
        :param log_file: Path to the log file.
        """
        try:
            all_files = self.get_files(path)
            checked = set()

            for file_index, file_path in enumerate(all_files):
                if file_path in checked:
                    continue
                for other_file in all_files[file_index+1:]:
                    if other_file in checked:
                        continue
                    if self.are_files_identical(file_path, other_file):
                        checked.add(other_file)
                        self.log_message(
                            f"Duplicate found: '{other_file}'", log_file)
                        if move_dupes:
                            self.move_duplicate(other_file, log_file)
                        elif delete_dupes:
                            self.delete_duplicate(other_file, log_file)

        except Exception as e:
            self.log_message(f"Error accessing path '{path}': {e}", log_file)

    def parse_arguments(self):
        """
        Parse command line arguments.

        :return: Namespace with parsed arguments.
        """
        parser = argparse.ArgumentParser(
            description='File Sorting and Duplicate Checking Script')

        # Arguments for sorting files
        parser.add_argument(
            '--source', '-s', help='Source directory path', default=None)
        parser.add_argument(
            '--dest', '-d', help='Destination directory path', default=None)
        parser.add_argument(
            '--log', '-l', help='Log file path', default='duplicates.log')

        # Create subparsers for subcommands
        subparsers = parser.add_subparsers(
            dest='command', help='Sub-command help')

        # Subparser for dupecheck
        dupe_parser = subparsers.add_parser(
            'dupecheck', help='Check for duplicates')
        dupe_parser.add_argument(
            'paths', nargs='+', help='Filepaths to check for duplicates')
        dupe_parser.add_argument('--move-dupes', action='store_true',
                                 help='Move duplicate files to a "dupe" directory')
        dupe_parser.add_argument(
            '--delete-dupes', action='store_true', help='Delete duplicate files')

        return parser.parse_args()

    def log_message(self, message, log_file=None):
        """
        Log a message to a specified log file or to a default log file. Will always have default value 'duplicates.log' set by parse_arguments().

        :param message: Message to log.
        :param log_file: Path to the log file.
        """
        try:
            self.log_file = log_file or self.log_file  # Use log_file parameter if provided, otherwise default to self.log_file
            with open(self.log_file, 'a') as log:
                log.write(message + '\n')
        except Exception as e:
            print(f"Error writing to log file '{self.log_file}': {e}")

    def run(self):
        """
        Main method, executes the script.
        """
        try:
            args = self.parse_arguments()
            self.log_file = args.log

            if args.command == 'dupecheck':
                for file_path in args.paths:
                    self.log_message(f"Starting dupecheck of '{file_path}'...")
                    self.check_duplicates_in_directory(
                        file_path, args.move_dupes, args.delete_dupes, self.log_file)
            else:
                # Set the source and destination from the parsed arguments
                self.source = args.source
                self.destination = args.dest

                # Check if source and destination directories are provided
                if self.source and self.destination:
                    self.log_message(
                        f"Sorting files from '{self.source}' into '{self.destination}'...")
                    self.sort_files(self.source, self.destination, self.log_file)
                else:
                    print(
                        "Error: Source and destination directories are required for sorting.")

        except Exception as e:
            print(f"An error occurred: {e}")


if __name__ == "__main__":
    media_sorter = MediaSorter(None, None)
    media_sorter.run()

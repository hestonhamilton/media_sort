#!/usr/bin/env python3

import os
import shutil
from datetime import datetime
from PIL import Image, ExifTags
import re
import mimetypes
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
        Get the oldest date (either from EXIF data or file's metadata) of a file.

        :param file_path: Path of the file.
        :return: The oldest date as a timestamp.
        """

        category = self.categorize_file(file_path)

        if category == 'images':
            exif_data = self.get_exif_data(file_path)
            if 'DateTimeOriginal' in exif_data:
                try:
                    exif_date = datetime.strptime(
                        exif_data['DateTimeOriginal'], '%Y:%m:%d %H:%M:%S')
                    return exif_date.timestamp()
                except (ValueError, TypeError) as e:
                    # Debugging output
                    self.log_message(f"EXIF date error: {e}")

        # Fallback to using file's metadata
        creation_time = os.path.getctime(file_path)
        modification_time = os.path.getmtime(file_path)
        oldest_date = min(creation_time, modification_time)
        return oldest_date

    def are_files_identical(self, file1, file2):
        try:
            if not (os.path.exists(file1) and os.path.exists(file2)):
                return False  # One or both files do not exist

            # Not duplicates if filename minus extension aren't similar
            name1, name2 = os.path.splitext(os.path.basename(file1))[
                0], os.path.splitext(os.path.basename(file2))[0]
            if not self.similar_filenames(name1, name2):
                return False

            # For images only, check specific EXIF tags
            # Store second return value in "_" since it's not important
            category1 = self.categorize_file(file1)
            category2 = self.categorize_file(file2)
            if category1 == 'images' and category2 == 'images':
                exif1, exif2 = self.get_exif_data(
                    file1), self.get_exif_data(file2)
                # Compare the selected EXIF tags
                for tag in exif1:
                    if exif1[tag] != exif2[tag]:
                        return False
                return True

            # For non-image files or images without EXIF data, check file sizes
            size1, size2 = os.path.getsize(file1), os.path.getsize(file2)
            return size1 == size2

        except Exception as e:
            self.log_message(
                f"Error comparing files '{file1}' and '{file2}': {e}")
            return False

    def similar_filenames(self, name1, name2):
        """
        Check if two filenames are similar, considering possible renaming or numbering at the end.
        """
        # Regular expression to match renaming patterns such as:
        # "1-1-07 283.jpg" and "1-1-07 283_1.jpg" and "H1019100.JPG" and "H1019100_2.JPG"
        # The regex handles any number of spaces, dashes, underscores, and parentheses around numbers at the end of filenames.
        # It also allows for arbitrary characters preceding the "rename" string.
        pattern = r'([-_ ]*\d+)?([-_ ]*\(\d+\))?([-_ ]*\d+)?$'
        base_name1 = re.sub(pattern, '', name1)
        base_name2 = re.sub(pattern, '', name2)
        return base_name1 == base_name2

    def get_exif_data(self, filepath):
        """Extract specific EXIF data from an image file."""
        try:
            if not os.path.exists(filepath):
                return {}  # File does not exist

            with Image.open(filepath) as img:
                exif_data = img.getexif()
                if exif_data:
                    readable_exif = {ExifTags.TAGS.get(
                        k, k): v for k, v in exif_data.items()}
                    selected_tags = ['DateTimeOriginal', 'Make', 'Model',
                                     'ExposureTime', 'FNumber', 'ISOSpeedRatings']
                    return {tag: readable_exif.get(tag) for tag in selected_tags}
                else:
                    return {}
        except IOError as e:
            self.log_message(f"Error opening image file '{filepath}': {e}")
            return {}

    def get_files(self, path):
        """
        Get a list of all files in a directory.

        :param path: Path to a directory.
        :return: List of file paths.
        """
        file_list = []
        try:
            for root, _, files in os.walk(path):
                for file in files:
                    file_path = os.path.join(root, file)
                    # Optionally, you could add a check to skip files in specific subdirectories
                    # if needed, similar to the check for 'dupe' directories in your original code.
                    file_list.append(file_path)
            return file_list

        except Exception as e:
            self.log_message(f"Error accessing path '{path}': {e}")
            return []

    def move_duplicate(self, file_path, log_file=None):
        """
        Move a duplicate file to a 'dupe' subdirectory within the destination directory.

        :param file_path: Path of the duplicate file to be moved.
        :param log_file: Path to the log file.
        """
        try:
            # Extract the oldest date from the file to determine its target directory
            oldest_date = datetime.fromtimestamp(
                self.get_oldest_date(file_path))
            year_month = oldest_date.strftime("%Y/%m")
            # Construct the new duplicate directory path using the destination directory
            category = self.categorize_file(file_path)

            # Split the file path to analyze the directory structure
            path_parts = os.path.normpath(file_path).split(os.sep)
            year, month = year_month.split('/')

            # Check if the parent and grandparent directories match year and month
            if len(path_parts) >= 3 and path_parts[-2] == month and path_parts[-3] == year:
                dupe_dir = os.path.join(
                    self.destination, "duplicates", category, year_month)
            else:
                dupe_dir = os.path.join(self.destination, "duplicates")

            # Create the directory and move the file
            os.makedirs(dupe_dir, exist_ok=True)
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

    def dupe_check(self, path, move_dupes=False, delete_dupes=False, log_file=None):
        """
        Check for duplicate files in a directory and optionally move or delete them.

        :param path: Directory path to check for duplicates.
        :param move_dupes: Boolean indicating whether to move duplicates to 'dupe' directory.
        :param delete_dupes: Boolean indicating whether to delete duplicates.
        :param log_file: Path to the log file.
        """
        try:
            self.log_message(f"Starting dupecheck of '{path}'...", log_file)
            all_files = self.get_files(path)
            checked = set()

            for file_index, file_path in enumerate(all_files):
                if file_path in checked:
                    continue
                for other_file in all_files[file_index+1:]:
                    if other_file in checked:
                        continue
                    if self.are_files_identical(file_path, other_file):
                        self.log_message(
                            f"Duplicate found: '{other_file}'", log_file)
                        checked.add(other_file)
                        if move_dupes:
                            self.move_duplicate(other_file, log_file)
                        elif delete_dupes:
                            self.delete_duplicate(other_file, log_file)

        except Exception as e:
            self.log_message(f"Error during dupecheck: {e}", log_file)

    # Only called by sort_files(), which logs the return of copy_file()

    def copy_file(self, src, dest, log_file=None):
        """
        Copy a file from src to dest.

        :param src: Source file path.
        :param dest: Destination file path.
        :param log_file: Path to the log file.
        :return: Log message about the copying result.
        """
        try:
            # Check if a file with the same name exists in the destination and rename if necessary
            base, extension = os.path.splitext(dest)
            counter = 1
            while os.path.exists(dest):
                dest = f"{base}_{counter}{extension}"
                counter += 1

            shutil.copy2(src, dest)
            return f"File copied: '{src}' to '{dest}'"
        except Exception as e:
            return f"Error copying file '{src}' to '{dest}': {e}"

    def sort_files(self, src_directory, dest_directory, mode='date', move_dupes=False, delete_dupes=False, log_file=None):
        processed_files = []  # Files processed in this run
        # Files already in destination
        existing_files = self.get_files(dest_directory)

        try:
            # Fetch files from the source directory using get_files()
            source_files = self.get_files(src_directory)

            for file_path in source_files:
                category = self.categorize_file(file_path)

                # Directory structure based on mode
                new_dir = os.path.join(dest_directory, category, datetime.fromtimestamp(self.get_oldest_date(
                    file_path)).strftime("%Y/%m")) if mode == 'date' else os.path.join(dest_directory, category)
                os.makedirs(new_dir, exist_ok=True)

                new_file_path = os.path.join(
                    new_dir, os.path.basename(file_path))
                is_duplicate = any(self.are_files_identical(
                    file_path, other_file) for other_file in processed_files + existing_files)

                if is_duplicate:
                    if move_dupes:
                        # Copy the file to the destination before moving it to duplicates
                        self.copy_file(file_path, new_file_path, log_file)
                        self.move_duplicate(
                            new_file_path, log_file)
                    elif delete_dupes:
                        self.delete_duplicate(file_path, log_file)
                    else:
                        # If not moving or deleting, just log the duplicate without copying
                        no_copy_message = f"Duplicate found, not copying: '{file_path}'"
                        self.log_message(no_copy_message, log_file)
                else:
                    # If it's not a duplicate, copy the file normally
                    copy_message = self.copy_file(
                        file_path, new_file_path, log_file)
                    # Add the destination file path to processed_files
                    processed_files.append(new_file_path)
                    self.log_message(copy_message, log_file)

        except Exception as e:
            self.log_message(
                f"Error accessing directory '{src_directory}': {e}", log_file)

    def parse_arguments(self):
        """
        Parse command line arguments.

        :return: Namespace with parsed arguments.
        """
        parser = argparse.ArgumentParser(
            description='File Sorting and Duplicate Checking Script')

        # Global arguments
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

        # Subparser for copy
        copy_parser = subparsers.add_parser('copy', help='Copy files')
        copy_parser.add_argument(
            '--source', '-s', help='Source directory path')
        copy_parser.add_argument(
            '--dest', '-d', help='Destination directory path')
        copy_parser.add_argument('--mode', '-m', choices=['date', 'category'], default='date',
                                 help='Sorting mode: "date" for sorting by date and type, "category" for sorting only by type')
        copy_parser.add_argument('--move-dupes', action='store_true',
                                 help='Move duplicate files to a "dupe" directory')
        copy_parser.add_argument(
            '--delete-dupes', action='store_true', help='Delete duplicate files')

        return parser.parse_args()

    def log_message(self, message, log_file=None):
        """
        Log a message to a specified log file or to a default log file. Will always have default value 'duplicates.log' set by parse_arguments().

        :param message: Message to log.
        :param log_file: Path to the log file.
        """
        try:
            # Use log_file parameter if provided, otherwise default to self.log_file
            self.log_file = log_file or self.log_file
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
            self.move_dupes = args.move_dupes
            self.delete_dupes = args.delete_dupes

            if args.command == 'dupecheck':
                for file_path in args.paths:
                    self.destination = file_path
                    self.log_message(
                        f"Dupecheck on: {file_path}, Move Dupes: {self.move_dupes}, Delete Dupes: {self.delete_dupes}")
                    self.dupe_check(file_path, self.move_dupes,
                                    self.delete_dupes, self.log_file)
                    self.log_message(
                        f"Dupecheck on: {file_path} complete!")
            else:
                # Set the source and destination from the parsed arguments
                self.source = args.source
                self.destination = args.dest
                self.sort_mode = args.mode or 'date'

                # Check if source and destination directories are provided
                if self.source and self.destination:
                    self.log_message(
                        f"Sorting files from '{self.source}' into '{self.destination}'...")
                    self.sort_files(self.source, self.destination, self.sort_mode,
                                    self.move_dupes, self.delete_dupes, self.log_file)
                else:
                    print(
                        "Error: Source and destination directories are required for sorting.")

        except Exception as e:
            print(f"An error occurred: {e}")


if __name__ == "__main__":
    media_sorter = MediaSorter(None, None)
    media_sorter.run()

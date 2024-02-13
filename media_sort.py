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
        Get the oldest date (either creation or modification) of a file.

        :param file_path: Path of the file.
        :return: The oldest date as a timestamp.
        """
        creation_time = os.path.getctime(file_path)
        modification_time = os.path.getmtime(file_path)
        return min(creation_time, modification_time)

    def are_files_identical(self, file1, file2):
        try:
            # Not duplicates if filename minus extension aren't similar
            name1, name2 = os.path.splitext(os.path.basename(file1))[
                0], os.path.splitext(os.path.basename(file2))[0]
            if not self.similar_filenames(name1, name2):
                return False

            # For images only, check specific EXIF tags
            # Store second return value in "_" since it's not important
            mime_type1, _ = mimetypes.guess_type(file1)
            mime_type2, _ = mimetypes.guess_type(file2)
            if mime_type1.startswith('image') and mime_type2.startswith('image'):
                exif1, exif2 = self.get_exif_data(file1), self.get_exif_data(file2)
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
            with Image.open(filepath) as img:
                exif_data = img._getexif()
                if exif_data:
                    readable_exif = {ExifTags.TAGS.get(k, k): v for k, v in exif_data.items()}
                    # Selecting specific EXIF tags to focus on
                    selected_tags = ['DateTimeOriginal', 'Make', 'Model', 'ExposureTime', 'FNumber', 'ISOSpeedRatings']
                    return {tag: readable_exif.get(tag) for tag in selected_tags}
                else:
                    return {}
        except IOError as e:
            print(f"Error opening image file '{filepath}': {e}")
            return {}

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
        processed_files = []  # List to keep track of processed files

        try:
            for root, _, files in os.walk(src_directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    category = self.categorize_file(file_path)

                    # Directory structure based on mode
                    new_dir = os.path.join(dest_directory, category, datetime.fromtimestamp(self.get_oldest_date(
                        file_path)).strftime("%Y/%m")) if mode == 'date' else os.path.join(dest_directory, category)
                    os.makedirs(new_dir, exist_ok=True)

                    # Check for duplicates in processed_files
                    duplicate_file = next((other_file for other_file in processed_files if self.are_files_identical(
                        file_path, other_file)), None)
                    if duplicate_file:
                        if move_dupes:
                            message = f"Duplicate found, moving: '{file_path}'"
                            self.move_duplicate(file_path, log_file)
                        elif delete_dupes:
                            message = f"Duplicate found, deleting: '{file_path}'"
                            self.delete_duplicate(file_path, log_file)
                        else:
                            message = f"Duplicate found, not copying: '{file_path}'"
                    else:
                        message = self.copy_file(
                            file_path, os.path.join(new_dir, file), log_file)
                        # Add to processed files only if not a duplicate
                        processed_files.append(file_path)

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
            for dp, filenames in os.walk(path):
                if not dp.endswith(os.sep + 'dupe'):
                    self.files.extend([os.path.join(dp, f) for f in filenames])
            return self.files
        # Excludes ${path}/dupe directories previously created by the script.
        elif os.path.isfile(path) and not os.path.dirname(path).endswith(os.sep + 'dupe'):
            return [path]
        else:
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
            dupe_dir = os.path.join(
                self.destination, "duplicates", category, year_month)

            # Create the directory if it doesn't exist
            os.makedirs(dupe_dir, exist_ok=True)

            # Move the file
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

        # Add an argument for sorting mode
        parser.add_argument('--mode', '-m', choices=['date', 'type'], default='date',
                            help='Sorting mode: "date" for sorting by date and type, "type" for sorting only by type')
        parser.add_argument('--move-dupes', action='store_true',
                            help='Move duplicate files to a "dupe" directory')
        parser.add_argument('--delete-dupes', action='store_true',
                            help='Delete duplicate files')
        # Create subparsers for subcommands
        subparsers = parser.add_subparsers(
            dest='command', help='Sub-command help')

        # Subparser for dupecheck
        dupe_parser = subparsers.add_parser(
            'dupecheck', help='Check for duplicates')
        dupe_parser.add_argument(
            'paths', nargs='+', help='Filepaths to check for duplicates')

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
                    self.log_message(f"Starting dupecheck of '{file_path}'...")
                    self.check_duplicates_in_directory(
                        file_path, self.move_dupes, self.delete_dupes, self.log_file)
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

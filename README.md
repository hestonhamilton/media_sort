# Media Sorter

Media Sorter is a Python script designed for organizing and managing media files in a filesystem. It categorizes files based on their MIME types, detects and handles duplicates, and sorts files into structured directories.

## Features

- **File Categorization**: Sorts files into categories such as images, documents, music, videos, and others based on MIME type and file extensions.
- **Duplicate Detection**: Identifies duplicate files using file metadata and content.
- **EXIF Data Extraction**: For image files, extracts EXIF data to assist in sorting and duplicate detection.
- **File Operations**: Performs operations like copying, moving, and deleting files as part of the sorting process.
- **Command-Line Interface**: Offers a CLI for easy interaction and execution of various functionalities.

## Requirements

- Python 3
- PIL (Python Imaging Library) for EXIF data extraction

## Installation

Clone the repository or download the script:

```bash
    git clone https://your-repository-url/media_sort.git
```

Install the required dependencies:

```python
    pip install -r requirements.txt
```

## Usage

Run the script from the command line. It supports two main operations: `dupecheck` and `copy`.

### Dupecheck

Checks for duplicate files in the specified paths:

```python
    python media_sort.py dupecheck [paths] [options]
```

Options:

- `--move-dupes`: Move detected duplicates to a specified directory.
- `--delete-dupes`: Delete detected duplicates.

### Copy

Sorts and copies files from the source directory to the destination directory:

```python
    python media_sort.py copy --source [source_directory] --dest [destination_directory] [options]
```

Options:

- `--mode`: Choose between 'date' (default) and 'category' sorting.
- `--move-dupes`: Move duplicates to a specified directory.
- `--delete-dupes`: Delete duplicates.

### Logging

Specify a log file to record operations:

```python
    --log [log_file_path]
```

## Configuration

The script includes a `MediaSorter` class, which can be configured by modifying the source code to suit specific sorting and duplicate handling needs.

## Contributing

Contributions to improve the script are welcome. Please follow the standard fork, branch, and pull request workflow.

## License

This script is distributed under the [CC BY-NC](LICENSE).

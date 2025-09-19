# API Documentation

## ImageProcessor Class

The core class that handles image processing and matching operations.

### Constructor

```python
ImageProcessor(base_directory: str, output_directory: str)
```

**Parameters:**
- `base_directory`: Path to the directory containing images to process
- `output_directory`: Path where processed images will be saved

### Methods

#### `find_image_directories() -> List[Path]`

Recursively searches for directories containing both `sample_image_*.jpg` and `combined_mask_*.jpg` files.

**Returns:** List of Path objects representing directories with image pairs

#### `compute_correlation(sample_img: np.ndarray, mask_img: np.ndarray) -> float`

Computes pixel correlation between a sample image and mask image.

**Parameters:**
- `sample_img`: Sample image as numpy array
- `mask_img`: Mask image as numpy array

**Returns:** Correlation coefficient (0.0 to 1.0)

#### `find_matches_for_directory(directory: Path, verbose: bool = False) -> Dict[str, str]`

Finds optimal matches between sample and mask images in a directory using the Hungarian algorithm.

**Parameters:**
- `directory`: Directory path to process
- `verbose`: Enable detailed progress output

**Returns:** Dictionary mapping sample filenames to mask filenames

#### `extract_date_from_exif(image_path: Path) -> Optional[datetime]`

Extracts date/time information from image EXIF data.

**Parameters:**
- `image_path`: Path to the image file

**Returns:** DateTime object if found, None otherwise

#### `generate_timestamp_filename(file_path: Path, file_type: str, sequential_counter: int) -> Tuple[Optional[str], str]`

Generates timestamp-based filename for a file.

**Parameters:**
- `file_path`: Original file path
- `file_type`: Type of file ("sample" or "mask")
- `sequential_counter`: Sequential ID for the file pair

**Returns:** Tuple of (new_filename, date_source)

**Note:** Generates filenames in the format `image-NNNN-original_timestamp.jpg` for samples and `image-NNNN-mask_timestamp.jpg` for masks.

#### `process_all_directories(verbose: bool = False, dry_run: bool = True) -> Dict`

Main processing method that handles the complete workflow.

**Parameters:**
- `verbose`: Enable detailed progress output
- `dry_run`: If True, performs preview without copying files

**Returns:** Dictionary with processing results and statistics

## Usage Examples

### Basic Processing

```python
from process_and_rename_images import ImageProcessor

processor = ImageProcessor("/path/to/images", "/path/to/output")
results = processor.process_all_directories(verbose=True, dry_run=False)
```

### Preview Mode

```python
processor = ImageProcessor("/path/to/images", "/path/to/output")
preview = processor.process_all_directories(verbose=True, dry_run=True)
print(f"Would process {preview['total_pairs']} image pairs")
```

### Custom Directory Processing

```python
processor = ImageProcessor("/path/to/images", "/path/to/output")
directories = processor.find_image_directories()

for directory in directories:
    matches = processor.find_matches_for_directory(directory, verbose=True)
    print(f"Found {len(matches)} matches in {directory}")
```

## Data Structures

### Processing Results

The `process_all_directories` method returns a dictionary with the following structure:

```python
{
    "processing_date": "2025-09-19T14:24:43.580805",
    "total_directories": 7,
    "total_pairs": 87,
    "files_copied": 174,
    "errors": [],
    "pairs": [
        {
            "sequential_id": 0,
            "original_sample": "sample_image_0.jpg",
            "original_mask": "combined_mask_0.jpg",
            "new_sample": "image-0000-original_2025-08-15_11-43-45.jpg",
            "new_mask": "image-0000-mask_2025-08-15_11-48-30.jpg",
            "source_directory": "/path/to/original/dir",
            "correlation_score": 0.92
        }
    ]
}
```

### Error Handling

All methods include comprehensive error handling. Errors are logged to the `errors` array in the processing results.

Common error types:
- File access errors
- Image loading failures
- Correlation computation errors
- File copy errors

## Performance Considerations

- **Memory Usage**: Images are loaded one at a time to minimize memory footprint
- **Processing Speed**: Correlation computation is the bottleneck; consider parallel processing for large datasets
- **Disk Space**: Ensure sufficient space for output directory (roughly 2x input size)
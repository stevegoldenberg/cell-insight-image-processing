# Usage Examples

This document provides practical examples of using the Cell Insight Image Processing system.

## Basic Workflows

### 1. First Time Setup

```bash
# Clone the repository
git clone https://github.com/stevegoldenberg/cell-insight-image-processing.git
cd cell-insight-image-processing

# Install dependencies
pip install -r requirements.txt

# Verify installation
python3 process_and_rename_images.py --help
```

### 2. Quick Preview (Recommended First Step)

```bash
# Preview what will happen without making changes
python3 process_and_rename_images.py --preview --verbose
```

**Expected Output:**
```
🔍 Scanning directories for image pairs...
📁 Found 7 directories with image pairs

Directory: /path/to/images/batch_1
  🔍 Analyzing 12 samples vs 12 masks
    sample_image_0.jpg ↔ combined_mask_0.jpg (correlation: 0.923)
    sample_image_1.jpg ↔ combined_mask_1.jpg (correlation: 0.891)
    ...

📊 PREVIEW SUMMARY:
✅ Would process 87 image pairs from 7 directories
✅ Would copy 174 files to output directory
✅ Average correlation score: 0.92
```

### 3. Execute Processing

```bash
# Process all images with default output directory
python3 process_and_rename_images.py --execute --verbose

# Or specify custom directories
python3 process_and_rename_images.py --execute -i /path/to/input -o /path/to/output
```

## Advanced Workflows

### 4. Batch Processing Multiple Datasets

```bash
# Process dataset 1 (creates dataset1/processed_images/)
python3 process_and_rename_images.py --execute -i dataset1/

# Process dataset 2 with custom output name (creates dataset2/dataset2_processed/)
python3 process_and_rename_images.py --execute -i dataset2/ -o dataset2_processed

# Combine results if needed
mkdir combined_results
cp processed_dataset1/* combined_results/
cp processed_dataset2/* combined_results/
```

### 5. Quality Control Workflow

```bash
# 1. Preview with correlation details
python3 process_and_rename_images.py --preview --verbose > preview_report.txt

# 2. Review correlation scores
grep "correlation:" preview_report.txt | sort -k3 -n

# 3. Execute if correlations look good
python3 process_and_rename_images.py --execute --verbose

# 4. Verify results
ls -la output_directory/
python3 -c "
import json
with open('output_directory/processing_summary.json', 'r') as f:
    data = json.load(f)
    print(f'Processed {data[\"total_pairs\"]} pairs')
    print(f'Average correlation: {sum(p[\"correlation_score\"] for p in data[\"pairs\"]) / len(data[\"pairs\"]):.3f}')
"
```

### 6. Development and Testing

```bash
# Create test dataset
mkdir test_images
cp sample_images/* test_images/

# Test with small dataset (creates test_images/processed_images/)
python3 process_and_rename_images.py --execute -i test_images --verbose

# Verify test results
ls test_images/processed_images/
cat test_images/processed_images/processing_summary.json | python3 -m json.tool
```

## Warp-Specific Workflows

### 7. Using Warp's AI Features

In Warp terminal, you can use AI assistance:

```bash
# Ask Warp AI to analyze correlation scores
python3 process_and_rename_images.py --preview --verbose
# Then ask: "Analyze these correlation scores and suggest improvements"
```

### 8. Warp Workflow Automation

Create a Warp workflow for repeated processing:

```bash
# Save as workflow: "Process Cell Images"
echo "Processing microscopy images..."
python3 process_and_rename_images.py --preview --verbose

read -p "Continue with processing? (y/N): " confirm
if [[ $confirm == [yY] ]]; then
    python3 process_and_rename_images.py --execute --verbose
    echo "✅ Processing complete!"
    ls -la ./processed_images/  # Created in current directory
else
    echo "❌ Processing cancelled"
fi
```

## Troubleshooting Examples

### 9. Handle Low Correlation Scores

```bash
# Identify problematic pairs
python3 process_and_rename_images.py --preview --verbose | grep "correlation: 0\.[0-4]"

# Manual inspection of specific files
python3 -c "
import cv2
import numpy as np
from process_and_rename_images import ImageProcessor

# Load and compare specific images
sample = cv2.imread('problematic_sample.jpg', cv2.IMREAD_GRAYSCALE)
mask = cv2.imread('problematic_mask.jpg', cv2.IMREAD_UNCHANGED)

processor = ImageProcessor('.', '.')
correlation = processor.compute_correlation(sample, mask)
print(f'Correlation: {correlation}')
"
```

### 10. Handle Missing EXIF Data

```bash
# Check which files lack EXIF data
python3 -c "
from pathlib import Path
from PIL import Image
import os

for img_file in Path('.').glob('*.jpg'):
    try:
        with Image.open(img_file) as img:
            exif = img._getexif()
            if exif is None:
                mtime = os.path.getmtime(img_file)
                print(f'{img_file}: No EXIF, using mtime: {mtime}')
            else:
                print(f'{img_file}: Has EXIF data')
    except Exception as e:
        print(f'{img_file}: Error - {e}')
"
```

## Performance Optimization

### 11. Large Dataset Processing

```bash
# For datasets with >1000 images, consider processing in chunks
python3 -c "
import os
from pathlib import Path

# Split large directory into smaller chunks
base_dir = Path('large_dataset')
chunk_size = 100
chunk_num = 0

for i, img_dir in enumerate(base_dir.glob('*')):
    if i % chunk_size == 0:
        chunk_dir = Path(f'chunk_{chunk_num}')
        chunk_dir.mkdir(exist_ok=True)
        chunk_num += 1
    
    # Symlink to avoid copying
    os.symlink(img_dir, chunk_dir / img_dir.name)
"

# Process each chunk (output goes inside each chunk directory)
for chunk in chunk_*; do
    echo "Processing $chunk..."
    python3 process_and_rename_images.py --execute -i "$chunk" -o "processed_data" --verbose
    # Output is automatically created as $chunk/processed_data/
done
```

### 12. Memory Monitoring

```bash
# Monitor memory usage during processing
python3 -c "
import psutil
import subprocess
import time

# Start processing in background
proc = subprocess.Popen(['python3', 'process_and_rename_images.py', '--execute', '--verbose'])

# Monitor memory
while proc.poll() is None:
    memory = psutil.virtual_memory()
    print(f'Memory usage: {memory.percent}% ({memory.available / 1024**3:.1f}GB available)')
    time.sleep(10)
"
```

## Integration Examples

### 13. Pipeline Integration

```bash
# Part of larger analysis pipeline
#!/bin/bash

echo "🔬 Starting cell analysis pipeline..."

# Step 1: Process and organize images (creates raw_images/processed_images/)
python3 process_and_rename_images.py --execute -i raw_images/ --verbose

# Step 2: Run analysis (example)
# python3 analyze_cells.py --input processed_images/

# Step 3: Generate report
# python3 generate_report.py --data processed_images/processing_summary.json

echo "✅ Pipeline complete!"
```

### 14. Cloud Storage Integration

```bash
# Download from cloud storage
aws s3 sync s3://my-bucket/microscopy-data/ ./raw_images/

# Process images (creates raw_images/processed_images/)
python3 process_and_rename_images.py --execute -i raw_images/

# Upload results
aws s3 sync processed_images/ s3://my-bucket/processed-data/
```

## Best Practices

1. **Always preview first**: Use `--preview` to understand what will happen
2. **Use verbose mode**: `--verbose` provides valuable correlation insights
3. **Monitor disk space**: Processing roughly doubles storage requirements
4. **Backup originals**: Script copies (never moves) original files
5. **Review processing_summary.json**: Contains complete audit trail
6. **Test with small datasets**: Validate workflow before processing large collections
#!/usr/bin/env python3
"""
Combined Image Processing and Renaming Script

This script combines image matching using direct pixel correlation with the timestamp-based
renaming system. It scans directories, finds correct sample/mask pairs, and creates a single
organized output directory with properly named files.

Usage:
    python3 process_and_rename_images.py --preview      # Preview changes
    python3 process_and_rename_images.py --execute      # Execute processing
"""

import os
import glob
import shutil
import json
import numpy as np
import cv2
from scipy.optimize import linear_sum_assignment
from pathlib import Path
import argparse
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from PIL import Image
from PIL.ExifTags import TAGS
from collections import defaultdict
import re
from tqdm import tqdm


class ImageProcessor:
    def __init__(self, base_directory: str, output_directory: str):
        self.base_directory = Path(base_directory)
        self.output_directory = Path(output_directory)
        self.processed_pairs = []
        self.skipped_files = []
        self.errors = []
        
    def find_image_directories(self) -> List[Path]:
        """Find all directories containing sample and mask images."""
        image_dirs = []
        
        # Check if base directory itself has images
        sample_images = list(self.base_directory.glob("sample_image_*.jpg"))
        mask_images = list(self.base_directory.glob("combined_mask_*.jpg"))
        
        if sample_images and mask_images:
            image_dirs.append(self.base_directory)
            
        # Check all subdirectories
        for subdir in self.base_directory.rglob("*"):
            if subdir.is_dir() and subdir != self.base_directory:
                # Skip excluded directories
                if any(excluded in str(subdir) for excluded in ['Initial Test images', 'renamed_images', 'organized_pairs']):
                    continue
                    
                sample_images = list(subdir.glob("sample_image_*.jpg"))
                mask_images = list(subdir.glob("combined_mask_*.jpg"))
                
                if sample_images and mask_images:
                    image_dirs.append(subdir)
        
        return image_dirs
    
    def compute_correlation(self, sample_img: np.ndarray, mask_img: np.ndarray) -> float:
        """Compute direct pixel correlation between sample and mask images."""
        try:
            # Convert mask to RGB if needed
            if len(mask_img.shape) == 3 and mask_img.shape[2] == 4:
                mask_rgb = cv2.cvtColor(mask_img, cv2.COLOR_BGRA2RGB)
            elif len(mask_img.shape) == 3 and mask_img.shape[2] == 3:
                mask_rgb = cv2.cvtColor(mask_img, cv2.COLOR_BGR2RGB)
            else:
                mask_rgb = mask_img
            
            # Resize mask to match sample dimensions
            mask_resized = cv2.resize(mask_rgb, (sample_img.shape[1], sample_img.shape[0]))
            
            # Convert mask to grayscale for correlation
            if len(mask_resized.shape) == 3:
                mask_gray = np.mean(mask_resized, axis=2)
            else:
                mask_gray = mask_resized
            
            # Compute direct pixel correlation
            correlation = np.corrcoef(sample_img.flatten(), mask_gray.flatten())[0, 1]
            return correlation if not np.isnan(correlation) else 0.0
            
        except Exception as e:
            return 0.0
    
    def find_matches_for_directory(self, directory: Path, verbose: bool = False) -> Dict[str, str]:
        """Find matches for images in a single directory using correlation analysis."""
        sample_images = sorted(list(directory.glob("sample_image_*.jpg")))
        mask_images = sorted(list(directory.glob("combined_mask_*.jpg")))
        
        if not sample_images or not mask_images:
            return {}
        
        if verbose:
            print(f"  🔍 Analyzing {len(sample_images)} samples vs {len(mask_images)} masks")
        
        # Create similarity matrix
        similarity_matrix = np.zeros((len(sample_images), len(mask_images)))
        
        # Use tqdm for progress tracking during correlation computation
        sample_progress = tqdm(enumerate(sample_images), total=len(sample_images), 
                              desc=f"    Computing correlations", leave=False, 
                              disable=not verbose)
        
        for i, sample_path in sample_progress:
            sample_img = cv2.imread(str(sample_path), cv2.IMREAD_GRAYSCALE)
            if sample_img is None:
                continue
                
            for j, mask_path in enumerate(mask_images):
                mask_img = cv2.imread(str(mask_path), cv2.IMREAD_UNCHANGED)
                if mask_img is None:
                    continue
                
                correlation = self.compute_correlation(sample_img, mask_img)
                similarity_matrix[i, j] = correlation
        
        # Use Hungarian algorithm for optimal assignment
        if similarity_matrix.size > 0:
            row_ind, col_ind = linear_sum_assignment(-similarity_matrix)
            
            matches = {}
            for i, j in zip(row_ind, col_ind):
                sample_name = sample_images[i].name
                mask_name = mask_images[j].name
                correlation_score = similarity_matrix[i, j]
                matches[sample_name] = mask_name
                
                if verbose:
                    print(f"    {sample_name} ↔ {mask_name} (correlation: {correlation_score:.3f})")
            
            return matches
        
        return {}
    
    def extract_date_from_exif(self, image_path: Path) -> Optional[datetime]:
        """Extract date/time from EXIF data."""
        try:
            with Image.open(image_path) as img:
                exif_data = img._getexif()
                if exif_data is not None:
                    for tag_id, value in exif_data.items():
                        tag = TAGS.get(tag_id, tag_id)
                        if tag in ['DateTime', 'DateTimeOriginal', 'DateTimeDigitized']:
                            try:
                                # EXIF datetime format: 'YYYY:MM:DD HH:MM:SS'
                                dt = datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
                                return dt
                            except ValueError:
                                continue
        except Exception:
            pass
        return None
    
    def get_file_modification_time(self, file_path: Path) -> Optional[datetime]:
        """Get file modification time as fallback."""
        try:
            timestamp = os.path.getmtime(file_path)
            return datetime.fromtimestamp(timestamp)
        except:
            return None
    
    def generate_timestamp_filename(self, file_path: Path, file_type: str, sequential_counter: int) -> Tuple[Optional[str], str]:
        """Generate timestamp-based filename for a file."""
        # Try to get date from EXIF
        date_time = self.extract_date_from_exif(file_path)
        date_source = "exif"
        
        # Fallback to file modification time
        if date_time is None:
            date_time = self.get_file_modification_time(file_path)
            date_source = "file_mtime"
        
        if date_time is None:
            return None, "no_date_available"
        
        # Format: YYYY-MM-DD_HH-MM-SS
        date_str = date_time.strftime('%Y-%m-%d_%H-%M-%S')
        
        # Generate filename with 4-digit sequential counter
        counter_str = f"{sequential_counter:04d}"
        extension = file_path.suffix
        
        if file_type == "sample":
            filename = f"sample_image-{counter_str}_{date_str}{extension}"
        elif file_type == "mask":
            filename = f"combined_mask-{counter_str}_{date_str}{extension}"
        else:
            filename = f"{file_type}-{counter_str}_{date_str}{extension}"
        
        return filename, date_source
    
    def process_all_directories(self, verbose: bool = False, dry_run: bool = True) -> Dict:
        """Process all directories and return summary information."""
        print(f"🔍 Scanning for image directories in: {self.base_directory}")
        
        image_dirs = self.find_image_directories()
        
        if not image_dirs:
            print("❌ No directories found with both sample_image_*.jpg and combined_mask_*.jpg files")
            return {
                "status": "no_directories_found",
                "directories_processed": 0,
                "pairs_processed": 0,
                "files_copied": 0
            }
        
        print(f"📁 Found {len(image_dirs)} directories with image pairs")
        
        if not dry_run:
            # Create output directory
            self.output_directory.mkdir(parents=True, exist_ok=True)
        
        sequential_counter = 0
        total_pairs = 0
        files_copied = 0
        
        # Progress bar for processing directories
        dir_progress = tqdm(enumerate(image_dirs, 1), total=len(image_dirs), 
                           desc="Processing directories", unit="dir")
        
        for i, directory in dir_progress:
            dir_progress.set_description(f"Processing: {directory.name}")
            if verbose:
                print(f"\n[{i}/{len(image_dirs)}] Processing: {directory}")
            
            # Find matches for this directory
            matches = self.find_matches_for_directory(directory, verbose)
            
            if not matches:
                if verbose:
                    print(f"⚠️  No valid matches found in {directory}")
                continue
            
            # Process each matched pair with progress bar
            pair_progress = tqdm(matches.items(), desc="  Processing pairs", 
                               leave=False, disable=not verbose)
            
            for sample_name, mask_name in pair_progress:
                pair_progress.set_description(f"  Processing pair #{sequential_counter:04d}")
                
                sample_path = directory / sample_name
                mask_path = directory / mask_name
                
                # Generate new filenames
                sample_new_name, sample_date_source = self.generate_timestamp_filename(
                    sample_path, "sample", sequential_counter
                )
                mask_new_name, mask_date_source = self.generate_timestamp_filename(
                    mask_path, "mask", sequential_counter  
                )
                
                # Use primary file for date source reporting
                primary_date_source = sample_date_source if sample_new_name else mask_date_source
                
                pair_info = {
                    'sequential_id': sequential_counter,
                    'source_directory': str(directory),
                    'original_sample': sample_name,
                    'original_mask': mask_name,
                    'new_sample': sample_new_name,
                    'new_mask': mask_new_name,
                    'date_source': primary_date_source,
                    'sample_path': str(sample_path) if sample_path.exists() else None,
                    'mask_path': str(mask_path) if mask_path.exists() else None
                }
                
                if dry_run:
                    # Preview mode
                    status = "✓" if primary_date_source == "exif" else "⚠"
                    source = "EXIF" if primary_date_source == "exif" else "File Modified Time"
                    
                    print(f"  {status} Pair #{sequential_counter:04d} - {source}")
                    if sample_new_name:
                        print(f"    📷 {sample_name} → {sample_new_name}")
                    if mask_new_name:
                        print(f"    🎭 {mask_name} → {mask_new_name}")
                else:
                    # Execution mode
                    print(f"  🔄 Processing Pair #{sequential_counter:04d}")
                    
                    # Copy sample file
                    if sample_new_name and sample_path.exists():
                        sample_dest = self.output_directory / sample_new_name
                        if sample_dest.exists():
                            self.errors.append(f"Target exists: {sample_new_name}")
                            print(f"    ⚠️  Skipping {sample_name} (target exists)")
                        else:
                            try:
                                shutil.copy2(sample_path, sample_dest)
                                source_indicator = "📅" if primary_date_source == "exif" else "🕐"
                                print(f"    ✅ {source_indicator} 📷 {sample_name} → {sample_new_name}")
                                files_copied += 1
                            except Exception as e:
                                self.errors.append(f"Copy error for {sample_name}: {e}")
                                print(f"    ❌ Error copying {sample_name}: {e}")
                    
                    # Copy mask file
                    if mask_new_name and mask_path.exists():
                        mask_dest = self.output_directory / mask_new_name
                        if mask_dest.exists():
                            self.errors.append(f"Target exists: {mask_new_name}")
                            print(f"    ⚠️  Skipping {mask_name} (target exists)")
                        else:
                            try:
                                shutil.copy2(mask_path, mask_dest)
                                source_indicator = "📅" if primary_date_source == "exif" else "🕐"
                                print(f"    ✅ {source_indicator} 🎭 {mask_name} → {mask_new_name}")
                                files_copied += 1
                            except Exception as e:
                                self.errors.append(f"Copy error for {mask_name}: {e}")
                                print(f"    ❌ Error copying {mask_name}: {e}")
                
                self.processed_pairs.append(pair_info)
                sequential_counter += 1
                total_pairs += 1
        
        # Close progress bars
        if hasattr(locals(), 'dir_progress'):
            dir_progress.close()
        
        # Create summary file if executing
        if not dry_run and self.processed_pairs:
            summary = {
                "processing_date": datetime.now().isoformat(),
                "source_directory": str(self.base_directory),
                "output_directory": str(self.output_directory),
                "total_directories": len(image_dirs),
                "total_pairs": total_pairs,
                "files_copied": files_copied,
                "errors": self.errors,
                "pairs": self.processed_pairs
            }
            
            summary_file = self.output_directory / "processing_summary.json"
            with open(summary_file, 'w') as f:
                json.dump(summary, f, indent=2)
        
        return {
            "status": "success",
            "directories_processed": len(image_dirs),
            "pairs_processed": total_pairs,
            "files_copied": files_copied,
            "errors_count": len(self.errors)
        }


def main():
    parser = argparse.ArgumentParser(
        description="Process and rename matched image pairs using correlation analysis and timestamp-based naming",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview what will be processed
  python3 process_and_rename_images.py --preview
  
  # Execute processing with verbose output  
  python3 process_and_rename_images.py --execute --verbose
  
  # Process specific directory
  python3 process_and_rename_images.py --execute -i /path/to/images -o renamed_pairs
        """
    )
    
    parser.add_argument(
        '--preview', 
        action='store_true', 
        help='Preview changes without executing them'
    )
    parser.add_argument(
        '--execute', 
        action='store_true', 
        help='Execute the processing and file copying'
    )
    parser.add_argument(
        '--input', '-i',
        default='.',
        help='Input directory to scan for image pairs (default: current directory)'
    )
    parser.add_argument(
        '--output', '-o',
        default='processed_images',
        help='Output directory for processed files (default: processed_images)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output showing correlations and details'
    )
    
    args = parser.parse_args()
    
    if not args.preview and not args.execute:
        print("Error: You must specify either --preview or --execute")
        parser.print_help()
        return 1
    
    if args.preview and args.execute:
        print("Error: You cannot use both --preview and --execute at the same time")
        return 1
    
    input_dir = os.path.abspath(args.input)
    output_dir = os.path.abspath(args.output)
    
    if not os.path.exists(input_dir):
        print(f"Error: Input directory '{input_dir}' does not exist")
        return 1
    
    print(f"🚀 {'PREVIEW' if args.preview else 'EXECUTION'} MODE")
    print(f"📂 Input directory: {input_dir}")
    if not args.preview:
        print(f"📤 Output directory: {output_dir}")
    print()
    
    try:
        processor = ImageProcessor(input_dir, output_dir)
        results = processor.process_all_directories(
            verbose=args.verbose, 
            dry_run=args.preview
        )
        
        # Print summary
        print(f"\\n{'=' * 60}")
        print("SUMMARY")
        print("=" * 60)
        print(f"Directories processed: {results['directories_processed']}")
        print(f"Image pairs found: {results['pairs_processed']}")
        
        if not args.preview:
            print(f"Files copied: {results['files_copied']}")
            print(f"Errors: {results['errors_count']}")
            if results['files_copied'] > 0:
                print(f"\\n📂 All processed files saved to: {output_dir}")
                print(f"📋 Processing summary saved to: {output_dir}/processing_summary.json")
        
        if args.preview:
            print(f"\\n✅ Preview completed! Run with --execute to perform the processing.")
        else:
            print(f"\\n🎉 Processing complete!")
        
    except KeyboardInterrupt:
        print("\\n\\nOperation cancelled by user.")
        return 1
    except Exception as e:
        print(f"\\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
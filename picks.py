#!/usr/bin/env python3
"""
Image optimization tool with multiprocessing support.
See README.md for detailed usage and examples.
"""

import argparse
import os
import sys
from pathlib import Path
from typing import List, Optional, Set, Tuple, Union
from PIL import Image, ImageOps
from tqdm import tqdm
from concurrent.futures import ProcessPoolExecutor, as_completed

# Version
__version__ = "1.0.0"

# Check Python version
if sys.version_info < (3, 7):
    print("Error: Python 3.7 or higher is required")
    sys.exit(1)


def get_image_files(folder_path: Union[str, Path], include_extensions: Optional[Set[str]] = None) -> List[str]:
    """Recursively find all image files in the given folder."""
    default_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}
    
    # Use include_extensions if provided, otherwise use all supported extensions
    if include_extensions:
        image_extensions = include_extensions.intersection(default_extensions)
        if not image_extensions:
            print("Warning: No valid image extensions found in --include filter")
            return []
    else:
        image_extensions = default_extensions
    
    image_files = []

    for root, dirs, files in os.walk(folder_path, followlinks=False):
        for file in files:
            if Path(file).suffix.lower() in image_extensions:
                image_files.append(os.path.join(root, file))
    
    return image_files


def create_destination_structure(target_folder: Path, destination_base: Path, dry_run: bool = False) -> Path:
    """Create the destination folder structure mirroring the target folder name."""
    target_name = Path(target_folder).name
    destination_folder = Path(destination_base) / target_name
    if not dry_run:
        destination_folder.mkdir(parents=True, exist_ok=True)
    return destination_folder


def generate_sequential_name(folder_name: str, index: int, total_count: int, file_extension: str) -> str:
    """
    Generate sequential filename with zero-padding.
    
    Args:
        folder_name: Name of the source folder to use as prefix
        index: Current image index (1-based)
        total_count: Total number of images (for determining padding)
        file_extension: File extension (.jpg, .webp, etc.)
    
    Returns:
        Sequential filename like 'folder-0001.webp'
    """
    # Determine number of digits needed for zero-padding
    digits = len(str(total_count))
    digits = max(digits, 4)  # Always use at least 4 digits
    
    # Format with zero-padding
    number_str = str(index).zfill(digits)
    return f"{folder_name}-{number_str}{file_extension}"


def clean_filename_for_display(filename: str, fixed_length: int = 30) -> str:
    """
    Clean filename for progress bar display with fixed width to prevent bar jumping.
    
    Args:
        filename: Original filename
        fixed_length: Fixed length for consistent progress bar display
    
    Returns:
        Fixed-width cleaned filename safe for terminal display
    """
    # Get just the filename without path
    clean_name = Path(filename).name
    
    # Replace spaces with underscores and remove other problematic characters
    clean_name = clean_name.replace(' ', '_').replace('\t', '_')
    
    # Truncate to max length if needed
    if len(clean_name) > fixed_length:
        clean_name = clean_name[:fixed_length-3] + "..."
    
    # Pad to fixed length to ensure consistent progress bar width
    clean_name = clean_name.ljust(fixed_length)
    
    return clean_name


def process_single_image(args_tuple: Tuple[str, Path, int, int, str, bool]) -> Tuple[bool, str, Optional[str], int, int, bool]:
    """
    Worker function to process a single image. 
    Takes a tuple of arguments for multiprocessing compatibility.
    
    Args:
        args_tuple: (input_path, output_path, max_size, quality, output_format, skip_existing)
    
    Returns:
        (success: bool, input_path: str, error_message: str, input_size: int, output_size: int, skipped: bool)
    """
    input_path, output_path, max_size, quality, output_format, skip_existing = args_tuple
    
    try:
        # Get input file size
        input_size = Path(input_path).stat().st_size
        
        # Check if we should skip existing files
        if skip_existing and Path(output_path).exists():
            output_size = Path(output_path).stat().st_size
            return (True, str(input_path), None, input_size, output_size, True)
        
        # Process the image
        success = optimize_image(input_path, output_path, max_size, quality, output_format)
        if success:
            output_size = Path(output_path).stat().st_size if Path(output_path).exists() else 0
            return (success, str(input_path), None, input_size, output_size, False)
        else:
            return (False, str(input_path), "Processing failed", input_size, 0, False)
    except Exception as e:
        input_size = 0
        try:
            input_size = Path(input_path).stat().st_size
        except Exception:
            pass
        return (False, str(input_path), str(e), input_size, 0, False)


def validate_arguments(args: argparse.Namespace) -> Tuple[Path, Path, int, Optional[Set[str]]]:
    """Validate command line arguments and return validated paths and quality."""
    if args.processes < 1 or args.processes > 16:
        print(f"Error: Number of processes must be between 1 and 16 (got {args.processes})")
        sys.exit(1)

    if not 1 <= args.quality <= 100:
        print(f"Error: Quality must be between 1 and 100 (got {args.quality})")
        sys.exit(1)

    if args.max_size < 1:
        print(f"Error: Max size must be positive (got {args.max_size})")
        sys.exit(1)
    
    # Validate skip-existing only works with keep-names
    if args.skip_existing and not args.keep_names:
        print("Warning: --skip-existing only works with --keep-names flag")
        print("Sequential naming can't reliably map existing files to source files")
        sys.exit(1)
    
    target_path = Path(args.target_folder)
    if not target_path.exists() or not target_path.is_dir():
        print(f"Error: Target folder '{args.target_folder}' does not exist or is not a directory")
        sys.exit(1)
    
    destination_base = Path(args.destination)
    if not destination_base.exists():
        print(f"Error: Destination '{args.destination}' does not exist")
        sys.exit(1)
    
    # Parse include filter if provided
    include_extensions = None
    if args.include:
        include_extensions = {f'.{ext.strip().lower().lstrip(".")}' for ext in args.include.split(',')}
    
    # Adjust default quality for WebP if not explicitly set
    quality = args.quality
    if args.format == 'webp' and quality == 87:  # Default JPG quality
        quality = 82  # Better default for WebP
    
    return target_path, destination_base, quality, include_extensions


def prepare_processing_tasks(args: argparse.Namespace, target_path: Path, destination_folder: Path, quality: int, include_extensions: Optional[Set[str]]) -> List[Tuple[str, Path, int, int, str, bool]]:
    """Prepare all processing tasks and return task arguments list."""
    # Find all image files
    print("Scanning for images...")
    image_files = get_image_files(target_path, include_extensions)
    
    if not image_files:
        print("No image files found in the target folder.")
        return []
    
    # Sort files for consistent sequential numbering
    image_files.sort()
    print(f"Found {len(image_files)} images to process")
    
    # Handle dry-run mode
    if args.dry_run:
        return preview_processing(args, image_files, target_path, destination_folder, quality)
    
    # Pre-generate all task arguments for multiprocessing
    task_args = []
    file_extension = '.webp' if args.format == 'webp' else '.jpg'
    
    for index, input_file in enumerate(image_files, 1):  # 1-based indexing
        # Generate output filename
        if args.preserve_dirs:
            # Preserve subdirectory structure
            rel_path = Path(input_file).relative_to(target_path)
            if args.keep_names:
                output_file = destination_folder / rel_path.with_suffix(file_extension)
            else:
                # Sequential naming but preserve directory structure
                folder_name = target_path.name
                filename = generate_sequential_name(folder_name, index, len(image_files), file_extension)
                output_file = destination_folder / rel_path.parent / filename

            # Security check: ensure output path stays within destination folder
            try:
                output_file.resolve().relative_to(destination_folder.resolve())
            except ValueError:
                print(f"Security error: Output path would be outside destination folder: {output_file}")
                continue
        else:
            # Flatten directory structure (original behavior)
            if args.keep_names:
                # Keep original filename with new extension
                rel_path = Path(input_file).relative_to(target_path)
                output_file = destination_folder / rel_path.name.replace(rel_path.suffix, file_extension)
            else:
                # Generate sequential name
                folder_name = target_path.name
                filename = generate_sequential_name(folder_name, index, len(image_files), file_extension)
                output_file = destination_folder / filename
        
        task_args.append((input_file, output_file, args.max_size, quality, args.format, args.skip_existing))
    
    return task_args


def preview_processing(args: argparse.Namespace, image_files: List[str], target_path: Path, destination_folder: Path, quality: int) -> List[Tuple]:
    """Show preview of what would be processed in dry-run mode."""
    print("\n=== DRY RUN PREVIEW ===")
    print(f"Would process {len(image_files)} images")
    print(f"Format: {args.format.upper()}")
    print(f"Quality: {quality}")
    print(f"Max size: {args.max_size}px")
    print(f"Processes: {args.processes}")
    print(f"Naming: {'Keep original' if args.keep_names else 'Sequential'}")
    print(f"Directory structure: {'Preserved' if args.preserve_dirs else 'Flattened'}")
    if args.skip_existing:
        print("Skip existing: Yes")
    
    # Show first few example outputs
    print("\nExample output filenames:")
    file_extension = '.webp' if args.format == 'webp' else '.jpg'
    
    for index, input_file in enumerate(image_files[:5], 1):
        if args.preserve_dirs:
            rel_path = Path(input_file).relative_to(target_path)
            if args.keep_names:
                output_file = destination_folder / rel_path.with_suffix(file_extension)
            else:
                folder_name = target_path.name
                filename = generate_sequential_name(folder_name, index, len(image_files), file_extension)
                output_file = destination_folder / rel_path.parent / filename
        else:
            if args.keep_names:
                rel_path = Path(input_file).relative_to(target_path)
                output_file = destination_folder / rel_path.name.replace(rel_path.suffix, file_extension)
            else:
                folder_name = target_path.name
                filename = generate_sequential_name(folder_name, index, len(image_files), file_extension)
                output_file = destination_folder / filename
        
        print(f"  {Path(input_file).name} → {output_file.name}")
    
    if len(image_files) > 5:
        print(f"  ... and {len(image_files) - 5} more files")
    
    print("\nNo files will be processed in dry-run mode.")
    return []


def process_images_with_progress(task_args: List[Tuple[str, Path, int, int, str, bool]], args: argparse.Namespace) -> Tuple[int, int, int, int, int]:
    """Process images with progress tracking, supporting single or multi-process mode."""
    if not task_args:
        return 0, 0, 0, 0, 0
    
    successful = 0
    failed = 0
    skipped = 0
    total_input_size = 0
    total_output_size = 0
    
    if args.processes == 1:
        # Single process mode (original behavior)
        with tqdm(task_args, desc="Optimizing images", unit="img") as pbar:
            for task_arg in pbar:
                input_file = task_arg[0]
                display_name = clean_filename_for_display(input_file)
                pbar.set_postfix({'current': display_name})
                
                success, _, error, input_size, output_size, was_skipped = process_single_image(task_arg)
                total_input_size += input_size
                total_output_size += output_size
                
                if was_skipped:
                    skipped += 1
                elif success:
                    successful += 1
                else:
                    failed += 1
                    if error:
                        pbar.write(f"Error processing {input_file}: {error}")
    else:
        # Multi-process mode
        with ProcessPoolExecutor(max_workers=args.processes) as executor:
            # Submit all tasks
            future_to_task = {executor.submit(process_single_image, task_arg): task_arg for task_arg in task_args}
            
            # Process results with progress bar
            with tqdm(total=len(task_args), desc="Optimizing images", unit="img") as pbar:
                for future in as_completed(future_to_task):
                    task_arg = future_to_task[future]
                    input_file = task_arg[0]
                    
                    try:
                        success, _, error, input_size, output_size, was_skipped = future.result()
                        total_input_size += input_size
                        total_output_size += output_size
                        
                        if was_skipped:
                            skipped += 1
                        elif success:
                            successful += 1
                        else:
                            failed += 1
                            if error:
                                pbar.write(f"Error processing {input_file}: {error}")
                    except Exception as e:
                        failed += 1
                        pbar.write(f"Unexpected error processing {input_file}: {e}")
                    
                    display_name = clean_filename_for_display(input_file)
                    pbar.set_postfix({'current': display_name})
                    pbar.update(1)
    
    return successful, failed, skipped, total_input_size, total_output_size


def optimize_image(input_path: str, output_path: Path, max_size: int = 2400, quality: int = 87, output_format: str = 'jpg') -> bool:
    """
    Optimize a single image by resizing if needed and saving in specified format.
    
    Args:
        input_path: Path to input image
        output_path: Path for output image
        max_size: Maximum size for the widest dimension
        quality: Image quality (1-100)
        output_format: Output format ('jpg' or 'webp')
    """
    try:
        with Image.open(input_path) as img:
            # Handle EXIF orientation (auto-rotate images from phones/cameras)
            try:
                img = ImageOps.exif_transpose(img)
            except Exception:
                # If EXIF handling fails, continue with original orientation
                pass

            # Convert to RGB if needed (for PNG with transparency, etc.)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Get current dimensions
            width, height = img.size
            max_current = max(width, height)
            
            # Resize if larger than max_size
            if max_current > max_size:
                # Calculate new dimensions maintaining aspect ratio
                if width > height:
                    new_width = max_size
                    new_height = int((height * max_size) / width)
                else:
                    new_height = max_size
                    new_width = int((width * max_size) / height)
                
                # Resize using high-quality resampling
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save in specified format with optimization
            if output_format == 'webp':
                img.save(output_path, 'WEBP', quality=quality, optimize=True)
            else:  # jpg
                img.save(output_path, 'JPEG', quality=quality, optimize=True)
            
            return True
            
    except Exception as e:
        print(f"Error processing {input_path}: {e}")
        return False


def main() -> None:
    """Main function - orchestrates the image optimization workflow."""
    parser = argparse.ArgumentParser(description='Optimize images by resizing and compressing to JPG or WebP format')
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')
    parser.add_argument('target_folder', help='Source folder containing images to optimize')
    parser.add_argument('destination', help='Base destination folder for optimized images')
    parser.add_argument('--max-size', type=int, default=2400, help='Maximum size for widest dimension (default: 2400)')
    parser.add_argument('--quality', type=int, default=87, help='Image quality 1-100 (default: 87 for JPG, 82 for WebP)')
    parser.add_argument('--format', choices=['jpg', 'webp'], default='jpg', help='Output format: jpg or webp (default: jpg)')
    parser.add_argument('--keep-names', action='store_true', help='Keep original filenames (default: rename to folder-NNNN format)')
    parser.add_argument('--processes', type=int, default=1, help='Number of parallel processes (default: 1, max: 16)')
    parser.add_argument('--dry-run', action='store_true', help='Preview what would be processed without actually converting files')
    parser.add_argument('--skip-existing', action='store_true', help='Skip files that already exist in destination (only works with --keep-names)')
    parser.add_argument('--include', type=str, help='Comma-separated list of file extensions to include (e.g., jpg,png)')
    parser.add_argument('--preserve-dirs', action='store_true', help='Preserve subdirectory structure instead of flattening')
    
    args = parser.parse_args()
    
    # Validate arguments and get paths
    target_path, destination_base, quality, include_extensions = validate_arguments(args)
    
    # Create destination folder structure
    destination_folder = create_destination_structure(target_path, destination_base, args.dry_run)
    print(f"Output will be saved to: {destination_folder}")
    
    # Prepare processing tasks
    task_args = prepare_processing_tasks(args, target_path, destination_folder, quality, include_extensions)
    if not task_args:
        return
    
    # Process images with progress tracking
    successful, failed, skipped, total_input_size, total_output_size = process_images_with_progress(task_args, args)
    
    # Report results with size information
    print("\nOptimization complete!")
    print(f"Successfully processed: {successful} images")
    if skipped > 0:
        print(f"Skipped existing: {skipped} images")
    if failed > 0:
        print(f"Failed to process: {failed} images")
    
    # Size reporting
    if total_input_size > 0:
        def format_size(size_bytes):
            """Convert bytes to human readable format"""
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size_bytes < 1024.0:
                    return f"{size_bytes:.1f}{unit}"
                size_bytes /= 1024.0
            return f"{size_bytes:.1f}TB"
        
        input_size_str = format_size(total_input_size)
        output_size_str = format_size(total_output_size)
        
        if total_input_size > 0:
            compression_ratio = ((total_input_size - total_output_size) / total_input_size) * 100
            space_saved = total_input_size - total_output_size
            space_saved_str = format_size(space_saved)
            
            print("\nSize Summary:")
            print(f"Original: {input_size_str} → Optimized: {output_size_str}")
            print(f"Space saved: {space_saved_str} ({compression_ratio:.1f}% compression)")


if __name__ == '__main__':
    main()
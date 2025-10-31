# Picks - Image Optimization Script

A powerful Python tool for batch image optimization with multiprocessing support. Optimizes images by resizing and compressing to JPG or WebP format while maintaining quality and providing detailed progress feedback.

## Features

- **Smart Resizing**: Resize images larger than specified max dimension (preserves aspect ratio)
- **Format Conversion**: Convert to JPG or WebP format with quality control
- **Multiprocessing**: Parallel processing for faster batch conversion
- **Flexible Naming**: Sequential naming (folder-0001.ext) or preserve original names
- **Directory Handling**: Flatten or preserve subdirectory structure
- **Progress Tracking**: Real-time progress bar with current file display
- **Dry Run Mode**: Preview what would be processed without actually converting
- **Skip Existing**: Resume interrupted jobs intelligently
- **Format Filtering**: Process only specific file types
- **Size Reporting**: Detailed compression statistics and space saved
- **Cross-Platform**: Works on Windows, macOS, and Linux

## Installation

### Requirements
- Python 3.7+
- Pillow (PIL)
- tqdm

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Or install manually
pip install Pillow tqdm
```

### Verify Installation
```bash
# Test that picks can be run
python picks.py --version

# View all available options
python picks.py --help
```

## Usage

### Basic Syntax
```bash
python picks.py SOURCE_FOLDER DESTINATION_FOLDER [OPTIONS]
```

### Simplest Example

Start with the most basic usage - defaults to JPG format with quality 87:
```bash
python picks.py /path/to/photos /path/to/output
```

This creates `/path/to/output/photos/photos-0001.jpg`, `photos-0002.jpg`, etc.

**Note on destination structure**: The script automatically creates a subfolder named after your source folder. For example:
- Source: `/Users/me/vacation`
- Destination: `/Users/me/optimized`
- Output files: `/Users/me/optimized/vacation/vacation-0001.jpg`

### Quick Start Examples

**Basic usage with WebP and aggressive compression:**
```bash
python picks.py /path/to/photos /path/to/optimized --format webp --quality 60 --max-size 2000 --processes 8
```

**Preview without processing:**
```bash
python picks.py /source /dest --dry-run --format webp --quality 60
```

**Keep original filenames:**
```bash
python picks.py /source /dest --format webp --quality 60 --keep-names
```

**High quality JPG with moderate processing:**
```bash
python picks.py /source /dest --format jpg --quality 85 --processes 4
```

**Resume interrupted job:**
```bash
python picks.py /source /dest --format webp --keep-names --skip-existing
```
**Note**: `--skip-existing` requires `--keep-names` flag to work properly, as sequential naming cannot reliably map existing files to source files

**Process only specific formats:**
```bash
python picks.py /source /dest --include jpg,png --format webp --quality 60
# Or with dots: --include .jpg,.png (both formats work)
```

**Preserve folder structure:**
```bash
python picks.py /source /dest --preserve-dirs --format webp --quality 60
```

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `SOURCE_FOLDER` | Source folder containing images to optimize | Required |
| `DESTINATION` | Base destination folder for optimized images | Required |
| `--format` | Output format: `jpg` or `webp` | `jpg` |
| `--quality` | Image quality 1-100 | `87` (JPG), `82` (WebP) |
| `--max-size` | Maximum pixels for widest dimension | `2400` |
| `--processes` | Number of parallel processes (1-16) | `1` |
| `--keep-names` | Keep original filenames | `False` |
| `--dry-run` | Preview without processing | `False` |
| `--skip-existing` | Skip existing files (requires `--keep-names`) | `False` |
| `--include` | Comma-separated list of extensions (e.g., `jpg,png`). Case-insensitive, dots optional | All supported |
| `--preserve-dirs` | Maintain subdirectory structure | `False` |

## Supported Formats

**Input formats**: JPG, JPEG, PNG, BMP, TIFF, TIF, WebP
**Output formats**: JPG, WebP

**Important Notes**:
- **Image Orientation**: EXIF orientation tags are automatically respected. Images from phones/cameras will be correctly rotated.
- **Metadata Loss**: Most EXIF metadata (camera settings, GPS, timestamps) is not preserved in output files. Only orientation is handled automatically.
- **Transparency**: PNG images with transparency will be converted to RGB with a white background when saved as JPG or WebP.

## Platform Notes

**Cross-Platform Compatibility**: This tool works on Windows, macOS, and Linux with Python 3.7+

**Windows-Specific**:
- Use forward slashes `/` or escaped backslashes `\\` in paths
- PowerShell and CMD both work
- Example: `python picks.py C:/Photos C:/Output`

**macOS/Linux-Specific**:
- Paths with spaces should be quoted: `python picks.py "/path/with spaces" /output`
- Check file permissions with `ls -la` if you encounter access errors
- Use `chmod` to fix permission issues if needed

**Path Handling**:
- All platforms: absolute paths are recommended
- Relative paths work but can be confusing with multiple folders

## Performance Tips

### Process Count Guidelines
- **1 process**: Safe for any system, good for testing
- **4 processes**: Good balance for most systems
- **6-8 processes**: Optimal for 8+ core systems
- **10-12 processes**: High-end servers (12+ cores)
- **16+ processes**: The script enforces a maximum of 16 processes as a safety limit. If your machine has more cores and sufficient RAM, you can edit the validation check in `picks.py:138` to increase this limit

### Quality Recommendations
- **WebP**: 60-70 for aggressive compression, 75-85 for high quality
- **JPG**: 70-80 for web use, 85-95 for print/archival
- **Note**: WebP typically produces 25-35% smaller files than JPG at equivalent quality

### Hardware Considerations
- **RAM**: Each process uses ~50-100MB depending on image size
- **CPU**: More processes = higher CPU usage and heat generation
- **Storage**: Ensure destination has sufficient space (check dry-run first)

## Examples by Use Case

### Web Optimization (Aggressive Compression)
```bash
# For web galleries - small files, decent quality
python picks.py /photos /web-gallery --format webp --quality 65 --max-size 1920 --processes 6
```

### Archive Conversion (Balanced)
```bash
# Convert large photo collection with good compression
python picks.py /archive /optimized --format webp --quality 75 --max-size 2400 --processes 8 --preserve-dirs
```

### Print Preparation (High Quality)
```bash
# Resize for print while maintaining quality
python picks.py /raw-photos /print-ready --format jpg --quality 90 --max-size 3000 --processes 4
```

### Mobile Device Sync
```bash
# Optimize for mobile viewing
python picks.py /photos /mobile-sync --format webp --quality 70 --max-size 1600 --processes 6
```

### Batch Resume After Interruption
```bash
# Resume a large batch job that was interrupted
python picks.py /photos /optimized --format webp --quality 60 --keep-names --skip-existing --processes 8
```

## Output

The script provides detailed feedback including:
- File discovery and count
- Real-time progress with current file
- Processing statistics (success/failed/skipped)
- Compression summary with space saved
- Total processing time

Example output:
```
Scanning for images...
Found 3000 images to process
Output will be saved to: /optimized/photos

Optimizing images: 100%|████████| 3000/3000 [03:45<00:00, 13.29img/s]

Optimization complete!
Successfully processed: 2998 images
Failed to process: 2 images

Size Summary:
Original: 5.2GB → Optimized: 522MB (90.0% compression)
Space saved: 4.7GB
```

## Troubleshooting

### Common Issues

**Permission Denied Errors**
- Ensure you have read permissions for source folder
- Ensure you have write permissions for destination folder
- On Linux/macOS, check file ownership with `ls -la`

**Out of Memory Errors**
- Reduce the number of parallel processes (`--processes`)
- Very large images (>20MP RAW files) can use 200-500MB+ per process
- Close other applications to free up RAM

**Corrupted Image Files**
- Corrupted files are automatically skipped with a warning message
- Check the error output to see which files failed
- Try opening problematic files in an image editor to verify

**Progress Bar Display Issues**
- Some terminals may not render the progress bar correctly
- Try running in a different terminal emulator
- Progress continues normally even if display is garbled

**Unicode Filename Handling**
- Python 3.7+ handles Unicode filenames correctly on all platforms
- If issues occur, try renaming files with special characters

**Process Hangs or Freezes**
- Very large images can take significant time to process
- Wait for the current file to complete
- Reduce `--max-size` to speed up processing
- Use `--dry-run` first to estimate processing time

**Filename Collisions**
- When using `--keep-names` without `--preserve-dirs`, files with the same name from different subdirectories will overwrite each other
- Use `--preserve-dirs` to maintain folder structure and prevent overwrites
- Or use sequential naming (default) which guarantees unique names

## Error Handling

- **Corrupted files**: Skipped with warning message
- **Permission errors**: Reported and job continues
- **Insufficient disk space**: Fails gracefully with error message
- **Invalid arguments**: Clear error messages with usage hints

## FAQ

**Q: Does this modify my original files?**
A: No, original files are never modified. The script only reads from the source folder and creates new optimized files in the destination folder.

**Q: Can I convert WebP to JPG?**
A: No, this tool only supports JPG and WebP as output formats. However, WebP files can be used as input and converted to JPG.

**Q: What happens to transparent PNG images?**
A: Transparency is converted to a white background when saving as JPG or WebP, since these formats require RGB mode.

**Q: Is EXIF metadata preserved?**
A: Image orientation (rotation) is automatically handled, but other EXIF data (camera settings, GPS, timestamps) is not preserved in the output files.

**Q: How do I resume an interrupted batch job?**
A: Use `--keep-names --skip-existing` flags together. This will skip files that already exist in the destination folder. Note: sequential naming mode cannot resume jobs.

**Q: Can I use this in automated scripts?**
A: Yes! The script has predictable exit codes (0 for success, 1 for errors) and can be easily integrated into shell scripts or automation workflows.

**Q: Why are some images rotated incorrectly?**
A: Modern versions (1.0.0+) automatically handle EXIF orientation. If you're using an older version, update to the latest release.

**Q: How do I process multiple folders at once?**
A: Use a bash loop:
```bash
for dir in /photos/*/; do
    python picks.py "$dir" /output --format webp --quality 60
done
```

## Contributing

This project is not actively maintained for public contributions. However:

- **Bug Reports**: Please open an issue on GitHub if you find bugs
- **Feature Requests**: Feel free to fork and modify for your needs
- **Pull Requests**: Not being accepted at this time
- **Questions**: Open an issue for usage questions or clarifications

Feel free to fork this project and modify it as you please for your own use.

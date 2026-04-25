# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Duplicate File Finder** tool - detects duplicate files based on file size + content hash, provides GUI to preview and delete.

**Single implementation:**
- `duplicate_finder_ctk.py` - CustomTkinter version with modern glassmorphism design (**fully optimized** for large result sets, supports dark/light theme toggle)

## Architecture

**Detection Strategy:**
1. First pass: group files by size (quick filtering eliminates unique files)
2. Second pass: compute MD5 hash for files with same size (find true duplicates)
3. Result: list of duplicate groups, each with same content

**Key Features:**
- Delete files to Recycle Bin (recoverable)
- Batch delete / quick delete keep-one
- Export JSON report
- File preview (images, text, PDF)
- **Dark/Light theme toggle** - real-time switch, no restart needed
- **Incremental delete update** - delete doesn't require full rescan

## Common Commands

### Run
```bash
pip install -r requirements.txt
python duplicate_finder_ctk.py
```

### Build EXE with PyInstaller
```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name dup-finder duplicate_finder_ctk.py
```

### Validate syntax
```bash
python -m py_compile duplicate_finder_ctk.py
```

## Performance & UX Optimizations in `duplicate_finder_ctk.py`

For large result sets (1000+ duplicate groups):
- **Pagination:** > 50 groups automatically paginated (50 groups per page)
- **Incremental rendering:** 2-3 groups per batch, 16ms interval between batches to keep UI responsive
- **Cancelable rendering:** switching pages cancels previous rendering immediately
- **Lazy loading on expand:** 10-50 files in a group rendered incrementally (5 files per batch)
- **Native Listbox for large groups:** > 50 files uses native Tkinter Listbox (much lighter than CustomTkinter components)
- **Memory management:** expanding creates widgets on demand, collapsing destroys them immediately
- **Incremental delete update:** delete files updates results in-memory, no full rescan needed - instant refresh
- **Live theme switching:** dark/light theme toggle takes effect immediately, no restart required

## Important Notes for Development

- CustomTkinter does **not** allow `width`/`height` parameters in `.place()` method - must specify in widget constructor
- Don't mix `pack()` and `place()` in the same container - causes layout corruption
- All rendering uses incremental batches with 16ms intervals to avoid blocking the UI event loop
- Styling colors are accessed via global `COLORS` dict and getter functions (for theme switching)
- `COLORS` is updated on theme change and full UI rebuild applies new theme

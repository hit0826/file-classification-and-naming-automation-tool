

# File Classification and Naming Automation Tool

This is a Windows local automation tool that organizes messy folders by file format, date, type, and name rules.  
It also renames images, readable documents, and code files by looking at their contents, then can restore the original names from saved history.

폴더 안에 뒤섞인 파일을 버튼 한 번으로 정리하고, 파일 내용까지 보고 이름을 바꾸는 자동화 도구입니다.





https://github.com/user-attachments/assets/b2015bb4-aed8-4e9f-a79f-debcab053762







## What It Does

- Organizes files by detailed format such as `PDF`, `PNG`, `Python`, `Text`, and `HWP`.
- Groups files by date using filename dates first, then modified date when needed.
- Sorts files by large type such as documents, images, code, and videos.
- Sorts Korean and English filenames by first letter or initial.
- Collects previously organized files back into the target folder.
- Renames image files from visible text or simple scene judgment.
- Renames documents from readable text content.
- Renames code files from functions, classes, imports, and role keywords.
- Restores original names for files renamed by the content-based tools.

## Included Files

- `file_organizer_gui.py`: Main GUI application
- `organize_files.py`: Core file organizing engine
- `image_content_namer.py`: Image content-based naming
- `document_content_namer.py`: Document content-based naming
- `code_content_namer.py`: Code content-based naming
- `rules.example.json`: Default organizing rules
- `Preview-Organize.bat`: Preview-only Windows launcher
- `Apply-Organize.bat`: Apply-mode Windows launcher
- `Build-Exe.bat`: Build script for a Windows executable
- `test_organize_files.py`: Unit tests for organizing and naming behavior
- `FileOrganizer_Principle_Interactive.html`: Interactive visual explanation
- `FileOrganizer_Architecture_Map.html`: Architecture visualization

## Requirements

- Windows 10/11
- Python 3.11 or later recommended
- Optional packages for GUI drag-and-drop and image analysis:

```powershell
py -m pip install -r requirements.txt
```

If a packaged `FileOrganizer.exe` is provided in a release, the GUI can run without opening a terminal window.

## Installation

```powershell
git clone https://github.com/hit0826/file-classification-and-naming-automation-tool.git
cd file-classification-and-naming-automation-tool
py -m pip install -r requirements.txt
```

## Run

The simplest GUI run:

```powershell
py file_organizer_gui.py
```

Preview from the command line:

```powershell
py organize_files.py organize "C:\정리할\폴더" --recursive --rules .\rules.example.json --mode smart
```

Apply from the command line:

```powershell
py organize_files.py organize "C:\정리할\폴더" --recursive --rules .\rules.example.json --mode smart --apply
```

Quick Windows launchers:

```powershell
.\Preview-Organize.bat
.\Apply-Organize.bat
```

## Organizing Modes

| Mode | Meaning |
| --- | --- |
| Smart | Group files by detailed format such as PDF, PNG, Python, and HWP |
| Date | Move files into `YYYY\YYYY-MM-DD` folders |
| Type | Group files by broad type such as Images, Code, Documents, and Text |
| Name initial | Sort files by Korean initial, English letter, or number |
| Original return | Collect organized files back into the target folder |
| Image content name | Rename images from visible text or scene judgment |
| Document content name | Rename readable documents from their text content |
| Code content name | Rename source code from its role and symbols |
| Restore original name | Restore names changed by content-based renaming |

## Safety Features

- Dry run is the default for command-line organizing.
- No `.file-organizer-logs` folder is created by default.
- Duplicate names are protected with `_02`, `_03`, and later suffixes.
- Identical duplicate files can be removed safely when switching modes.
- A file type that appears only once can stay in place instead of creating a one-file folder.
- Hidden files, system files, dotfiles, and symbolic links are skipped by default.
- Windows-invalid filename characters are sanitized automatically.

## Example Result

```text
Before
Downloads\
├─ report.pdf
├─ class_33.py
├─ screen_capture.png
├─ memo.txt
└─ model.h5

After smart organizing
Downloads\
├─ PDF\
│  └─ report.pdf
├─ Python\
│  └─ class_33.py
├─ PNG\
│  └─ screen_capture.png
├─ Text\
│  └─ memo.txt
└─ model.h5
```

`model.h5` stays in place when it is the only file of its format.

## Test

```powershell
py -m unittest -v test_organize_files.py
```

The tests cover date sorting, type sorting, mode switching, duplicate handling, content-based naming, Korean/space paths, and original-name restore.

## Folder Structure

```text
.
├─ Apply-Organize.bat
├─ Build-Exe.bat
├─ Preview-Organize.bat
├─ code_content_namer.py
├─ document_content_namer.py
├─ file_organizer_gui.py
├─ image_content_namer.py
├─ organize_files.py
├─ rules.example.json
├─ test_organize_files.py
├─ FileOrganizer_Principle_Interactive.html
├─ FileOrganizer_Architecture_Map.html
├─ requirements.txt
├─ README.md
└─ LICENSE
```

## Notes

This project is designed to run locally on a Windows laptop. It does not require cloud storage, external servers, or paid APIs for the core organizing features.

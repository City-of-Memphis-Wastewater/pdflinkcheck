# Changelog
All notable changes to this project will be documented in this file.
The format is (read: strives to be) based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).



---

## [1.1.15] - 2025-12-11
### Fixed:
- Remove redundant uploading of .whl and .tar.gz from the multiple build. Favor the Ubuntu .whl and .tar.gz.

---

## [1.1.14] - 2025-12-11
### CI: Fix(Permissions) Release Upload
- Grant 'contents: write' permission to the 'attach-to-release' job's GITHUB_TOKEN to fix the artifact upload failure ('Resource not accessible by integration').
- The softprops/action-gh-release action failed with 'Resource not accessible by integration' when attempting to upload build artifacts.
- This was due to the default GitHub Actions token lacking the necessary scope to update a release. The fix explicitly adds the 'permissions: contents: write' block to the 'attach-to-release' job, granting the token sufficient authority to upload the built binaries (EXE, PYZ, etc.).

---

## [1.1.13] - 2025-12-11
### Fixed:
- Assumption in 1.1.12 was wrong, that bash could handle and safely ignore the PowerShell flags for the cp command. Now, in `build.yml`, have two sections `Collect Windows artifacts` and `Collect Unix artifacts`, the first with PowerShell-safe syntax (-ErrorAction SilentlyContinue) and the second with `2>/dev/null || true`, which cannot be used in Windows but is correct for unix systems. The good news is that now all sysmtes have succeeded at least once in Github Actions.

---

## [1.1.12] - 2025-12-11
### Fixed:
- In `build.yml`, Use the PowerShell-safe syntax (-ErrorAction SilentlyContinue) which ensures the step runs successfully on all three operating systems, regardless of which file types were created on that specific runner. This is an alterative to `2>/dev/null || true`, which cannot be used in Windows.

---

## [1.1.11] - 2025-12-11
### Fixed:
- Removed ✅ `\u2705` from build_pyz.py due to Windows CI failure in `.github/workflows/build.yml`.

---

## [1.1.10] - 2025-12-11
### Changed
- **CI Artifact Generation:** Modified the Continuous Integration (CI) workflow (`.github/workflows/build.yml`) to isolate the creation of the Source Distribution (`sdist`) from other artifacts.
    - The general build step now explicitly runs **`python -m build --sdist`** to produce only the `.tar.gz` file for release.
    - This ensures the generic build process does not create a default `.whl` file, which guarantees that the custom PYZ build script (`build_pyz.py`) always generates and uses a fresh, explicitly customized wheel file immediately before packaging the `.pyz` artifact.

### Fixed
- **CI Dependency Failure:** Resolved the CI workflow failure caused by an inability to find the `uv` executable.
    - The redundant dependency installation logic (the **`ensure_dependencies_and_shiv()`** function) was removed from `build_pyz.py`.
    - The custom scripts now rely entirely on the robust, standard `pip install` commands executed by the CI workflow, eliminating the `uv: command not found` error and simplifying the local build scripts.

---

## [1.1.9] - 2025-12-11
### Fixed:
- **Build Workflow:** Remove explicit `shell: bash` declaration from `.github/workflows/build.yml`, to work cross-platform.
- **Build Workflow:** Add `Install project dependencies (for build scripts)` section in `build.yml`, to ensure dependecies are available; dependencies were missing on the first run of `build.yaml`, during `build_pyz.py` when it tried to import `pyhabitat`.

---

## [1.1.8] - 2025-12-11
### Fixed:
- CLI Default Action (GUI Launch): Fixed an issue where running the CLI with no arguments (e.g., `uv run python -m pdflinkcheck.cli`) resulted in a silent exit instead of executing the default GUI launch logic defined in the `main` callback.
    - This was due to a **missing decorator symbol** in `app.callback()` on `def main(ctx: typer.Context)`. The correct decorator syntax `@app.callback()` is now in use.
    - The manual `sys.argv` workaround to launch the GUI is now removed from `src/pdflinkcheck/cli.py` as it is no longer necessary.
    - The detailed investigation into this issue is documented here: [Debugging the CLI Dispatcher, or, The Tale of The Missing @ Symbol](https://github.com/City-of-Memphis-Wastewater/pdflinkcheck/wiki/Debugging-the-CLI-Dispatcher,-or,-The-Tale-of-The-Missing-@-Symbol)

### Changed
- Migrated default CLI application logic from a pure Click implementation back to the preferred Typer implementation in `src/pdflinkcheck/cli.py`.
- Updated `.gitignore` to correctly exclude sandbox and defunct testing files.
- Updated core dependency pins: Typer minimum version is now set to `0.20.0`.

### Added
- Created foundational GitHub Actions workflow (`.github/workflows/build.yml`) for automated testing and releases.

---

## [1.1.7] – 2025-12-11
### Fixed:
- Fix erroneous relative import from build_executable by removing the leading dot.

---

## [1.1.6] – 2025-12-10
### Changed:
- In build_executable.py, change form_dynamic_binary_name() to form_dynamic_name().
- Import form_dynamic_name() from build_executable.py into build_pyz.py, so that the PYZ filename can be associated with it's OS and processir architecture. This is important because the pymupdf package has a corw which is not pure Python, ergo PYZ builds of pdflinkcheck are not cross platform. 

---

## [1.1.5] – 2025-12-10
### Fixed:
- Improve arch and os tagging in build_executable.py by leveraging pyhabitat.SystemInfo().

### Added:
- Add pyhabitat>=1.0.52 to the pyproject.toml as a dependency. This isnthe firsr version which exposes the SystemInfo class in pyhabitat/__init__.py.

---

## [1.1.4] – 2025-12-10
### Added: 
- build_executable.py.
- ci.yml

---

## [1.1.3] – 2025-12-10
### Fixed:
- Reference to GUI screenshot now uses `raw.githubusercontent` format to enable image content on PyPI.

---

## [1.1.1] – 2025-12-10
### Added:
- Add detail to gui command in CLI.
- Add and stabilize build_pyz.py.

Hooray, 1.1.1 indicates a stable public release.

---

## [0.1.5] – 2025-12-10
### Added:
- gui.py, for tkinter gui. Ensure you have `sudo apt install python3-tk tk-dev if using wslg`

---

## [0.1.1] – 2025-12-09
### Added:
- **Initial release** of the `pdflinkcheck` utility for comprehensive PDF link analysis.
- Core functionality to analyze PDF documents using PyMuPDF (Fitz).
- Ability to scan and categorize all links into: **External URIs**, **Mailto Emails**, and **Internal Jumps** (GoTo actions).
- Implemented robust **Anchor Text Extraction** by querying the text within the link's bounding box.
- Introduced a **Link Remnants** section to identify plain text URLs and email addresses that are not currently hyperlinked, flagging them for manual correction.

### Changed:
- Migrated link extraction and `fitz.Rect` manipulation logic to use **explicit coordinate arithmetic** (`rect.x0 - 1`, etc.) instead of version-dependent methods like `rect.from_expanded()`. This ensures maximum compatibility across different PyMuPDF versions.
- Switched Git repository origin from HTTPS to **SSH** for secure, key-based authentication.

### Fixed:
- Resolved coordinate handling errors stemming from non-normalized link rect tuples returned by PyMuPDF.
- Corrected issue where link extraction methods were failing due to missing `fitz.Rect` utility functions in the target environment (e.g., `'Rect' object has no attribute 'from_expanded'`).

### Removed:
- Eliminated reliance on potentially unstable or version-specific PyMuPDF methods for rect expansion.

---

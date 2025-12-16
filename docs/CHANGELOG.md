# Changelog
All notable changes to this project will be documented in this file.
The format is (read: strives to be) based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).


---

## [1.1.31] - 2025-12-15
### Added:
- Add functions form pdflinkcheck.analyze and pdflinkcehck.remnants to pdflinkcheck.__init__ so that functions are available as a library
- Add 'Show License' button to GUI
- Add export options to gui 
- **Export and Logging:** pdflinkcheck/io.py now handles export of the report and the error logging.

### Changed:
- Improved GUI formatting
- Improved report formatting
- By default, max-links is 0 (all), and export format is 'JSON' 

---

## [1.1.30] - 2025-12-15
### Fixed:
- **Automated PyInstaller Artifact Testing:** Correct build_executable.py run_pyinstaller() function to return the resolved final path.
- **Automated Artifact Testing:** Move post-build tests for build_pyz and build_executable into 'try' blocks of their own to see more detailed failure information.

---

## [1.1.29] - 2025-12-15
### Fixed:
- **Automated Artifact Building for Windows:** Correct the build.yml to run build_executable but not build_pyz for Windows.
- **Automated Artifact Testing:** Move post-build tests outside of the 'try' block to see more detailed failure information.

---

## [1.1.28] - 2025-12-15
### Fixed:
- **Artifact GUI testing:** Tkinter is not expected to be available on the github workflow systems, so use pyhabitat.tkinter_is_available() in build_pyz and build_executable to check for the automated GUI testing.

---

## [1.1.27] - 2025-12-15
### Added:
- **GUI Autoclose:** Add autoclose logic to gui, for testing. 
- **Artifact testing:** Add test logic to build_pyz and build_executable, to ensure only functional builds succeed in the CI pipeline.

---

## [1.1.24] - 2025-12-11
### Fixed:
- CI/Workflow: Resolved build errors on the Windows runner by splitting the directory cleanup step and using the native PowerShell command (Remove-Item -Recurse -Force) instead of the Unix rm -rf.
- CI/Workflow: Fixed artifact staging failure (cp: directory dist/upload does not exist) by moving the staging directory creation (mkdir -p dist/upload) to run after the actions/checkout@v4 step, ensuring the directory is available before artifacts are copied.
- CI/Artifacts: Ensured the staging directory creation (mkdir -p dist/upload) is explicitly present in all platform-specific artifact collection steps for maximum robustness.

---

## [1.1.23] - 2025-12-11
### Fixed:
- **ELF File Inclusion:** Linux and MacOS PyInstaller builds were not being copied. This is because they do not have a file extension, which build.yml relied on. 
- Now, the dist/ and build/ folders are wiped in build.yml before building. Then, for non-Windows systems, all files in dist/ are copied except for .whl and .tar.gz, which are handled once on the Ubuntu build.
    - Key known assumptions:
        - The three runners do not share the same directory or file system.
        - ELF binaries have no extension.
- Separate Windows and non-Windows cleaning logic in build.yml

---

## [1.1.21] - 2025-12-11
### Fixed:
- Build: Suppress non-running windows PYZ and requisite BAT for now, in build.yml.
- In build_pyz.py, remove the `--site-packages` flag. This is removed to prevent editable install conflicts.
- In build_pyz.py, remove the  `--python` flag. This is removed for cross-platform robustness.

### Status:
- The Windows BAT did not show up and the Windows PYZ works are neither a gui nor a CLI:

---

## [1.1.20] - 2025-12-11
### Idea:
- Build: Suppress non-running windows PYZ and requisite BAT for now, in build.yml.

### Try:
- Leave the Windows BAT and PYZ on with the `--site-packages` flag but not the `--python` flag.

---

## [1.1.19] - 2025-12-11
### Success:
- Windows EXE performs well. It is true, it does not work as a CLI to print to the console, though commands are accepted, just silent.

### Attempt: 
- The Windows BAT did not show up and the Windows PYZ works are neither a gui nor a CLI:
    - Add line `cp dist/*.bat dist/upload/ -ErrorAction SilentlyContinue` to the Windows section of build.yml, to ensure the BAT is uploaded to the release.
    - In build_pyz.py, remove the `--site-packages` flag. This is removed to prevent editable install conflicts.
    - In build_pyz.py, remove the  `--python` flag. This is removed for cross-platform robustness.

---

## [1.1.18] - 2025-12-11
### Fixed:
- Correct formatting in pyproject.toml for author tables, project.urls section, and remove the gui entry point as a separate command.

### Changed:
- Improved the README.

### Added:
- README section about the AGPL.

---

## [1.1.16] - 2025-12-11
### Fixed:
- Refactoring cli.py to use lazy execution for the pyhabitat GUI check, to increase the speed of PYZ launch. Pyhabitat uses the cache decorator internally, so the check will be non-redundant after the first time.

### Changed:
- Update classifers in pyproject.toml, for accuracy.
- **Favor GUI for PyInstaller Builds:** Add `--noconsole` flag to Pyinstaller command in build_execuable.py. This might render the Typer CLI non-functional when calling binaries from the command line: ergo, for CLI, users are encouraged to use the PYZ, which the binaries will favor a smooth GUI experience without any suprising console window.

### Added:
- Include a BAT in the build_pyz.py, only for Windows. Filename should match the Windows PYZ, plus a "-gui" ending, because that is the purpose.

---

## [1.1.15] - 2025-12-11
### Fixed:
- Remove redundant uploading of .whl and .tar.gz from the multiple builds in build.yml. Favor the Ubuntu .whl and .tar.gz.

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

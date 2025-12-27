# Changelog

All notable changes to this project will be documented in this file.

The format is (read: strives to be) based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---


## [1.1.95] - 2025-12-26
### Changed:
- Function naming; report.run_report_and_validtion() AKA run_report_and_validation(), now reverted back to run_report(), so that the naming scheme fits complement the over arching report.run_report_and_call_exports(). See CHANGELOG 1.1.81.
- Remove the max links feature entirely, from report.py, from the CLI, and from the GUI.
- Adjust the use of Open Report Button - now have two buttons - Open Report JSON and Open Report TXT. Have these buttons greyed out if a report has not been run. They will open the currently known files, which can be a object attribute of the gui class instance. Now that there is a single Run Analysis button with the validation folded in to the singular process, there is no reason to not allow direct file opening of the actual exports, as opposed to generating a tmp file when hitting the **Open Report** button.
- Update report results link count metadata and dictionary schema to be more granular. Do not mix other links with external URI links.

### Fixed:
- Redundant prints to window in report.py, at print_bool instances. Choose - print until hypothetical failure inside of log or print once the buffer is finished, which is cleanest but expects safe. We chose to print the completed buffer after it is converted to a string completion.
- GUI: Improve _set_icon() to try the PNG logo first and then to try the ICO. The ICO is expected to fail on Linux. If both the PNG and the ICO succeed, the ICO will overrride the PNG -this is slightly innefficient, but worth the robustness.
- analyze_pymupdf.py: There is a plus-one page issue, in the pymupdf-based method, not the pypdf-based method.
- Browsing location for MSIX: Ensure msix installation browses in Path.home(), while all else defause to Path.cwd(). If there is a filepath in the text field, it's parent diretory will be used

### Internal:
- pyhabitat.edit_textfile() blocks the current console.
---

## [1.1.94] - 2025-12-26
### Added:
- At long last, a version flag in the CLI.

---

## [1.1.93] - 2025-12-25
### Changed:
- Remove Badge from README until we can test further.
```[![Build MSIX for Microsoft Store](https://github.com/City-of-Memphis-Wastewater/pdflinkcheck/actions/workflows/microsoftstore.yml/badge.svg)](https://github.com/City-of-Memphis-Wastewater/pdflinkcheck/actions/workflows/microsoftstore.yml)
```

---

## [1.1.92] - 2025-12-25
### Fixed:
- Default browse path is now Path.home() rather than Path.cwd(), or in the most recent selection dir.

### Added:
- Microsoft Store updates now automated upon release in CI/CD Actions.

---

## [1.1.91] - 2025-12-25
### Fixed: 
- Correct referneces to CERT_* GitHub Secrets, for the proper GUID for the partner center
- We can now upload to partner center!!
- Remove extraneous print statement checking keys in the report_results dictionary.

### Added:
- build_executable.py: Add **--osx-bundle-identifier** for macOS expecte feature.

---

## [1.1.89] - 2025-12-24
### Fixed:
- Valdiate eror - handle Payment Link as no-page-destination-page. There is one new key and one broken page key which had refeences corrected.
- cli.py and gui.py, force copy when file not found for license and readme. use broad strokes multi file force copy with ensure_data_files_for_build() instead of  ensure_package_license() and the ensure license function. Yhe issue was thsy paths needed to be passed for those internal functions. the ideas was that they wpupd stau modular - the true answer is to use upper case path values in the file, to allow fpr mpdulat exposure but wxpixot internal.use case dpcumentwtipn
pyproject is now copied forcefully as well, though it is not specifically necessary.

### Added:
- ./external/typertree/
- .gitconfig_alias
- validate.py - {"no-destinstion-page":no_destination_page_count} 

---

## [1.1.87] - 2025-12-24
### Fixed:
- Revert CN value in AppxManifest.xml to match my self signed cert. I was getting error code 0x8007000b, because i had preemtively changed the CN value to match my MSIX requirements for my Partner Center upload. 

### Internal:
- Signing Error 0x8007000b information: https://learn.microsoft.com/en-us/windows/win32/appxpkg/how-to-sign-a-package-using-signtool?redirectedfrom=MSDN

---

## [1.1.86] - 2025-12-23
### Fixed:
- Ensure ctypes.windll in gui.py is only called on windows

---

## [1.1.84] - 2025-12-22
### Added:
- Implement the microsoftstore.yml github flow - ensure that it builds; all i need now is to download a .cer file distributed by [Partner Center](https://partner.microsoft.com/en-us/dashboard), rather than using my own local .cer file.
- Set up local Assets/ directory, with AppxManifest.xml and the logo files.
- Update AppxManifest.xml to match the values from Partner Center.

### Changed:
- Try to get the GUI to pop up in front, by using tricks in Tkinter. Remove the Extensions section in the AppxManifest.xml that has been created for this purpose.

### Internal:
- Download the .msix generated by the Github microsoftstore.yml action, and run it locally; the only issue is that it didn't come to the foreground, and apparently it is associated with the wrong .cer.
- Do glorious battle setting up Partner Center for my onmicrosft.com account and for the elevated guest outlook.com account

---

## [1.1.83] - 2025-12-22
### Changed:
- In the GUI, to add the Development label, check that the gui is not being called as part of a PyInstaller build.
- In the GUI, to not add the Development label, check if the gui is being called from a PYZ - this is probably overkill, because a PYZ s not expected to carry a .git directory, which is a check that is already completed.

### Added:
- .github/workflows/microsftstore.yml

### Internal
- Wrestle with `MSIX Packaging Tool`. Microsoft Store, here we come.

---

## [1.1.81] - 2025-12-22
### Added:New-SelfSignedCertificate `
  -Type Custom `
  -Subject "CN=YourAppName" `
  -KeyUsage DigitalSignature `
  -FriendlyName "MSIX Signing Cert" `
  -CertStoreLocation "Cert:\CurrentUser\My" `
  -KeyExportPolicy Exportable `
  -HashAlgorithm sha256 `
  -KeyLength 2048 `
  -Provider "Microsoft Enhanced RSA and AES Cryptographic Provider"

- I Have Questions.md, to src/pdflinkcheck/data, to help explorers find answers.
- Add a dropdown button to the Tools dropdown in gui.py, to show I Have Questions.md. Call it "I Have Questions". 
- Add function run_report_and_call_exports(), which is now called as the primary entry point at the high level points in the CLI, in the GUI, and in the analyze_*.py main blocks, rather than run_report()
- pdflinkcheck.environment.assess_default_pdf_library(), to ascertain the suggested default PDF engine n CLI help for the analyze command.

### Changed:
- build_executable.py: Change **--noconsole** flag in PyInstaller build to **--windowed**, to use the GUI subsystem bootloader and avoid the quick console popup on  which happens with the **--noconsole** flag.
- run_report() is now called run_report_and_validtion() for clarity. We can change stuff  (library function names) later as it settles in.

### Removed:
- 'sv-ttk' optional dependecy from pyproject.toml - this is a forest theme family now. Remove now-excessive sun-valley-theme-relevant code from gui.py. Ensure there are no references to "[gui]" in the README, etc. 

---

## [1.1.80] - 2025-12-22
### Changes:
- CLI env command -> CLI tools command
- Licensing: Create a purpose built LICENSE file which references the other two LICENSE-MIT and LICENSE-AGPL3 files.

### Added: 
- pyproject.toml: Add "License :: OSI Approved :: MIT License" as an additonal OSI to existing the AGPL3+, because portions of the code use the AGPL3+ and other portions use the MIT.
- Add help str to tools (formerly env) CLI command

---

## [1.1.79] - 2025-12-22
### Added:
- Custom ICO file: red_pdf_512px.ico. The GUI looks great.

### Changed:
- Tree Help -> Help Tree

### Internal:
- Screen shot the versioned Help Tree and the GUI and update the references in the README.

---

## [1.1.78] - 2025-12-22
### Changed:
- GUI improvement: Keep sv_ttk and also implement the files for the forest theme (https://github.com/rdbende/Forest-ttk-theme).
- GUI improvements: Five way theme toggling!
- GUI improvements: No, only forest-dark and forest-light is better. KISS.

### Added:
- environment.py: Cache the availability of fitz. Enable cache clearing through the GUI Tools > Clear Cache and also through the env command in the CLI.
- GUI Menu item, Tools.

### Fixed:
- Better messaging and behavior if PyMuPDF is not available, and if it is selected. Default to pypdf at load if not pymupdf_is_available().

### Internal:
- We still need to fix the incorporation of the validation logic and logs into the run_report() function, and to have combined behavior. One TXT, on JSON (which carries the two separate sections of TXT, initial analysis and the validation summary).

---

## [1.1.77] - 2025-12-21
### Changed:
- gui.py: Implementation of sv_ttk
- gui.py, report.py: Improve error messaging if PyMuPDF is selected but is not available.

### Fixed:
- Move run_report() import in the analyze_*.py functions to inside of the __main__ loop, for better flow of the program flow chart and mitigating the risk of circular import. 

---

## [1.1.76] - 2025-12-21
### Changed:
- Simplify: Adjust gui, remove the validate button. the logic should handle the combination of the validation json and txt summary into tje existing report structure and txt.
- CLI: Adjust validate CLI commant to print both the initial analysis and the validation reports.

### Internal:
- To Do: If a report with a potentially identical name if found in the export directory, use a file naming bump like " file (2).txt ", etc.
---

## [1.1.74] - 2025-12-20
### Fixed:
- Improve empty returns in edge cases for report.py, so that they can handled by the server cleanly.

---

## [1.1.73] - 2025-12-20
### Added:
- SEP_COUNT=28, variable implemented in report.py and validate.py.

---

## [1.1.72] - 2025-12-20
### Fixed:
- Fix missing comma in run_validation() call in gui.py

---

## [1.1.70] - 2025-12-20
### Changed:
- Compress Windows EXE to ZIP before copying for upload, for speed.
---

## [1.1.68] - 2025-12-20
### Fixed:
- Hunting down errors in buil_pyz.py

---

## [1.1.65] - 2025-12-20
### Changed:
- Migrate to a uv_build build system, away from hatchling.

---

## [1.1.64] - 2025-12-19
### Fixed:
- validate.py: Add keys to the assessment for granularity and accuracy.
- validate.py: Move original, unused run_validate() version from report.py to alidate.py and assign placeholder function name run_validation_more_readable_slop().
- validate.py: Correct references to run_validate() in the analyze_*.py files.

## Added:
- validate.py: Add export for validation report, leveraging io.py.
- cli.py: Add export option to `validate` CLI command.
- gui.py: Add `▶ Run Validate` button and `_run_validation_gui()` function to GUI.

---

## [1.1.63] - 2025-12-19
### Fixed:
- GUI: sv_ttk fails on macos. put inside a try block.

---

## [1.1.62] - 2025-12-19
### Fixed:
- Handle invalid headers and also missing EOF blocks, for scans without links.

---

## [1.1.61] - 2025-12-19
### Fixed:
- Favicon handling error, missing return -> now favicon errors are silent, and the missing return above is fixed.

---

## [1.1.60] - 2025-12-19

### Added

- New `validate` CLI command that performs validation of internal GoTo links, remote GoToR file references, and TOC bookmark targets
- New `serve` CLI command that starts a pure-stdlib HTTP server for browser-based PDF upload and analysis
- New `validate.py` module with reusable validation logic
- Support for direct validation testing via `python -m pdflinkcheck.validate`
- Handling for browser favicon requests in the web server to reduce extraneous 404 log entries

### Changed

- Updated server HTML form for clarity and usability
- Improved validation handling of page numbers stored as strings when using the `pypdf` engine
- Updated README with documentation for the new `serve` and `validate` commands
- Minor adjustments to exposed imports in `__init__.py`

### Internal

- To Do: Solve incorrect validation failures when internal destination pages were returned as strings by `pypdf`


---

## [1.1.59] - 2025-12-18
### Fixed:
- `build_pyz.py`: Managed Shiv command based on if the platform is Termux or not.
- `__init__.py`: Change import reference from analyze_pypdf to analyze_pypdf_v2 in __init__.py. I need to choose the defacto and delete the dfunct version, but I havent taken the time to perform the rigorous oversight.

### Changed:
- build_executable.form_dynamic_name() adjusted to no longer include "-PyMuPDF" if that package is included in the build. 
- Update the README to indicate the assumption that PyMuPDF is included in all artifacts except for ones built on Android.

### Internal
- To Do: Validation logic:
    - Check if file references exist relative to PDF path, and if page numbers are reasonable based on file length.
    - Check if GoTo link page numbers are reasonable based on file length.

---

## [1.1.58] - 2025-12-18

### Added

* **TXT Export Support:** Introduced plain text (`.txt`) as a valid export format in both the CLI and GUI, providing a lightweight, human-readable alternative to JSON.
* **Privacy-Aware Pathing:** Implemented `get_friendly_path()` utility to sanitize printed file paths, protecting developer/user directory privacy in logs and console output.
* **Enhanced TOC Reporting:** Integrated structural Table of Contents (TOC) handling into the final report generation for better document navigation analysis.

### Changed

* **PyMuPDF Installation Policy:** Transitioned from a hard-coded block on ARM/Linux to a "permissive attempt" model. Users on any system can now try to install the `full` extra, with clear guidance provided if the build fails on mobile hardware.
* **CLI Robustness:** Improved `run_report()` error messaging to provide actionable `uv sync` or `pip` commands when a user explicitly selects an unavailable PDF library.
* **GUI Error Handling:** Upgraded the Analysis GUI to use rich traceback information for unexpected failures, displayed via a dedicated red-text `_display_error` state-aware method.
* **Refined Build Logic:** Updated `build_executable.py` to intelligently toggle the `--noconsole` flag based on Tkinter availability (via `pyhabitat`), ensuring functional console output on Termux.
* **Library Fallback Terminology:** Standardized "Engine" and "Library" wording across reporting logs for consistent technical communication.

### Fixed

* **GUI Configuration:** Resolved an issue where the TXT export checkbutton was not properly linked to the analysis execution logic in the Tkinter interface.
* **PEP 508 Compliance:** Corrected environment marker syntax in `pyproject.toml` to ensure successful `uv sync` operations across heterogeneous hardware (WSL2 vs. Termux).

### Internal

* Cleaned up and optimized `analyze_pypdf.py` (v2) with spatial anchor text extraction logic using the `pypdf` visitor pattern.
* Verified cross-platform dependency resolution for `ruff` and `shiv` across `x86_64` and `aarch64`.

---

## [1.1.57] - 2025-12-18
### Added
- GUI Failure in Tkinter: Clear console.print() in GUI failure section concerning Tkinter compatibility
- README for help-tree: Add documentation for the `DEV_TYPER_HELP_TREE` env var in the easter egg section of the README.

### Learned
- To test on Termux snd not include ruff, run `uv sync --no-dev`

---

## [1.1.56] - 2025-12-18
### Added
- **Environment Variable Configuration:** Added support for `PDFLINKCHECK_ANALYZE_PDF_LIBRARY` to allow persistent user preferences without repetitive flagging.
- **Strict CLI Validation:** Implemented `Literal` type hinting for `--pdf-library` and `--export-format`, providing automatic validation and better help menu clarity.
    
### Changed
- **Version Discovery Logic:** Updated `version_info.find_pyproject()` to prioritize the developer root `pyproject.toml` over the packaged data file, ensuring local development reflects the correct versioning.
- **GUI Layout Refinement:** Reorganized the control panel into a three-column grid to resolve frame overlap issues between PDF Library selection and Export settings.
- **Action Row UX:** Expanded the "Run Analysis" button to span two columns and increased the "README" button width for better visual balance and accessibility.
- **CLI Command Names:** Renamed internal CLI functions (e.g., `analyze_pdf`) and command names for better maintainability.
    
### Fixed
- **Reporting Hints:** Corrected the "Max Links" hint logic within the generated reports to accurately reflect brevity settings.

### Internal Note for 1.1.56/1.1.57 transition:
> **To-Do:** Clean up `analyze_pypdf.py`, verify `__init__.py` compatibility, and refresh the `README` before the next major push to `main`.

---

## [1.1.55] - 2025-12-17

### Added

* **Multi-Engine PDF Support:** Integrated `pypdf` as the primary, lightweight PDF analysis engine alongside `PyMuPDF`.
* **Dynamic Library Selection:** - **CLI:** Added support for selecting the backend engine via flags. Default behavior now utilizes `pypdf`.
* **GUI:** Implemented a library selection interface allowing users to toggle between engines.


* **Dependency Management:**
* Transitioned `pymupdf` to an `optional-dependency` (extra: `full`) to minimize core installation footprint.
* Implemented PEP 735 `[dependency-groups]` for development tools (`ruff`, `pytest`, `pyinstaller`).


* **Build System Evolution:**
* Migrated build backend to `hatchling`.
* Implemented `datacopy.ensure_package_pyproject()` to force-include `pyproject.toml` into `src/pdflinkcheck/data/` for runtime version discovery.


* **Reporting Enhancements:**
* New `report.py` module created to handle centralized analysis orchestration.
* Improved string and log handling within the reporting pipeline.
* Added the active PDF library name to export filenames for better traceability of results.

### Changed

* **Major Refactor:** - Renamed `run_analysis()` to `run_report()` and migrated it to the new `report.py`.
* Isolated engine-specific logic into `analyze.py` (PyMuPDF) and `analyze_pypdf.py` (pypdf).
* `pypdf` implementation optimized for URI long-name extraction, outperforming the previous implementation in specific edge cases.
* GUI Export Format Selection: Now each filetype has its own checkbox, rather than a report or not report checkbox with a combo box for slecting a single file type. TXT is currently greyed out and desaled until it is supported. 


* **Internal Versioning:** Updated `version_info.py` to successfully resolve project versions during `hatchling` builds.
* **User Interface:** Default behavior across both CLI and GUI now defaults to the `pypdf` engine for improved portability.

### Removed

* **Remnant Checking:** Completely stripped all "check remnants" functionality and options from the CLI, GUI, and analysis engines to focus on the core link-checking use case.
* **Mandatory PyMuPDF:** Removed `pymupdf` from the required dependencies list to allow for Termux-compatible "slim" installs.

### Fixed

* **Build Reliability:** Resolved issues where `version_info` would fail to locate version strings during automated `uv` or `hatch` build processes.
* **Package Integrity:** Fixed missing `pyproject.toml` inclusion in distributed wheels by implementing a force-copy artifact strategy in `datacopy.py`.

---

## [1.1.54] - 2025-12-16
### Added / Changed:
**Link and TOC analysis functions:**
    - Rename analyze.extract_links() to analyze.extract_links_pymupdf(). 
    - Rename analyze.extract_toc() to analyze.extract_toc_pymupdf(). 
    - All four of these now appear in __init__, like 'from pdflinkcheck.analyze import extract_links_pymupdf as extract_links # to expose functions referred to in README'. 
    - Also add extract_links_pypdf() and extract_toc_pypdf() to __init__ and to __all__. 
    - This helps with troubleshooting in the REPL, to compare the pymupdf results to the under-development pypdf results.
**pdflinkcheck.dev.help_tree_command():**
    - Add dev.py file to represent the add_help_tree(). Reference this in cli.py, to safely include the experiemental help_tree CLI command. License dev.py as MIT-licensed internally. 

---

## [1.1.53] - 2025-12-16
### Fixed:
- Added clarity and handling for the `--export-format` option for the `analyze` CLI command.

---

## [1.1.52] - 2025-12-16
### Fixed: 
- Erroneous import of `ensure_data_files_for_build` in build_executable.py; remove excessive parentheses.

### Changed:
- Versioning: `src/pdflinkcheck/version_info.py` created, with versioning functions from `build_executable.py` and `build_pyz.py` migrated to `version_info.py`
- Analysis report order changed so that most aesthetic and immediately useful information is at the top.
- Adjust Gui screenshot reference in 

### Added:
- GUI Version: Version info added to frame heading of the Tkinter gui, by leveraging `version_info.get_version_from_pyproject()`
- GUI Buttons: Top and Bottom.
- Asset: `assets/pdflinkcheck_gui_v1.1.51.png`; update GUI screenshot reference in README.
- Asset: `assets/pdflinkcheck_cli_v1.1.51.png`; add CLI screenshot reference in README.
- CLI versioning: Import version_info into cli.py and add version number to help print statment.
- CLI Tree Help: New CLI command to show the entire CLI structure.

---

## [1.1.50] - 2025-12-16
### Added:
- GUI: Readme button in Tkinter GUI. Strip the glyphs but otherwise accept the markdown formatting.
- src/pdflinkcheck/datacopy.py: `ensure_data_files_for_build()` is defined, to be called manually or automatically for copying LICENSE and README.md from root to the pdflinkcheck/data/ directory for package inclusion. 
- src/pdflinkcheck/datacopy.py: `ensure_data_files_for_build()` is called in build_pyz.py, build_executable.py, and in publish.yml to ensure proper files at build time.
- hook-pdflinkcheck.py: PyInstaller expected hook file added to ensure success of data/ files inclusion.  

### Changed:
- CLI: `license` command is not `docs` command, with `--license/-l` and `--readme/-r` flags.

### Fixed:
- LICENSE is now purely the suggested AGPL template, so that GitHub picks up on the type.
- Copyright for `pdflinkcheck` is now declared at the bottom of the README and in the __init__ file.

---

## [1.1.49] - 2025-12-16
### Fixed:
- Revert page numbering correction factor to use +1
- Revert / unsuppress `self.text_widget.update_idletasks()`, for immediate feedback when a new file is checked.

### Added:
- Tkinter Copy Path button, because copying the selection does not work manually as expected.
- GUI Row 0 Frame: Tkinter row 0 has nicer spacing when using a ttk.Frame() for the file selection.

---

## [1.1.47] - 2025-12-16
### Fixed:
- **Reporting Accuracy:** All reports containing internal page jumps (TOC links, table references, etc.) now show the correct destination page number. Previously, these links were incorrectly reported as pointing to the following page (e.g., a link to page 57 was reported as page 58). This is now fixed across all inspected files.
- ** fitz.Point object serialization:** analyze.serialize_fitz_object() helper function implemented to avoid unexpected IO errors that result in analysis failure.

---

## [1.1.46] - 2025-12-16
### Fixed:
- analyze.py: Remove redundant call to get structural_toc
- analyze.py: Add hint when there is no PDF file in run_analysis()
- __init__.py: Clean up order and guarding of the easter egg and the __all__ definition.

### Added:
- README: Section concering the start_gui() easter egg library function, unlocked by an env var.

---

## [1.1.45] - 2025-12-16
### Added:
- Easter egg: Add elements to the pdflinkcheck/__init__.py, to enable start_gui() to be imported as a library function if the `PDFLINKCHECK_GUI_EASTEREGG` env var is set.

---

## [1.1.44] - 2025-12-16
### Added:
- Add detail to compatibility section in README explaining our typical Termux compatibility goals.

---

## [1.1.43] - 2025-12-15
### Changed:
- PyMuPDF does not (easily) build on alpine. change to a py3.11-slim build.

---

## [1.1.40] - 2025-12-15
### Added:
- **Dockerization:** docker.yaml in github workflows and Docker.multi-dev in root, basically copied from the pyhabitat repository. This is meant to build on tag push.

---

## [1.1.39] - 2025-12-15
### Added:
- Update license information to include links to dependency source code.

---

## [1.1.38] - 2025-12-15
### Added:
- README: Update the GUI to include the license command and the gui command features. 
- README: Document the library commands.

---

## [1.1.37] - 2025-12-15
### Fixed:
- Remove `--include` flag from shiv call and hope for the best for the LICENSE file.
- Adjust path reference to LICENSE and README.md in Pyinstaller.

---

## [1.1.35] - 2025-12-15
### Fixed:
- Implement `assured_auto_close_value` in cli.gui_command() to handle the typer.OptionInfo type given a call of gui_command() from main().

---

## [1.1.34] - 2025-12-15
### Added/Fixed:
- `src/pdflinkcheck/data/LICENSE`, to be included in the wheel. Use this version with the gui.py code, so that it functions with the pipx installed CLI-launched GUI.

### Fixed:
- Use explicit flag `--include` in Shiv command, instead of short `--i`, which might default to `--index-url`.
- Correct erroneous quotation in pyproject.toml

---

## [1.1.32] - 2025-12-15
### Added:
- MANIFEST.in file, to ensure inclusion of README and LICENSE files.
- Sections in build_pyz.py and build_executable.py to  inclusion of README and LICENSE files. 

### Fixed: 
- Use 0 to mean no auto closure for GUI, rather than None.

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

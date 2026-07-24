# Changelog

All notable changes to this project will be documented in this file.

The format is (read: strives to be) based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

### Internal:

- I need to add a TargetDescription enum, for target_description in the JSON structure.
- So that I can have 'target' be consistent key rather than some that say: destination_page or url or filename or whatever kind of target.

---

## [1.5.10] - 2026-07-24
### Added:
- Flatpak versioned naming.
- No interactive password usage for CER file
- Versioned naming for CER and MSIX

---

## [1.5.9] - 2026-07-24
### Added:
- Fix placement of ondir _internal in build.yml
- Attach .cer to msix release

---

## [1.5.8] - 2026-07-02
### Added:
- flatpak manifest YAML in root and related github runner .github/workflows/flatpak.yml
- flatpak theory brought in from copy-n-launch-xlsx

---

## [1.5.7] - 2026-06-19
### Changed:
- Implement LinkValidationResult and MetricKey classes in validate.py.

---

## [1.5.6] - 2026-06-19
### Changed:
- create_link_dict() standardized for all three engines.
- SourceKindPyPDF class implemented for clear documentation.
- JSON data structure altered to include GUID, details, validation, and risk sections.

---

## [1.5.5.11] - 2026-06-18
### Fixed:
- msix.yml runner should fail if the windows build from build.yml / build_executable.py fails.
- 'uv pip install pyinstaller' added to build.yml, for peace of mind; this command also works on termux, which 'uv add pyinstaller' does not, strange.
---

## [1.5.5.10] - 2026-06-18
### Fixed:
- 'build' should be called through uv
- Improve runner diagnostics which are failing to find dest executable files.

---

## [1.5.5.9] - 2026-06-18
### Fixed:
- Dear lord. Don't touch pip or use the --system flag. 'uv sync --extra pdfium --group dev'
- Leverage uv more in build_pyz.py.

---

## [1.5.5.8] - 2026-06-18
### Fixed:
- 'pyinstaller' -> 'sys.executable, "-m", "PyInstaller"' in build_executable.py.

---

## [1.5.5.7] - 2026-06-18
### Fixed:
- '--all-groups' ->  '--group dev' for 'uv pip install ...'

---

## [1.5.5.6] - 2026-06-18
### Fixed:
- Use 'astral-sh/setup-uv@v7' in all YML runners, rather than 'pip install uv'

---

## [1.5.5.5] - 2026-06-18
### Fixed:
- Fix cli.py reference, as __main__, in build_executable.py, so that relative refs are allows in the source code
- build.yml GitHub runner updated for pure uv and pyproject.toml group dep handling.

---

## [1.5.5.4] - 2026-06-18
### Changed:
- Pull Dependabot commit for updating runners, to local main branch. Merge with dev branch.

---

## [1.5.5.3] - 2026-06-18
### Fixed:
- Windows builds are hanging; drop CI CLI checks for runners, in build_executable.py. (This worked).

---

## [1.5.5.2] - 2026-06-18
### Fixed:
- Ensure the Docker build has a current extra reference and that it is MIT compliant.
- Remove references to [full] in favor of explicit [pdfium,pymupdf].

---

## [1.5.5] - 2026-06-18
### Changed:
- We now claim to be MIT licensed. See NOTICE file for details, but otherwise, the project contains no AGPL3+.
- Adjust github YML runners accordingly, to not include PyMuPDF in the builds that will be attached to releases.

### Internal:
- Create a separate repository for AGPL3+ licensing. The Microsoft Store Version should ultimately be AGPL3+.

---

## [1.5.4] - 2026-06-17
### Changed:
- Standardize LinkType enum class usage across all three PDF engines.
- Add magic keys to validate.py to elucidate differentiable results. 
- Allow only one --engine flag to be used in the CLI; remove list functionality.
- Ping machination improved.
- PageValidationResult implemented in validate.py.

---

## [1.5.3] - 2026-06-16
### Changed:
- helptree improved with typer-helptree 0.2.10.5
- Validation fleshed out for various valid cases, "valid" not being grandular enough, and refactored for modular function usage.

---

## [1.5.1beta] - 2026-06-06
### Changed:
- Canary: Ping, call not actually made.
-  ping.ping_url(), PingUrlResult

### Internal:
- web-ping-* not implemented yet locally, push from Dell.

---

## [1.4.4] - 2026-06-05
### Changed:
- Logging improvements, for application.
- Loggers are now defined in logging_setup.py.
- Paths are now defined in paths.py

---

## [1.4.3] - 2026-05-28
### Fixed:
- Corrected variable error in get_structural_toc()
- Corrected GUI checkbox code to check each TK boolean var to convert to enum safely.
- Add click>=8.1.8 as a dep.

---

## [1.4.2] - 2026-05-21
### Changed:
- Include in __init__: ExportFormat, PdfEngine, ReportRequest, PageRef
- Change recently added safe report.run_report(request:ReportRequest) to run_report_request() for clarity; pdflinkcheck.run_report() is already available as a renaming of report.run_report_and_call_exports()

---

## [1.4.1] - 2026-05-21
### Changed:
- Use ExportFormat flag enum, PdfEngine flag enum, and ReportRequest dataclass to represent stable, defensive forms.

---

## [1.3.48] - 2026-05-18
### Fixed:
- __init__.py  improved to use lazy loading and modern 3.7+ standards.
 
---

## [1.3.47] - 2026-03-26
### Fixed:
- Increase pyhabitat to 1.2.6, which handles on_termux() for Python 3.13 properly.

### Changed:
- Make the helptree cli entry not hidden.
- Updated `--help` image in README, which now includes helptree.

---

## [1.3.46] - 2026-03-11
### Fixed:
- Increase pyhabitat to 1.2.3, which now has better handling for launching file explorer from WSL, in launch.show_system_explorer()

### Changed:
- Improve caching in publish.yml, to use `cache-dependency-glob: "pyproject.toml"`, to avod error message regarding missing uv.lock file.

### Added:
- ./scripts/update_index_version.sh copied from dworshak for udateing the helptree reference in README; this should become a part of the typer-helptree package.

---

## [1.3.45] - 2026-03-08
### Fixed:
- README usage of typer-helptree no longer should reference outdated DEV_TYPER_HELPTREE env var.
- Use SVG helptree image now, and update reference in README.
- Increase typer-helptree dep version to v0.2.6.

---

## [1.3.43] - 2026-01-26
### Fixed:
- Update spelling error in I have Questions and Improve the Termux blurb.

### Changed:
- Increase typer-helptree version to 0.1.10, with form add_typer_helptree(app, console, version=__version__, hidden=True), to pass in __version__ from the consuming program (this one, pdflinkcheck)

---

## [1.3.42] - 2026-01-26
### Changed:
- Implement is_in_dev_environment() to use new tri-state pyhabitat.is_in_git_repo()
- Bump pyhabitat version to 1.1.35

---

## [1.3.41] - 2026-01-25
### Fixed:
- Ensure MSIX build can upload to GitHub release.

---

## [1.3.40] - 2026-01-25
### Changed:
- '--windowed' PyInstaller flag will only be used in the precise scenario targeting MSIX.
- Add MSIX upload to release
- Add SHA256 checksum to MSIX notes 

---

## [1.3.39] - 2026-01-25
### Added:
- Add print to GUI console (after redirect) to confirm that analysis is running, especially when slow.

### Changed:
- Get rid of duplicated logic for default engine selection in GUI; leverage the environment.assess_default_pdf_library() function. 

---

## [1.3.38] - 2026-01-25
### Changed:
- analysis_pdfium.py anchor text improved.

---

## [1.3.37] - 2026-01-25
### Changed:
- Dynamic versioning based on VERSION

### Fixed:
- In analyze_pymupdf.py, correct 'pymupdf is None' -> 'fitz is None'

---

## [1.3.36] - 2026-01-24
### Changed:
- "Clear All Caches" button in GUI changed to "Recheck PDF Libraries"

---

## [1.3.35] - 2026-01-21
### Reaffirm:
- pypdf is the standard library. It is a fallback. It is not performant. It is stable. It is lightweight. Pypdf is a dependency. It is not an optional dependency. It's purpose is to be a good fallback.
- pypdfium2 is faster than pypdf, while having a license that is as permissive as pypdf's, while not being as large a package as PyMuPDF (~30 gb vs ~15 gb). 
- Spreadsheet exports are useful. They are managed in `src/pdflinkcheck/spreadsheet.py`.
- By reading spreadsheet exports and comparsing them between each engine, it easy to see (namely in the 'External' tab) that the data gleaned from any given PDF (if it has external links) is different between the analysis performed in `src/pdflinkcheck/analysis_pypdfium.py ` and analysis performed in `analysis_pymupdf.py ` . 
- It is assumed at this point that `PyMuPDF` offers higher quality, and it has the keys and schema of records.
- While external links are now found for `pdfium` is is believed that there is redundacy.
- A schema has been recorded in `src/pdflinkcheck/data/*.json`; as a goal to move toward. This is mid-refactor, and the schema that is used is represented in `src/pdflinkcheck/report.py` and in `src/pdflinkcheck/stdlib_server.py`.
- As the permanent schema is considered, we should be aware the pdfium is clearly the best option in terms of licensing and size, and that it is a key feature of this library the be able to be rolled easily without the PyMuPDF dependency. Ergo, to be overly attached to the PyMuPDF-ideal schema is overcoupling the project to a fundamentally separable aspect. We are glad to be able to leverage PyMuPDF as testing continues and to be able to offer it to user who choose to use PyMuPDF.
- A breakthrough was made in v1.3.34 concerning capturing external links. There was in encoding issue but it was sorted out by reading the docs that Google publishes for PDFium. The anchor text is missing and some links appear redundant. Comparison between the various engines is important for continuous improvement.

### Changed:
- Function name change: call_stable() -> demo() in analysis_pymupdf.py and analysis_pdfium.py; 
- Implement a demo function in analysis_pdfim.py.
- For the demo function, stop using the wrong-direction import from report.py and instead from pdflinkcheck.io import get_first_pdf_in_cwd().
- `help-tree` CLI  command changed to `helptree`, and is imported from the typer-helptree library rather than carried internally.

### Removed:
- pdflinkcheck.io.export_report_data()

### Internal:
- Testing should be implemented, with packaged PDF files that are relatively lightweight (<5 mb) but have various links that can be used to test the performance of the three current PDF engines.
- Use PDF testing in CI/CD for automated but catching and quality assurance.

---


## [1.3.34] - 2026-01-21
### Fixed:
- Missing external link types added to pdfium engine

---

## [1.3.31] - 2026-01-16
### Fixed:
- Ensure dist/zipapp/ dir at the very beginning of build_pyz.py
- Ensure custom_env is being ued in the case of Termux, so that uv build point ot a temp dir within $HOME.

### Changed:
- PyHabitat dependency increased to a minumum of 1.1.18, due to out-migration of the show_system_explorer() function. 

---

## [1.3.30] - 2026-01-16
### Fixed:
- Implement dist/zipapp/ folder for build_pyz, and referenc this in build.yml for file handling.

### Fxed:
- Improve build_pyz.py to be compatible with F-Droid Termux, by sending `uv build` to use a tmp dir within $HOME during the wheel build phase.

### Internal
- All PYZ builds are not designated to use pdfium but not pymupdf as an extra, to stay small.

---

## [1.3.29] - 2026-01-16
### Fixed:
- Correct path check in build.yml diagnostic to use dist/onedir/ and dist/onefile/

### Internal:
- Start to implement prereleases, using:
    ```bash
    git tag v1.3.29-test
    git push origin v1.3.29-test
    gh release create v1.3.29-test --title "PDF Link Check v1.3.29-test" --prerelease
    ```

---

## [1.3.28] - 2026-01-16
### Fixed:
- Migrate to a dist/onedir/ and dist/onepath/ strategy for clear separation. Implement this in build_executable.py, build.yml, and msix.yml.

### Internal:
- For build_executable.py to work on Termux, PyInstaller must be installed as a dependency to the local venv, not with termux or system pip. This is facilitated by the dev dependency section in ./pyproject.toml.
- Delete detritis comments from pyproject.toml.

---

## [1.3.27] - 2026-01-16
### Fixed:
- Correct expected "-onedir" file tail in msix.yml; Now we just validate expected structure of the onedir folder rather than looking for an exe to ignore based on filename.

---

## [1.3.25] - 2026-01-16
### Fixed:
- build.yml is passing. Correct commented line in msix.yml which caused error

###
- Uncomment the 'overwrite_files' key in the 'Attach artifacts to GitHub Release' section of build.yml; this might or might not, work, with the alternative being the 'overwrite' key (which VS Code flags as erroneous).

---

## [1.3.23] - 2026-01-16
### Fixed:
- Upload conflict for the two Windows build runs (onedir and onefile)

### Changed:
- Adjust build.yml to not yell in case of overwrite. Only build source tar.gz and .whl on ubuntu. 

---

## [1.3.22] - 2026-01-16
### Added:
- Enable onefile vs onedir mode as argparse call to build_executible.py; default to onedir if no arg is provided.
- In build.yml, add a section to call the onefile mode for just Windows.

---

## [1.3.20] - 2026-01-16
### Fixed:
- Improve unix section of build.yml to handle both onedir and onefile

---

## [1.3.19] - 2026-01-15  
### Fixed:
- Anchor text now coming through with pdfium.
- Ensure hyperlinks are functional in Excel export by using the source_path key.

### Added:
- Separate TOC and Internal GoTo Links into two separate pages.

---

## [1.3.18] - 2026-01-15  
### Fixed:
- For the PyMuPDF library, the document was being preemtively closed. Now a with block is being implemented in analysis_pymupdf.analyze_pdf() rather than erroneously within analysis_pymupdf.extract_links_pymupdf() .

---

## [1.3.17] - 2026-01-15  
### Fixed:
- PyMuPDF needds to return empty structural_toc list if no links are found
- No links: no XLSX.
- MSIX now build as --onedir successfully, and all three engines are available.

---

## [1.3.7] - 2026-01-15  
### Fixed:
- Pdfium was being used in report.py regardless of selection from the server, the cli, and the gui.
- pypdfium2/pdfium.dll known to be blocked by threatlocker. For the MSIX installation, it appears in C:/Users/user/appdata/local/temp/_mei173922/pypdfium2_raw/pdfium.dll. The mei number will change with each launch.
- Clear cache functons had no body - now it clears pdfium_is_available() and pymupdf_is_available(). 
- Ensure metadata is returned in stdlib_server._process_pdf()

### Changed:
- is_in_git_repo() is no longer cached.
- --onedir used with all build_executable.py builds instead of --onefile, to help mitigate issues with threatlocker and a dynamic _MEI* path. 
- build.yml and msix.yml now enable proper performance i case of --onedir or --onepath.


## Added:
- Sign all DLL, PYD, and EXE files packaged into MSIX, for extra care and ThreatLocker mitigation.

---

## [1.3.6] - 2026-01-14  
### Fixed
- Ensure pdf library used is included in xlsx export name

### Internal:
- To do: Combine export file naming logic for all file types, to avoid maintance issues.

---

## [1.3.5] - 2026-01-14  
### Fixed:
- File naming of spreadsheet exports made consistent with JSON and TXT exports.

---

## [1.3.4] - 2026-01-14  
### Changed:
- Update README and asset screenshots to version 1.3.3

---

## [1.3.3] - 2026-01-14  
### Changed:
- GUI: Take away Open TXT and Open JSON buttons and add Show System Explorer button
- Width increased to 800 pixels to allow for XLSX button addition width impact

### Breaking:
- Extra indetifier. Change pymupdf extra dep group name for consistency. Intances of --extra mupdf -> --extra pymupdf, to reduce confusion. Example: `pip install -e ".[pdfium,mupdf]"` -> `pip install -e ".[pdfium,pymupdf]"`

### Fixed:
- GUI: _show_system_explorer() function triggered by button is stable, prints and passes.

### Added:
- Implement _get_export_path() to dynamically resolve the report directory by leveraging the PDFLINKCHECK_HOME constant from io.py.
- Add _show_system_explorer() to provide cross-platform access to the export folder using native shell commands and io.py path logic.

---


## [1.3.1] - 2026-01-14  
### Added:
- Spreadsheet report export

---

## [1.2.44] - 2026-01-13                                
### Changed:
- Printing and error handling in stdlib_server_alt.py
- Delete unused stdlib_server.py
- File name change: stdlib_server_alt.py -> stdlib_server.py
- Update OPEN API docs in server code.
- Modularize the do_GET() function in the server code.
- Use log buffer pattern for toc structure in report.py.

---

## [1.2.43] - 2026-01-13
### Fixed:
- For store badge, correct assets path to: https://raw.githubusercontent.com/City-of-Memphis-Wastewater/pdflinkcheck/main/assets/

---

## [1.2.42] - 2026-01-13
### Added:
- Microsoft Sotre badge added to assets and shown on README (which will show on PyPI as well).

### Fixed:
- Incorrect/outdated library usage shown in README

---

## [1.2.41] - 2026-01-13
### Changed:
- Minor improvements to report styling.

---

## [1.2.40] - 2026-01-13
### Changed:
- Ensure docker build only occurs with a release, not a tag push, in docker.yml

### Fixed:
- Use "validation": EMPTY_VALIDATION_SUMMARY.copy() in the one place it is missing, if there are no links at all.
- Implement report._print_report_algorithm() before all early returns in report.run_report_extraction_and_assessment_and_recording()
- Try different version of gui._open_export_file(); assume pyhabitat.edit_textfile() won't run on Windows.

---

## [1.2.39] - 2026-01-13
### Changed:
- Suppress AllowExternalContent in AppxManifest file, to see if it allows sideloading

---

## [1.2.38] - 2026-01-13
### Fixed:
- In the msix.yml runner, remove AppxManifest_unversioned.xml before packing; the theory is that if it is present, it will be merged with the versioned one, and that this will result in sideloading being made unavailable

---

## [1.2.37] - 2026-01-13
### Fixed:
- Remove unrestrictedAppContainer capability from AppxManifest.xml, to allow for sideloading of the MSIX file.

---

## [1.2.36] - 2026-01-13
### Fixed:
- io.get_friendly_path() no longer forces a tilde into Windows paths.

---

## [1.2.32] - 2026-01-12
### Fixed:
- Stability for the server command by troubleshooting the usage of stdlib_serve_alt.py
    - Current issue, no print feedback while using the web app
- MSIX adjsutment in AppxManifest XML file: Application: `uap4:SupportedUsers="allUsers"` 

### Added:
- CLI now has a short concise report, whereas the GUI and the weber server generate a long report.

### Internal:
- Add PDF library used to JSON structure; right now the web server only shows "auto", which is useless.


---

## [1.2.31] - 2026-01-12
### Testing:
- Ensure _open_export_file() buttons work fine on Windows. Analyze failure modes.

### Changed:
- Update pyhabitat version to 1.1.6, which has better windows path resolution in case of VFS in MSIX distribution.
- To ensure the MSIX can launch Notepad, etc and interact with files, update AppxManifest XML file to enable:
    - uap10
    - Capabilities, Name="unrestrictedAppContainer"
    - Properties, uap10:AllowExternalContent 

---

## [1.2.30] - 2026-01-12
### Changed:
- Supress `--onedir` usage in build_executible.py for ph.on_termux(); these termux builds are currently failing on both systems. We likely need to pin a version of pyinstaller. Check for handling.
- Ensure MSIX includes both PyMuPDF and PDFium, in msix.yml: `pip install -e ".[pdfium]"` -> `pip install -e ".[pdfium,mupdf]"`

---

## [1.2.29] - 2026-01-12
### Changed:
- Remove outdated print_bool arg from report.get_structural_toc()

### Added:
- Add concise_print arg to report.run_report_extraction_and_assessment_and_recording() but do not expose it; this is just for documentation and keeping the option to toggle verbosity or just overview print, rather than commenting. Beware maintenance. concise_print=False is a safe default.

---

## [1.2.28] - 2026-01-07
### Added:
- io.get_unique_unix_time(): ensure unique filenames to avoid overwrites of redundant analysis with same PDF engine with same target PDF file - do this quick and dirty by adding the unix time value to the filename.

---

## [1.2.27] - 2026-01-06
### Changed:
- Struggle through a refactor of report.py. Keep legacy function in file for now.
- Revert to stable function while carrying fetal refactor code in the report.py file.

### Fixed:
- Correct import to gui.py in start_gui easter egg import in __init__.py

---

## [1.2.26] - 2026-01-06
### Added:
- Use splash scren with loading bar for better UX while app launchs. Add splash.py.

### Changed:
- guit_tight.py -> gui.py
- analysis: For each engine, the link and toc and metadata information now only requires the file to be opened once, rather than an opening processes for each distinct purpose. 
- total_pages: matadata has been resturctured so that page number is assessed in each engine, during the calls from report.py, and stored for use, rather than being assessed on the tail end in validate.py.

### Fixed:
- gui.pi: ensure that the loading screen and the gui are popiing up in the middle of the main window, even in multiscreen setups and cross-platform.
- Updated README and __init__ to expose fewweer functions, now that the link and toc extractions have been combined into single analysis functions for each engine. 

---

## [1.2.24] - 2026-01-06
### Fixed:
- data inclusion: add MANIFEST.in file to ensure data is included with setuptools backend.

---

## [1.2.23] - 2026-01-06
### Added:
- MSIX failure to build with CLI exposure: update appxmanifest extension section.

---

## [1.2.21] - 2026-01-05
### Added:
- Insert env vars at the top of cli.py to ensure PYZ distributed CLI's can have rich colors. Using the in-file env vars is termux compatobke for shiv 1.0.8.

### Fixed:
- gui.py: unidecode fails on mac os. Revert to former glyph sanitization function

---

## [1.2.20] - 2026-01-03
### Added:
- More robust stdlib server version, _alt

---

## [1.2.18] - 2026-01-03
### Changed:
- Move from hatchling back to uv-build. Fdroid Termux supports neither pyinstaller nor uv build.

---

## [1.2.13] - 2026-01-02
### Changed:
- Move from uv-build to hatchling

---

## [1.2.12] - 2026-01-02
### Fixed:
- Liberal applicatiom of 'from __future__ import annotations' for.3.9.compatibility.

---

## [1.2.10] - 2026-01-02
### Fixed:
- Guard against failed if pdfium is not included.

---

## [1.2.4] - 2026-01-02
### Added:
- PDFium engine support via src/pdflinkcheck/analysis_pdfium.py; this means that we no longer need and ffi bridge nor a pdflinkcheck-rust package. The hold up there was packaging the libpdfium.so/.dll/.dylib into the pdflinkcheck-rust .whl along with the pdflinkcheck-rust.so/.dll/.dylib. The pypdfium2  requires less maintenance on my part, though less rust as a portfolio piece. We learned though.

### Changed: 
- Available radio button for library selection will now only include the ones that are available to the current environment or the build.

### Removed:
-  FFI stuff

---

## [1.2.2] - 2025-12-31
### Fixed:
- Remove .so from /data/. It was fun, but not Pythonic. We will build a separate pdflinkcheck-rust PyPI library, for optional dep inclusion, packaged with PyO3
- Suprress rust stuff for now.

### Changed:
- Rust to Python nirmlaizatiojnis jow internal to ffi.oy and does not jeed to be called in report.py, such that exois3d runction in __init__ is also pre-normalized.

---

## [1.2.1] - 2025-12-29
### Changed
- Standardized internal module naming convention to analysis_{engine} across Python and Rust source files.
- Renamed Rust analysis core to analysis_pdfium.rs to clarify the underlying technology and support future engine expansion.

### Breaking:
- In the CLI, changed the PDF library selection flag on the analyze command from `--pdf-library/-p` to `--engine/-e`. There are enough p's happening.
- In the CLI, changed the export filetime selection flag on the analyze command from `--export-format/-e` to `--format/-f`. This is to avoid the conflict with `-e/--engine`.

---

## [1.1.99] - 2025-12-28

### Fixed:
- Reduced Tkinter padding. Included minimum size. Do this in parallel new file, gui_tight.py.
- Change import reference from gui_alt.py to gui_tight.py in cli.py.

### Added:
- security.py, for checking external links. Look at TLD, homoglyphs, and tracking parameters. Currently the risk structures in the JSON export are separate but they should become integrated with the existing sections of external links.

### Internal:
- There is no getting around the Windows program picker is os.startfile() is used. Ergo, we no longer expect or enable fallback to Notepad, etc.
- Researched mhtml file link artifacts. They do nit need to be checked as local relative file links.

---

## [1.1.98] - 2025-12-27
### Changed
- Update screenshots for README.

---

## [1.1.97] - 2025-12-27
### Changed
- Change geometry in gui_alt.py to self.geometry("800x600"), like gui.py.

---

## [1.1.96] - 2025-12-27
### Fixed
- Upgrade to pyhabitat v1.1.3, which now handles file explicitly on Windows to use notepad.exe if a program is unassociated, like for JSON.

---

## [1.1.95] - 2025-12-26
### Changed:
- Function naming; report.run_report_and_validtion() AKA run_report_and_validation(), now reverted back to run_report(), so that the naming scheme fits complement the over arching report.run_report_and_call_exports(). See CHANGELOG 1.1.81.
- Remove the max links feature entirely, from report.py, from the CLI, and from the GUI.
- Adjust the use of Open Report Button - now have two buttons - Open Report JSON and Open Report TXT. Have these buttons greyed out if a report has not been run. They will open the currently known files, which can be a object attribute of the gui class instance. Now that there is a single Run Analysis button with the validation folded in to the singular process, there is no reason to not allow direct file opening of the actual exports, as opposed to generating a tmp file when hitting the **Open Report** button.
- Update report results link count metadata and dictionary schema to be more granular. Do not mix other links with external URI links.
- Require pyhabitat v1.1.1, which implements the new pyhabitat.is_msix() function, which is used to determine Path.home() as the default browser directory when installed as MSIX from the Microsoft Store.

### Fixed:
- Redundant prints to window in report.py, at print_bool instances. Choose - print until hypothetical failure inside of log or print once the buffer is finished, which is cleanest but expects safe. We chose to print the completed buffer after it is converted to a string completion.
- GUI: Improve _set_icon() to try the PNG logo first and then to try the ICO. The ICO is expected to fail on Linux. If both the PNG and the ICO succeed, the ICO will overrride the PNG -this is slightly innefficient, but worth the robustness.
- analyze_pymupdf.py: There is a plus-one page issue, in the pymupdf-based method, not the pypdf-based method.
- Browsing location for MSIX: Ensure msix installation browses in Path.home(), while all else defause to Path.cwd(). If there is a filepath in the text field, it's parent diretory will be used

### Internal:
- pyhabitat.edit_textfile() 1.0.53 blocks the console. Updated made in pyhabitat 1.1.1 so that this is no longer an issue.

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
- GUI Version: Version info added to frame heading of the Tkinter gui, by leveraging `version_info.get_version()`
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

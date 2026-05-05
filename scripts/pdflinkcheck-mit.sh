git clone git@github.com:City-of-Memphis-Wastewater/pdflinkcheck.git ~/pdflinkcheck-mit
cd ~/pdflinkcheck-mit
# replace project name in pyproject.toml, and al other string instances of pdflinkcheck -> pdflinkcheck-mit
rm LICENSE
mv LICENSE-MIT LICENSE
rm LICENSE-AGPL3

# the hardest part, most error prone:

#[project.optional-dependencies]
#pymupdf = ["pymupdf>=1.24.0,<2.0.0"] # fails on termux # If you choose to include PyMuPDF, you must comply with the AGPL3
#pdfium = ["pypdfium2>=5.2.0,<6.0.0"]
#full = "pdlinkcheck[pymupdf,pdfium]"
# i need to destroy the line in this section that include pymupdf, and i need to remove the full line
# it can be easy: remove every line where 'pymupdf' is found


rm ~/pdflinkcheck-mit

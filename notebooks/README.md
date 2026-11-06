# Thesis notebooks: how to run

This folder holds the notebooks that present the Kambale thesis results.

| File | What it is |
|---|---|
| `Kambale_Thesis_Results.ipynb` | The results notebook for supervisors. Five objectives, each with the research question, the methods and settings, live results, key figures and a summary. All numbers are read from the databases when the notebook runs. |
| `Kambale_Technical_Appendix.ipynb` | The companion technical appendix. It documents how the results were checked (software environment, settings and input checksums, automated checks) and how to rerun the full analysis. |
| `MATH_NOTES.md` | The full mathematical notes, generated from the same strings as the results notebook. Each formula is tied to the module that implements it. |
| `build_notebook.py` | The source of the two notebooks and `MATH_NOTES.md`. All markdown and code cells are defined here so that they can be reviewed in git. |
| `_check_queries.py` | Runs every SQL query and code cell of both notebooks against the databases (read-only), without the helper package. Use it after changing any query. |
| `prep/` | Local only and gitignored. The author's private preparation notebook (`prep/Presentation_Prep.ipynb`), built by `prep/build_prep.py` from an earlier version of the builder. It holds the full detail and the likely questions. It is not for distribution. |
| `.gitignore` | Ignores `output/` and `prep/`. |

Do not edit the generated `.ipynb` files or `MATH_NOTES.md` by hand. Change `build_notebook.py` and regenerate.

## 1. Install

```bash
pip install -e ".[notebook]"
```

The `notebook` extra supplies Jupyter, nbformat, nbclient, papermill and ipykernel.

## 2. Regenerate the notebooks and the mathematical notes

```bash
python notebooks/build_notebook.py
```

This overwrites `Kambale_Thesis_Results.ipynb`, `Kambale_Technical_Appendix.ipynb` and `MATH_NOTES.md`. The notebooks are
written without outputs.

To test every query and code cell of both notebooks without running them:

```bash
python notebooks/_check_queries.py
```

## 3. Run the results notebook

```bash
mkdir -p notebooks/output
python -m papermill notebooks/Kambale_Thesis_Results.ipynb notebooks/output/Kambale_Thesis_Results.ipynb
python -m nbconvert --to html notebooks/output/Kambale_Thesis_Results.ipynb
```

The first command executes the notebook and writes the executed copy to `notebooks/output/`. It takes under a minute.
The second writes an HTML page with the code visible. To show a supervisor a page without code, add `--no-input` to the
`nbconvert` command.

## 4. Run the technical appendix

```bash
python -m papermill notebooks/Kambale_Technical_Appendix.ipynb notebooks/output/Kambale_Technical_Appendix.ipynb
python -m nbconvert --to html notebooks/output/Kambale_Technical_Appendix.ipynb
```

By default the appendix runs the automated checks (`RUN_CHECKS = True`) on a copy of the repository and does not rerun
the analysis. The checks take a few minutes.

## 5. Rerun the full analysis

```bash
python -m papermill notebooks/Kambale_Technical_Appendix.ipynb notebooks/output/Kambale_Technical_Appendix_rerun.ipynb -p RUN_RERUN True
```

This reruns every stage of Objectives 1 to 5 on a copy of the repository and compares the regenerated tables and figures
with the stored ones. It takes **about 15 minutes**. It works on a copy and never changes the stored databases. The
appendix reports the verdict and its scope in a highlighted box.

## 6. Data privacy

- The databases hold row-level drill-hole data and are not in the repository (see the root `.gitignore`).
- **The committed notebooks have no outputs.** They contain code and text only.
- **`notebooks/output/` holds executed copies, and those contain query results** (counts, metrics, scenario tables and
  figure paths). The folder is listed in `notebooks/.gitignore`, so it is not committed. Do not copy executed notebooks or
  HTML pages out of the project without checking them first.
- `notebooks/prep/` holds the author's private preparation notes. It is gitignored and must not be shared.
- The notebooks read specification and report files at run time. They do not copy them into the notebook source.

## 7. Conventions

- Numbers in the notebooks come from queries or from files read when they run. They are not typed in.
- Every formula is in `build_notebook.py` next to the module and function that implements it. The same formulas appear in
  `MATH_NOTES.md`, with the implementation references. The results notebook shows the formulas without those references.
- Relative links to the run reports (`../reports/...`) work when the notebooks are opened from the `notebooks/` folder.

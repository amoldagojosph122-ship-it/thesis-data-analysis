# Results notebook: how to run

This folder holds the supervisor-facing results notebook for the Kambale thesis.

| File | What it is |
|---|---|
| `build_notebook.py` | The source. All markdown and code cells, and the mathematical notes, are defined here so that they can be reviewed in git. |
| `Kambale_Thesis_Results.ipynb` | The generated notebook. It is committed **without outputs**. |
| `MATH_NOTES.md` | The mathematical notes as a standalone document, generated from the same strings as the notebook. |
| `_check_queries.py` | Runs every SQL query and code cell of the notebook against the databases (read-only), without the helper package. Use it after changing any query. |
| `.gitignore` | Ignores `output/`. |

Do not edit `Kambale_Thesis_Results.ipynb` or `MATH_NOTES.md` by hand. Change `build_notebook.py` and regenerate.

## 1. Install

```bash
pip install -e ".[notebook]"
```

The `notebook` extra supplies Jupyter, nbformat, nbclient, papermill and ipykernel.

## 2. Regenerate the notebook and the mathematical notes

```bash
python notebooks/build_notebook.py
```

This overwrites `Kambale_Thesis_Results.ipynb` and `MATH_NOTES.md`. It needs nbformat only for the notebook; the
mathematical notes are written from the same strings.

To test every query without running the notebook:

```bash
python notebooks/_check_queries.py
```

## 3. Mode A: stored results (`MODE = "present"`)

Mode A shows the results stored in the databases. It queries the databases read-only, reads the configurations and
run reports, and checks the gates on a copy of the repository. It takes a few minutes.

```bash
mkdir -p notebooks/output
papermill notebooks/Kambale_Thesis_Results.ipynb notebooks/output/Results_present.ipynb -p MODE present
jupyter nbconvert --to html notebooks/output/Results_present.ipynb --no-input
```

The first command executes the notebook and writes the executed copy to `notebooks/output/`. The second writes an HTML
page **without code cells**, which is the version to show a supervisor.

For a version with the code visible, omit `--no-input`:

```bash
jupyter nbconvert --to html notebooks/output/Results_present.ipynb
```

## 4. Mode B: reproduction (`MODE = "reproduce"`)

Mode B re-runs the Objective 1 to 5 pipelines on a copy of the repository and compares the regenerated tables and figures
with the registered ones. It takes **about 15 minutes**. It works on a copy and never changes the real databases.

```bash
papermill notebooks/Kambale_Thesis_Results.ipynb notebooks/output/Results_reproduce.ipynb -p MODE reproduce
```

The notebook reports the reproduction verdict and its scope in a highlighted box. Mode B does not change the committed
notebook or the results in `database/`.

To skip the gate run inside Mode A or Mode B (for quick test runs), add `-p RUN_GATES False`.

## 5. Data privacy

- The databases hold row-level drill-hole data and are not in the repository (see the root `.gitignore`).
- **The committed notebook has no outputs.** It contains code and text only.
- **`notebooks/output/` holds executed copies, and those contain query results** (counts, metrics, scenario tables and
  figure paths). The folder is listed in `notebooks/.gitignore`, so it is not committed. Do not copy executed notebooks or
  HTML pages out of the project without checking them first.
- The notebook reads specification and report files at run time. It does not copy them into the notebook source, so the
  committed notebook does not contain the text of the specifications.

## 6. Conventions

- Numbers in the notebook come from queries or from files read when it runs. They are not typed in.
- Every formula is in `build_notebook.py` next to the module and function that implements it. The same formulas appear in
  `MATH_NOTES.md`.
- Relative links to the run reports (`../reports/...`) work when the notebook is opened from the `notebooks/` folder.

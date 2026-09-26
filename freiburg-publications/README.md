# Freiburg Galaxy Team publications

Finds new publications by members of the Freiburg Galaxy Team (current and
former) so they can be added to the Galaxy Hub bibliography
`content/freiburg/citations/freiburg.bib`.

The bibliography is the *Publications* page shown on
https://galaxyproject.org/freiburg/citations/ and (since the
`freiburg-citations-title` hub PR) also on https://galaxyproject.org/eu/citations/.

## How it works

1. Reads everyone listed under `freiburg` in the Galaxy Hub
   `content/people/people.yaml` (fetch from GitHub raw or local file).
2. Fetches each person's works from the ORCID public API (`/works`).
3. Estimates the person's **join year** as the earliest year of a *strictly*
   Galaxy-related work (title/journal contains `galaxy`/`usegalaxy`/`toolshed`/
   `bioconda`/`biocontainer`/`planemo`/`orione`). People with no such work are
   skipped (membership cannot be anchored).
4. Drops works already present in `freiburg.bib` (DOI match, then normalized
   title). A `[version…]`/preprint marker in a title does not hide an existing
   entry.
5. Prefers the journal version over a preprint when the same title appears
   twice, and drops preprints (bioRxiv/medRxiv/Research Square/preprints.
   org/OSF/cordi/protocols) whose *journal* twin already exists — in
   `freiburg.bib` or among the new candidates.
6. Writes clean BibTeX (via DOI content negotiation) to `data/candidates.bib`
   and a human-readable report to `data/freiburg-candidates.md`.

## Run

```bash
# full run, fetching people.yaml + freiburg.bib from galaxy-hub main
python3 freiburg_publications.py

# only one person (faster while iterating)
python3 freiburg_publications.py --only paulzierep

# against local galaxy-hub checkout (no network fetch for those two files)
python3 freiburg_publications.py \
  --yaml /path/to/galaxy-hub/content/people/people.yaml \
  --bib  /path/to/galaxy-hub/content/freiburg/citations/freiburg.bib

# write outputs to the current directory instead of ./data
python3 freiburg_publications.py --out .
```

Stdlib only (no pip installs). Needs network for ORCID + DOI resolvers.

## Output

| file | contents |
|------|----------|
| `data/candidates.bib` | BibTeX entries ready to merge into `freiburg.bib` (journal versions preferred, preprints of already-known journal papers removed) |
| `data/freiburg-candidates.md` | per-person report: join year, each candidate with year / journal / DOI / `galaxy: yes|no` |

Entries that cannot be resolved to BibTeX (no DOI, or the resolver fails) are
reported in the summary as "without BibTeX (manual)".

## Update the Galaxy Hub bibliography

1. Run the script and review `data/freiburg-candidates.md` (drop anything not
   actually team-relevant).
2. Create/refresh a branch in `galaxyproject/galaxy-hub` from `main`:

   ```bash
   cd /path/to/galaxy-hub
   git checkout main && git pull
   git checkout -b add-freiburg-team-citations
   ```

3. Append the candidates to the bibliography (reformat the compact
   DOI-resolver entries into the file's `@article{key,\n  field = {value},`
   style):

   ```bash
   python3 ../galaxy-kpis/freiburg-publications/freiburg_publications.py --out /tmp/fp
   # …reformat+append (or do it during merge in an editor)
   ```

   Alternatively assemble the merged file programmatically (this is what the
   `add-freiburg-team-citations` hub PR does): take `main`'s `freiburg.bib`,
   format each `candidates.bib` entry into the multi-line style and append.

4. Verify no duplicate keys / DOIs / titles were introduced, commit, push to
   the fork, and open a PR against
   `galaxyproject/galaxy-hub` `main`.

   ```bash
   git add content/freiburg/citations/freiburg.bib
   git commit -m "Add recent Freiburg Galaxy team publications to citations"
   git push -u my-fork add-freiburg-team-citations
   # PR compare:
   # https://github.com/galaxyproject/galaxy-hub/compare/main...paulzierep:galaxy-hub:add-freiburg-team-citations
   ```

## Conventions / gotchas

- With no `gh`/token, PRs must be opened from the compare URL (no API
  creation).
- Pre-existing duplicate keys in `freiburg.bib` (e.g. `Wolff2020` x3) are that
  file's own `Author_year` key collisions — distinct papers, leave them alone.
- `people.yaml` `freiburg:` block: entries without ORCID are skipped; `bio:`/
  heredocs are ignored by the minimal YAML parser.
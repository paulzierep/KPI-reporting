#!/usr/bin/env python3
"""Tool update stats for bioconda: how many packages got new versions per year.

Each date snapshot in bioconda-stats (branch `data`, tags <YYYY-MM-DD>)
contains `package-downloads/anaconda.org/bioconda/versions/<pkg>.tsv` with one
row per version and its *cumulative* download total. A version key that is
present at the end of year Y but was absent at the end of Y-1 counts as a new
version released and downloaded in year Y.

Version sets are compared across the four boundary tags 2022-12-31 .. 2025-12-31;
the per-tag source tarballs (~0.6 MB each) are downloaded once into
`/tmp/opencode` and reused.

Usage
-----
    python3 bioconda_tool_updates.py

Writes to `data/`:
  bioconda_tool_updates.tsv          year, packages_with_new_versions, new_versions
  bioconda_new_versions.tsv          year, package, new_version (one row per bump)
"""

import tarfile
import urllib.request
from collections import defaultdict
from pathlib import Path

YEARS = (2023, 2024, 2025)
BOUNDARIES = (2022, 2023, 2024, 2025)

TARBALL_URL = (
    "https://codeload.github.com/bioconda/bioconda-stats/tar.gz/refs/tags/{tag}"
)
CACHE_DIR = Path("/tmp/opencode")
VERSIONS_PREFIX = "package-downloads/anaconda.org/bioconda/versions/"

WATCHLIST = {
    "samtools", "bcftools", "bedtools", "fastp", "fastqc", "multiqc",
    "trim-galore", "cutadapt", "bwa", "star", "bowtie2", "kallisto",
    "salmon", "sra-tools", "snakemake", "picard",
}


def fetch_tarball(tag):
    cache = CACHE_DIR / f"bioconda-stats-{tag}.tar.gz"
    if not cache.exists():
        print(f"  downloading {tag} snapshot ...")
        urllib.request.urlretrieve(TARBALL_URL.format(tag=tag), cache)
    return cache


def versions_at(tag):
    """Return {package: {version}} with downloads > 0 at this snapshot."""
    versions = defaultdict(set)
    tarball = fetch_tarball(tag)
    with tarfile.open(tarball, "r:gz") as tf:
        for mem in tf.getmembers():
            if not mem.isfile() or VERSIONS_PREFIX not in mem.name:
                continue
            pkg = mem.name.rsplit(VERSIONS_PREFIX, 1)[-1]
            if not pkg.endswith(".tsv"):
                continue
            pkg = pkg[:-4]
            f = tf.extractfile(mem)
            if f is None:
                continue
            for line in f.read().decode("utf-8", "replace").splitlines()[1:]:
                parts = line.split("\t")
                if len(parts) >= 2 and parts[1].isdigit() and int(parts[1]) > 0:
                    versions[pkg].add(parts[0])
    return versions


def main():
    out_dir = Path(__file__).resolve().parent / "data"
    out_dir.mkdir(exist_ok=True)

    snap = {b: versions_at(f"{b}-12-31") for b in BOUNDARIES}

    summary_rows = []
    new_rows = []
    for year in YEARS:
        prev, cur = snap[year - 1], snap[year]
        print(f"\ntool updates {year}:")
        per_pkg = {}
        for pkg, curr in cur.items():
            added = curr - prev.get(pkg, set())
            if added:
                per_pkg[pkg] = sorted(added)
        total_new = sum(len(v) for v in per_pkg.values())
        print(f"  packages with new version: {len(per_pkg):,}  new versions: {total_new:,}")
        summary_rows.append((year, len(per_pkg), total_new))

        for pkg, added in per_pkg.items():
            for v in added:
                new_rows.append((year, pkg, v))

        top = sorted(per_pkg.items(), key=lambda x: -len(x[1]))[:15]
        for pkg, added in top:
            print(f"    {pkg:<32}{len(added):>4}  {', '.join(added[:5])}")
        watch = {p: per_pkg[p] for p in WATCHLIST if p in per_pkg}
        if watch:
            print("  watchlist new versions:")
            for p in sorted(watch):
                print(f"    {p:<32}{', '.join(watch[p])}")

    with open(out_dir / "bioconda_tool_updates.tsv", "w", encoding="utf-8") as fh:
        fh.write("year\tpackages_with_new_versions\tnew_versions\n")
        for year, npk, nv in summary_rows:
            fh.write(f"{year}\t{npk}\t{nv}\n")

    with open(out_dir / "bioconda_new_versions.tsv", "w", encoding="utf-8") as fh:
        fh.write("year\tpackage\tnew_version\n")
        for year, pkg, v in new_rows:
            fh.write(f"{year}\t{pkg}\t{v}\n")

    print("\nwrote: bioconda_tool_updates.tsv, bioconda_new_versions.tsv")


if __name__ == "__main__":
    main()
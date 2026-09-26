# Dependency verification

`ci.txt` and `release.txt` are human-reviewed version inputs. `locks/` contains
complete wheel hashes for Linux x86_64 on glibc 2.35 or newer, matching the
Ubuntu 22.04 CI/release builder. Separate Python 3.11 and 3.14 files account for
interpreter-specific wheels; the minimum-Qt lock pins PyQt6/Qt 6.6.0.
Release locks include CI tools because the release gate runs the test suite.

Regenerate with `python scripts/lock_requirements.py` after deliberately editing
versions. Review all added transitive dependencies, version changes, and hashes.
The generator resolves wheel metadata and hashes the actual downloaded wheels;
no source distributions are accepted. Dependency update PRs must regenerate
locks. Unchanged inputs should reproduce identical lock contents.

Install the matching lock using:

```bash
python -m pip install --require-hashes --only-binary=:all: -r requirements/locks/ci-py3.11.txt
python -m pip install --no-deps --no-build-isolation -e .
```

Use the release lock for artifact builds. Other development platforms may use
the version constraints; these Linux locks are not a cross-platform guarantee.
Python itself, pip, OS packages, and GitHub runner images remain separately
trusted build inputs. Hashes prevent silent wheel substitution; they do not
prove that the reviewed package version is free of vulnerabilities.

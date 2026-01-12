# Strain Authentication and Identification Methods - saim

[![release: 0.9.28](https://img.shields.io/badge/rel-0.9.28-blue.svg?style=flat-square)](https://github.com/LeibnizDSMZ/saim.git)
[![MIT LICENSE](https://img.shields.io/badge/License-MIT-brightgreen.svg?style=flat-square)](https://choosealicense.com/licenses/mit/)
[![Documentation Status](https://img.shields.io/badge/docs-GitHub-blue.svg?style=flat-square)](https://LeibnizDSMZ.github.io/saim/)

[![main](https://github.com/LeibnizDSMZ/saim/actions/workflows/main.yml/badge.svg?branch=main)](https://github.com/LeibnizDSMZ/saim/actions/workflows/main.yml)

[![DOI](https://zenodo.org/badge/932743748.svg)](https://doi.org/10.5281/zenodo.14879790)

---

**saim** (Strain Authentication and Identification Methods) is a Python toolkit for reproducible identification, authentication, and metadata handling of microbial strains. It provides utilities for validating strain metadata, harmonizing identifiers, running identification workflows, and exporting results for downstream analysis.

---

## Installation - Development

### Prerequisites

- **GNU/Linux**
- **Docker (optional)**
- **Docker Compose (optional)**
- **Dev Container CLI (optional)**

### Steps

1. Clone the repository:
   ```sh
   git clone https://github.com/LeibnizDSMZ/saim.git
   cd saim
   ```

#### Docker

2. If using Docker, start the development container manually or use VSCode:
   ```sh
   devcontainer up --workspace-folder .
   devcontainer exec --workspace-folder . bash
   ```

3. Create and activate a virtual environment (inside docker the container):
   ```sh
   make dev
   make runAct
   ```

#### Local

2. Create and activate a virtual environment:
   ```sh
   python -m venv .venv
   source .venv/bin/activate
   ```
3. Install the dependencies:
   ```sh
   pip install .
   pip install -r configs/dev/requirements.dev.txt
   pip install -r configs/dev/requirements.test.txt
   pip install -r configs/dev/requirements.docs.txt
   ```

---

## Contributors

- Artur Lissin
- Julius Witte

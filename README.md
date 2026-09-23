# Computational Study

This repository contains the computational implementation and experimental analyses for the study:

**A Lexicographic Assignment Framework for Priority-Preserving Resource Allocation**

The computational experiments evaluate priority-preserving assignment formulations under different resource availability and suitability conditions using the IEEE 33-bus and IEEE 118-bus benchmark systems.

## Repository Structure

```text
computational-study/
├── outputs/
│   ├── data/              # Generated experimental results
│   └── figures/           # Generated figures
├── src/
│   ├── data_summary/      # Data aggregation and summary scripts
│   ├── experiments/       # Computational experiment scripts
│   ├── utilities/         # Shared utility functions
│   ├── verification/      # Model verification scripts
│   └── visualization/     # Figure generation scripts
├── .gitignore
├── README.md
└── requirements.txt
```

## Computational Environment

The computational study was developed and executed using:

* Python 3.11.9
* Gurobi Optimizer 13.0.1
* Windows 11

The complete Python package dependencies are provided in `requirements.txt`.

## Installation

Clone the repository and navigate to the computational study directory.

Create a virtual environment:

```bash
python -m venv venv
```

Activate the environment on Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

Install the required Python packages:

```bash
python -m pip install -r requirements.txt
```

A valid Gurobi installation and license are required to execute the optimization models.

## Experimental Design

The computational experiments evaluate the assignment formulations under variations in three experimental factors:

* number of resources,
* resource-to-node availability probability, and
* resource-to-node suitability probability.

The experiments include one-factor, two-factor, and full-factorial analyses. Fixed pseudo-random seeds are used for scenario generation to support reproducibility.

## Outputs

Experimental results are stored in:

```text
outputs/data/
```

Figures generated from the experimental results are stored in:

```text
outputs/figures/
```

The scripts used to generate the figures reported in the study are located in:

```text
src/visualization/
```

## Reproducibility

The computational environment can be recreated using the provided `requirements.txt` file. Experimental scenarios are generated using fixed pseudo-random seeds so that the computational analyses can be reproduced consistently.

## Citation

Citation information will be added upon publication of the associated article.

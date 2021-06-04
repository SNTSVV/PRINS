# PRINS: Scalable Model Inference for Component-based System Logs

This repository contains the replication package for the paper titled "[PRINS: Scalable Model Inference for Component-based System Logs](http://arxiv.org/abs/2106.01987)" (arXiv, 2021).

## Authors
- Donghwan Shin (donghwan.shin@uni.lu)
- Domenico Bianculli (domenico.bianculli@uni.lu)
- Lionel Briand (lionel.briand@uni.lu)

## Prerequisite

- python3 (python3.7 or higher is recommended)

Please initialize python's virtual environment & install required packages:
```shell script
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Dataset Check
You can simply run the following script:
```shell script
python check_dataset_summary.py
```

It will save the summary data in `dataset/dataset_summary.csv`.

## Unit Tests
You can run the unit tests:
```shell script
cd PRINS
python -m unittest
```

All 50 tests should pass.


## RQ1: Execution Time
```shell script
(venv) PROMPT PRINS-expr % python run_model_inference.py -h
usage: run_model_inference.py [-h] [--system SYSTEM] [-n NUM_LOGS]
                              [--overwrite] [--prins_only] [--mint_sys_only]

optional arguments:
  -h, --help            show this help message and exit
  --system SYSTEM       System name (default=none)
  -n NUM_LOGS, --num_logs NUM_LOGS
                        Number of logs (default=all)
  --overwrite           overwrite existing preprocessed logs
  --prins_only          Specify this to run PRINS only
  --mint_sys_only       Specify this to run MINT-SYS only
```

## RQ2: Accuracy
```shell script
(venv) PROMPT PRINS-expr % python run_k_folds_cv.py -h
usage: run_k_folds_cv.py [-h] [-k NUM_FOLDS] [-n NUM_LOGS] system technique

positional arguments:
  system                System name (e.g., Hadoop)

optional arguments:
  -h, --help            show this help message and exit
  -k NUM_FOLDS, --num_folds NUM_FOLDS
                        Number of folds
  -n NUM_LOGS, --num_logs NUM_LOGS
                        Number of logs (default: all)
```

## Result Data Analysis

Run the script (note that the experimental results must be provided in `/expr_output`; by default, the results reported in the paper are given):
```shell script
python run_analyze_results.py
```

The scripts will automaticaly generate the following files:
- `rq1-boxplot.pdf`
- `rq2-boxplot.pdf`
- `rq3-boxplot.pdf`
- `rq4-table.csv`
- `rq5-table.csv`
- `message_distribution.csv`



## Licensing

PRINS is © 2021 University of Luxembourg and licensed under the GPLv3 license.

Please read `PRINS licensing information.txt` for details.

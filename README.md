# PRINS: Scalable Model Inference for Component-based System Logs

This repository contains the replication package for the paper titled "[PRINS: Scalable Model Inference for Component-based System Logs](https://doi.org/10.1007/s10664-021-10111-4)", EMSE (2022). Please use the following citation when you want to cite our work:
> Shin, D., Bianculli, D. & Briand, L. PRINS: scalable model inference for component-based system logs. Empir Software Eng 27, 87 (2022). https://doi.org/10.1007/s10664-021-10111-4

## Authors
- Donghwan Shin (donghwan.shin@uni.lu)
- Domenico Bianculli (domenico.bianculli@uni.lu)
- Lionel Briand (lionel.briand@uni.lu)

## Prerequisite

- Python 3 (python3.7 or higher is recommended)
- Java runtime environment 1.8 (1.8.0_301 is tested)

Please initialize python's virtual environment & install required packages:
```shell script
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Dataset Check
You can simply run the following script:
```shell script
(venv) python check_dataset_summary.py
```

It will save the summary data in `dataset/dataset_summary.csv`.

## Unit Tests
You can run the unit tests:
```shell script
cd PRINS
(venv) python -m unittest
```

All 50 tests should pass.


## Execution Time Evaluation (RQ1, RQ2, RQ4)
```shell script
(venv) PROMPT PRINS-expr % python run_model_inference.py -h
usage: run_model_inference.py [-h] [-s SYSTEM] [-n NUM_LOGS] [--prins_only]
                              [--mint_sys_only] [-d DUPLICATE_RANGE]
                              [-r REPETITIONS]

optional arguments:
  -h, --help            show this help message and exit
  -s SYSTEM, --system SYSTEM
                        System name (default=None)
  -n NUM_LOGS, --num_logs NUM_LOGS
                        Number of logs (default=all)
  --prins_only          Specify this to run PRINS only
  --mint_sys_only       Specify this to run MINT-SYS only
  -d DUPLICATE_RANGE, --duplicate_range DUPLICATE_RANGE
                        Input log duplication factor range 'from,to'
                        (default='1,1')
  -r REPETITIONS, --repetitions REPETITIONS
                        Number of repetitions (default=1)
```

## Accuracy Evaluation (RQ3, RQ5)
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
(venv) python run_analyze_results.py
```

The scripts will automatically generate the following files:
- `rq1-boxplot.pdf`
- `rq2-boxplot.pdf`
- `rq3-boxplot.pdf`
- `rq4-line.csv`
- `rq5-table.csv`
- `rq5-table-size.csv`
- `message_distribution.csv`



## Licensing

PRINS is © 2021 University of Luxembourg and licensed under the GPLv3 license.

Please read `PRINS licensing information.txt` for details.

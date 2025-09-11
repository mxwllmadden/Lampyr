@echo
conda env create -f mx_hardware.yaml -y
conda activate mx_hardware
pip install .
cmd /k
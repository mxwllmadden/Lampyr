@echo

conda activate
conda activate mx_hardware
pip uninstall lampyr -y
pip install .
cmd /k
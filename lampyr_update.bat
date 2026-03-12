@echo

conda activate
conda activate mx_hardware
pip uninstall lampyr -y
pip install "git+https://github.com/mxwllmadden/Lampyr.git@main"
cmd /k
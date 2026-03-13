@echo

call conda activate
call conda activate mx_hardware
pip uninstall lampyr -y
pip install "git+https://github.com/mxwllmadden/Lampyr.git@main"
cmd /k
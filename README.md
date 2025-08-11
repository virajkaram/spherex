Install with virtualenv or conda.

1. virtualenv : 
```
python3 -m venv myenv
source myenv/bin/activate
cd project_directory
pip install -e .
```
2. conda :
```
conda create -n myenv python=3.12
conda activate myenv
cd project_directory
pip install -e .
```

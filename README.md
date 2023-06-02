# code-tree-generator
Generate CST and AST for code files or codebases.

## Current Steps

### Pass One
- Pass through *treesitter* suntax tree and add create a tree structue based on a custom class
- Do some slight condensing for binary nodes and attribute nodes
- Take all function calls and add them to a dictionary storing file, function, node name
  - If there is a matching import, also connect the call to the import $\rightarrow$ these are the only extra edges I am adding in the first pass
- Take all imports and store them in a dict, handling the format of the import (import from or import as)
- Take all function definitions and store them in a dict

Do this for every file in the codebase

### Pass Two
- Track function definitions again to help with scoping (remove from first loop then)
- Track any variable assignment (including calls) and store it in a dict with the variable type and the node location
- Track all class definitions in a separate dictionary
  - When a class is encountered, traverese through the entire class before doing anything else to make sure you account for all attributes in the class
- Track any other constant imports for identifier nodes and connect to the import or the actual definition in the other file if possible (add to *connect import edges* or if the node doesn't have a pointer yet add to *connect assignment edges*)
- For call nodes check if the function is defined in the current file and add to *connect import edges*
  - Also check if the call is an import into the current file and add to *connect import edges* or *connect call edges* depending on if the node has a pointer or not
- Check if a call is a class attribute and find its definition to connect (*connect import edges*)
- Connect all identifiers uses to their assignments (*connect import edges*)
- Copy *definitions*, *assignments*, and *classes* dictionaries for scoping and reset after visiting all children

### Pass Three
- Here we connect edges when the nodes were not existing in other files (or we did not have a pointer to these nodes in the other files)
- Connect import edges
- Connect assignment edges
- Connect call edges

## Usage

### Download
To use the `download` script, you must pass as an argument a file that contains github repos separated by newlines. For example the file could look like:
```
numba/llvmlite
simplejson/simplejson
Hackndo/lsassy
lunixbochs/ActualVim
boramalper/himawaripy
pydicom/pydicom
bhavsec/reconspider
```
And to download all the repos call `download filename.txt`.

### Get Training Data
To use the `get_training_data` script, pass the directory that you would like to search for GitHub repos and the dimension size for the node features.

#### Output
The script will create a folder `../repos/` in the parent directory of `code-tree-generator`. Inside this folder you will locate all the cloned repos.

**Note:** the script assumes that you have a virtual environemnt named `venv`.

An example usage of the script would be: `get_training_data ../repos/ 64`.

#### Output
The script will create a folder `../adj/` and `../node_feats/` that are located in the parent folder of `code-tree-generator`. These folders contain the output adjacency matrix and node features respectively. The files within the folders are named the same as the repository they correspond to.


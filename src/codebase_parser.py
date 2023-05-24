import argparse
import os
from typing import *

from tree_sitter import Language, Node, Parser, Tree, TreeCursor

from file_parser import ASTFileParser
from graph import Graph as G
from graph import Node as N

Language.build_library(
    'build/my-languages.so',
    ['../tree-sitter-python']
)

PYTHON = Language('build/my-languages.so', 'python')

class ASTCodebaseParser(ASTFileParser):

    BUILTINS = dir(__builtins__)

    def __init__(self, dir: str) -> None:
        self._dir : str = dir
        self._relative_files = self.get_files()

        self._parser = Parser()
        self._parser.set_language(PYTHON)

        self._AST = G()

        self._init_tracking()

    @property
    def AST(self) -> dict[str, Any]:
        return self._AST

    @AST.setter
    def AST(self, value: dict[str, Any]) -> None:
        raise Exception("AST is read-only. Use parse() instead.")

    def __str__(self) -> str:
        if not self._AST:
            raise Exception("AST is empty. Use parse() first.")
        return str(self._AST)
    
    def get_files(self) -> List[str]:
        files = []
        for (dirpath, dirnames, filenames) in os.walk(self._dir):
            files.extend(
                [
                    os.path.relpath(os.path.join(os.path.join(os.getcwd(), dirpath) , x))
                    for x in filenames if x.endswith(".py")
                ]
            )
        return files
    
    def parse_dir(self) -> None:
        for file in self._relative_files:
            self._filepath = file
            tree = self._get_syntax_tree(file)
            self._root = tree.root_node
            self.parse()

        self._resolve_imports(self._AST)

    def _resolve_imports(self, parent: G) -> None:
        # connect all function calls to their definitions
        for function_name in self._function_calls:
            # check if function is defined
            short_name = function_name if len(function_name.split('.')) <= 1 else function_name.split('.')[-1]
            if short_name in self._function_definitions:
                # add edge
                for call_location, call_node_name in self._function_calls[function_name]:
                    for definition_location, definition_node_name in self._function_definitions[short_name]:
                        parent.add_edge(definition_node_name, call_node_name)
                        parent.add_edge(call_node_name, definition_node_name)
def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--dir", type=str, required=True, help="Path to directory to parse")
    args = arg_parser.parse_args()

    ast = ASTCodebaseParser(args.dir)
    ast.parse_dir()

    ast.convert_to_graphviz()
    ast.view_k_neighbors("module | ../pygamelib/pygamelib/functions.py_0", 2)

    # import ast
    # print(ast.dump(ast.parse(file), indent = 5))

if __name__ == "__main__":
    main()

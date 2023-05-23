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
    def __init__(self, dir: str) -> None:
        self._dir : str = dir
        self._relative_files = self.get_files()

        self._parser = Parser()
        self._parser.set_language(PYTHON)

        self._AST = G()

        self._counts = {}

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
            files.extend([os.path.join(os.path.join(os.getcwd(), dirpath) , x) for x in filenames])
        return files
    
    def parse_dir(self) -> None:
        for file in self._relative_files:
            tree = self._get_syntax_tree(file)
            self._root = tree.root_node
            self.parse()
    
def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--dir", type=str, required=True, help="Path to directory to parse")
    args = arg_parser.parse_args()

    ast = ASTCodebaseParser(args.dir)
    ast.parse_dir()

    ast.save_dot_format()


    # import ast
    # print(ast.dump(ast.parse(file), indent = 5))

if __name__ == "__main__":
    main()

import argparse
import json
import sys
from typing import *

from tree_sitter import Language, Node, Parser, Tree, TreeCursor

from import_tracking import track_imports

Language.build_library(
    'build/my-languages.so',
    ['../tree-sitter-python']
)

PYTHON = Language('build/my-languages.so', 'python')

class ASTParser():
    def __init__(self, tree: Tree, f: str) -> None:
        super().__init__()
        self._tree : Tree = tree
        self._cursor : TreeCursor = self._tree.walk()
        self._root : Node = self._tree.root_node
        self._f : str = f
        # self._imports : Dict[str, str] = track_imports(f)
        # print(self._imports)

        self._AST = dict()

    @property
    def AST(self) -> dict[str, Any]:
        return self._AST

    @AST.setter
    def AST(self, value: dict[str, Any]) -> None:
        raise Exception("AST is read-only. Use parse() instead.")
    
    def __str__(self) -> str:
        if not self._AST:
            raise Exception("AST is empty. Use parse() first.")
        print(type(self._AST))
        return json.dumps(self._AST, indent=4)
    
    def parse(self) -> None:
        self.parse_node(self._root, self._AST)
    
    def parse_node(self, node: Node, parent: dict[str, Any]) -> None:
        parent["type"] = node.type
        parent["start_point"] = node.start_point

        parent["end_point"] = node.end_point
        # add text if node is terminal
        if node.is_named and len(node.children) == 0:
            parent["text"] = node.text.decode("utf-8")
        if node.type == 'binary_operator':
            parent["text"] = node.children[1].text.decode("utf-8")
        
        parent["children"] = []

        for child in node.children:
            # only use named nodes
            if not child.is_named:
                continue
            
            child_dict = dict()
            self.parse_node(child, child_dict)
            parent["children"].append(child_dict)

    def save_dot_format(self, filepath: str = 'tree.gv') -> str:
        if not self._AST:
            raise Exception("AST is empty. Use parse() first.")
        return self._get_dot_format(filepath)
    
    def _get_dot_format(self, filepath: str) -> str:
        edges = []
        nodes = []
        counts = {}

        def get_edges(treedict, parent=None):
            name = treedict['type'] if not treedict.get('text') else treedict['type'] + ' | ' + treedict['text']
            
            if name not in counts:
                counts[name] = 0
                name = name + '_' + str(counts[name])
            else:
                counts[name] += 1
                name = name + '_' + str(counts[name])

            nodes.append((name, treedict.get('start_point'), treedict.get('end_point')))

            if parent is not None:
                edges.append((parent, name))
            for item in treedict["children"]:
                if isinstance(item, dict):
                    get_edges(item, parent=name)
                else:
                    edges.append((name, item))

        get_edges(self._AST)
        real_stdout = sys.stdout
        sys.stdout = open(filepath, 'w')

        # Dump edge list in Graphviz DOT format
        print('strict digraph tree {')
        for row in edges:
            print('    "{0}" -> "{1}";'.format(*row))
        for node in nodes:
            print('    "{0}" [xlabel="{1}->{2}"];'.format(*node))
        print('}')

        sys.stdout.close()
        sys.stdout = real_stdout

def main(args):
    parser = Parser()
    parser.set_language(PYTHON)

    with open (args.file, "r") as myfile:
        file = myfile.read()


    tree = parser.parse(bytes(file, "utf8"))


    ast = ASTParser(tree, file)
    ast.parse()

    ast.save_dot_format()


    # import ast
    # print(ast.dump(ast.parse(file), indent = 5))

if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--file", type=str, required=True, help="Path to file to parse")
    args = arg_parser.parse_args()
    main(args)
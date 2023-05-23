import argparse
import sys
from typing import *

from tree_sitter import Language, Node, Parser, Tree, TreeCursor

from graph import Graph as G
from graph import Node as N

Language.build_library(
    'build/my-languages.so',
    ['../tree-sitter-python']
)

PYTHON = Language('build/my-languages.so', 'python')

class ASTFileParser():
    def __init__(self, filepath: str) -> None:
        super().__init__()

        self._parser = Parser()
        self._parser.set_language(PYTHON)

        self._filepath = filepath
        self._tree : Tree = self._get_syntax_tree(self._filepath)
        self._cursor : TreeCursor = self._tree.walk()
        self._root : Node = self._tree.root_node

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
    
    def _get_syntax_tree(self, filepath: str) -> Tree:
        with open (filepath, "r") as myfile:
            file = myfile.read()
        return self._parser.parse(bytes(file, "utf8"))
    
    def parse(self) -> None:
    
        def _parse_node(node: Node, parent: G) -> None:
            

            # add text if node is terminal
            text = None
            if node.is_named and len(node.children) == 0:
                text = node.text.decode("utf-8")
            if node.type == 'binary_operator':
                text = node.children[1].text.decode("utf-8")
            
            name = node.type if not text else node.type + ' | ' + text

            if name not in self._counts:
                self._counts[name] = 0
                name = name + '_' + str(self._counts[name])
            else:
                self._counts[name] += 1
                name = name + '_' + str(self._counts[name])
            
            n_ = N(name, node.start_point, node.end_point)
            if text:
                n_.text = text
            id = parent.add_vertex(n_)

            for child in node.children:
                # only use named nodes
                if not child.is_named:
                    continue
                to_id_ = _parse_node(child, parent)
                parent.add_edge(n_.id, to_id_)
            
            return id
    
        _parse_node(self._root, self._AST)


    def save_dot_format(self, filepath: str = 'tree.gv') -> str:
        if not self._AST:
            raise Exception("AST is empty. Use parse() first.")
        return self._get_dot_format(filepath)
    
    def _get_dot_format(self, filepath: str) -> str:
        edges = []
        nodes_ : List[str] = self._AST.get_vertices()
        nodes = []

        for node in nodes_:
            n_ : N = self._AST.get_vertex(node)
            nodes.append((n_.id, n_._start, n_._end))
            
            for child in n_.get_connections():
                edges.append((n_.id, child.id))


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

def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--file", type=str, required=True, help="Path to file to parse")
    args = arg_parser.parse_args()

    ast = ASTFileParser(args.file)
    ast.parse()

    ast.save_dot_format()


    # import ast
    # print(ast.dump(ast.parse(file), indent = 5))

if __name__ == "__main__":
    main()
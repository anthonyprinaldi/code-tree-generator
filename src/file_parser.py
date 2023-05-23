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

# get all python builtins
BUILTINS = dir(__builtins__)

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

        self._init_tracking()

    def _init_tracking(self) -> None:
        # track the number of each node type
        self._counts : Dict[str, int] = {}

        # track calls to functions and their locations
        # key: function name
        # value: list of tuples of (file, node name)
        self._function_calls : Dict[str, List[Tuple[str, str]]] = {}

        # track imports and their locations
        # key: import name
        # value: list of tuples of (file, node name)
        self._imports : Dict[str, List[Tuple[str, str]]] = {}

        # track function definitions and their locations
        # key: function name
        # value: list of tuples of (file, node name)
        self._function_definitions : Dict[str, List[Tuple[str, str]]] = {}

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

            # handle function calls
            if node.type == 'call' and node.children[0].text.decode("utf-8") not in BUILTINS:
                self._handle_call(node, parent, name)

            # handle imports
            if node.type == "aliased_import" or \
                (node.type == "dotted_name" and node.parent.type.startswith("import")):
                self._handle_import(node, parent, name)

            # handle function definitions
            if node.type == 'function_definition':
                self._handle_definition(node, parent, name)
            
            for child in node.children:
                # only use named nodes
                if not child.is_named:
                    continue
                to_id_ = _parse_node(child, parent)
                parent.add_edge(n_.id, to_id_)
            
            return id
    
        _parse_node(self._root, self._AST)

        # check if this is a file or dir parser
        if type(self) == ASTFileParser:
            self._resolve_imports(self._AST)

    def _handle_call(self, node: Node, parent: G, id: str) -> None:
        # get function name
        function_name = node.children[0].text.decode("utf-8")
        # get function call location
        location = (self._filepath, id)
        # add function call to dict
        if function_name not in self._function_calls:
            self._function_calls[function_name] = [location]
        else:
            self._function_calls[function_name].append(location)

        # add edge from the call to the import statment if it exists
        function_name = function_name if len(function_name.split('.')) <= 1 else function_name.split('.')[0]
        if function_name in self._imports:
            for import_location in self._imports[function_name]:
                if import_location[0] == self._filepath:
                    parent.add_edge(id, import_location[1])
        
    def _handle_import(self, node: Node, parent: G, id: str) -> None:
        if node.type == 'aliased_import':
            import_name = [(node.children[2].text.decode("utf-8"), id)]
        elif node.type == 'dotted_name':
            # skip the first dotted name of the import from
            if node.parent.type == 'import_from_statement' and node.parent.children[1] == node:
                return
            import_name = [(node.children[0].text.decode("utf-8"), id)]
            
        # add import to dict
        for import_, id_ in import_name:
            # get import location
            location = (self._filepath, id_)
            if import_ not in self._imports:
                self._imports[import_] = [location]
            else:
                self._imports[import_].append(location)

    def _handle_definition(self, node: Node, parent: G, id: str) -> None:
        # get function name
        function_name = node.children[1].text.decode("utf-8")
        # get function definition location
        location = (self._filepath, id)
        # add function definition to dict
        if function_name not in self._function_definitions:
            self._function_definitions[function_name] = [location]
        else:
            self._function_definitions[function_name].append(location)

    def _resolve_imports(self, parent: G) -> None:
        # connect all function calls to their definitions
        for function_name in self._function_calls:
            # check if function is defined
            if function_name in self._function_definitions:
                # add edge
                for call_location, call_node_name in self._function_calls[function_name]:
                    for definition_location, definition_node_name in self._function_definitions[function_name]:
                        if call_location == definition_location:
                            parent.add_edge(call_node_name, definition_node_name)

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
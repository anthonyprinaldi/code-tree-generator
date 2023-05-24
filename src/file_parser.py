import argparse
import sys
from typing import *

from tree_sitter import Language, Node, Parser, Tree, TreeCursor
from graphviz import Digraph
import networkx as nx
import numpy as np
import pandas as pd
import pygraphviz as pgv

from graph import Graph as G
from graph import Node as N

Language.build_library(
    'build/my-languages.so',
    ['../tree-sitter-python']
)

PYTHON = Language('build/my-languages.so', 'python')


class ASTFileParser():

    BUILTINS = dir(__builtins__)

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

            # add file name to root node
            if node.type == 'module':
                name = node.type + ' | ' + self._filepath

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
            if node.type == 'call' and node.children[0].text.decode("utf-8") not in self.BUILTINS:
                self._handle_call(node, parent, name)

            # handle imports
            if node.type == "aliased_import" or \
                (node.type == "dotted_name" and node.parent.type.startswith("import")):
                self._handle_import(node, parent, name)

            # handle function definitions
            if node.type == 'function_definition' or node.type == 'class_definition':
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
                            parent.add_edge(definition_node_name, call_node_name)

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
    
    def convert_to_graphviz(self) -> pgv.AGraph:
        if not self._AST:
            raise Exception("AST is empty. Use parse() first.")
        return self._convert_to_graphviz()
    
    def _convert_to_graphviz(self) -> pgv.AGraph:
        nodes = self._AST.get_vertices()
        edges = []
        # g = Digraph('G', filename='tree.gv')
        g = pgv.AGraph(strict=True, directed=True)


        for node in nodes:
            n : N = self._AST.get_vertex(node)
            g.add_node(
                n.id,
                xlabel=f'{n._start}->{n._end}',
            )
            edges.extend([(n.id, x.id) for x in n.get_connections()])

        g.add_edges_from(edges)
        g.write('tree.gv')
        return g

    def to_csv(self) -> None:
        if not self._AST:
            raise Exception("AST is empty. Use parse() first.")
        self._to_csv()

    def _to_csv(self) -> None:
        g : pgv.AGraph = self.convert_to_graphviz()
        g : nx.DiGraph = nx.nx_agraph.from_agraph(g)

        nodes = [n for n in g.nodes()]
        feats = [feat['xlabel'] for node, feat in dict(g.nodes(data=True)).items()]
        node_feats = pd.DataFrame({'node': nodes, 'feat': feats})
        node_feats.to_csv('node_feats.csv', index = False)
        del node_feats
        del nodes
        del feats
        adj = nx.to_numpy_array(g, dtype = np.bool_, weight = None)
        np.savetxt('adj.csv', adj, delimiter = ',', fmt = '%.0f')

    def _to_networkx(self) -> nx.DiGraph:
        g : pgv.AGraph = self.convert_to_graphviz()
        return nx.nx_agraph.from_agraph(g)

    def view_k_neighbors(self,
                         node_id: str,
                         k: int = 10
                        ) -> None:
        g : nx.DiGraph = self._to_networkx()
        g_k = pgv.AGraph(strict=True, directed=True)
        g_k.add_node(node_id)

        depth = 0

        def neighbors(g: nx.DiGraph, node_id: str, depth: int) -> None:
            if depth >= k:
                return
            depth += 1
            for neighbor in g.neighbors(node_id):
                g_k.add_edge(node_id, neighbor)
                neighbors(g, neighbor, depth)

        neighbors(g, node_id, depth)

        print(g_k)
        g_k.write('tree.gv')

        

def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--file", type=str, required=True, help="Path to file to parse")
    args = arg_parser.parse_args()

    ast = ASTFileParser(args.file)
    ast.parse()
    ast.to_csv()

    # import ast
    # print(ast.dump(ast.parse(file), indent = 5))

if __name__ == "__main__":
    main()
import argparse
import os
from typing import *
import re

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
        roots = []
        for file in self._relative_files:
            self._filepath = file
            tree = self._get_syntax_tree(file)
            self._root = tree.root_node
            root_id = self.parse()
            roots.append(root_id)

        for root in roots:
            filepath = root.split(' | ')[1]
            self._second_loop(root, self._AST, filepath)
        self._add_edges(self._AST)
        self._add_delayed_assignment_edges(self._AST)
        self._add_delayed_call_edges(self._AST)

    def _add_edges(self, parent: G) -> None:
        # connect import edges to their calls
        for edge_from, edge_to in self._edges_to_add:
            parent.add_edge(edge_from, edge_to)

    def _add_delayed_assignment_edges(self, parent: G) -> None:
        # connect import edges to their calls
        for edge_from, edge_to_file, function_name in self._delayed_assignment_edges_to_add:
            if edge_to_file not in self._assignments or function_name not in self._assignments[edge_to_file]:
                continue
            edge_to = self._assignments[edge_to_file][function_name][1]
            parent.add_edge(edge_from, edge_to)
            parent.add_edge(edge_to, edge_from)
    
    def _add_delayed_call_edges(self, parent: G) -> None:
        # connect calls to their definition
        for edge_from, edge_to_file, function_name in self._delayed_call_edges_to_add:
            if edge_to_file not in self._assignments:
                continue
            edge_to = self._function_definitions[edge_to_file][function_name]
            parent.add_edge(edge_from, edge_to)
            parent.add_edge(edge_to, edge_from)

    def _second_loop(self, node_id: str, parent: G, file: str) -> None:
        # copy all dictionaries for scoping
        # f, i, fd, a, c = self._copy_for_scope()
        # self._function_calls = f
        # self._imports = i
        # self._function_definitions = fd
        # self._assignments = a
        # self._classes = c

        # add assignments
        if parent.get_vertex(node_id).type == 'assignment':
            identifier_node = [n for n in parent.get_vertex(node_id).get_connections() if n.type == 'identifier'][0]
            variable_node = list(parent.get_vertex(node_id).get_connections())[1]
            type_ = variable_node.type
            if variable_node.type == 'call':
                variable_node = list(variable_node.get_connections())[0]
                type_ = variable_node.text
            if file not in self._assignments:
                self._assignments[file] = {}
            self._assignments[file][identifier_node.var_name] = (type_, identifier_node.id)

        # add class methods
        if parent.get_vertex(node_id).type == 'class_definition':
            # add a dictionary entry for the class name
            class_name = list(parent.get_vertex(node_id).get_connections())[0].text
            self._classes[file] = {class_name: {}}

            # traverse the rest of the class definition and add all attributes
            self._class_attribute(file, class_name, parent, node_id)

        # handle each function call vertex
        if parent.get_vertex(node_id).type == 'call':
            self._call_to_definition(parent.get_vertex(node_id), parent, file)
        
        # handle other imports (constants) from other files
        if file in self._imports:
            if parent.get_vertex(node_id).type == 'identifier' and not (parent.get_parent(node_id).type == 'aliased_import' or parent.get_parent(node_id).type == 'dotted_name'):
                # TODO: cache to save time
                possible_imports = list(self._imports[file].keys())
                import_ids = [i for _, (i, _) in self._imports[file].items()]
                paths = [p for _, (_, p) in self._imports[file].items()]
                                        
                txt = parent.get_vertex(node_id).text
                if any([re.match(r'(^' + s + r'\.|^' + s + r'$)', txt) for s in possible_imports]):
                    func, import_id, path = [
                        (f, i, p if i.startswith('aliased_import') else p + '.' + f if p else f) for f, i, p in zip(possible_imports, import_ids, paths)
                        if txt.startswith(f)
                    ][0]

                    # if there is an identifier that matches an import, add an edge to the import
                    self._edges_to_add.append((node_id, import_id))

                    func_new = (txt if path not in txt else txt[txt.find(path)+1+len(path):]) \
                        if not import_id.startswith('aliased_import') \
                        else (path[path.rfind('.')+1:] if txt == func else txt[txt.find(func) + len(func) + 1:])
                    path_new = (path[:path.rfind(txt)-1] if len(path) - path.rfind(txt) == len(txt) else path) \
                        if not import_id.startswith('aliased_import') \
                        else (path[:path.rfind('.')] if '.' in path else path)
                    
                    # find which file we are importing the constant from
                    imported_from = [f for f in self._relative_files if path_new.replace('.', '/') in f]
                    if imported_from:
                        
                        imported_from = imported_from[0]
                        if imported_from in self._assignments:
                            if func_new in self._assignments[imported_from]:
                                # add edge
                                self._edges_to_add.append((node_id, self._assignments[imported_from][func_new][1]))
                                self._edges_to_add.append((self._assignments[imported_from][func_new][1], node_id))
                        else:
                            self._delayed_assignment_edges_to_add.append((node_id, imported_from, func_new))
               
        # check if the function is defined in the current file
        if file in self._function_definitions and parent.get_parent(node_id) and parent.get_parent(node_id).type == 'call':
            func = parent.get_vertex(node_id).text
            if func in self._function_definitions[file]:
                # add edge
                self._edges_to_add.append((node_id, self._function_definitions[file][func]))
                self._edges_to_add.append((self._function_definitions[file][func], node_id))
        
        # check if the function is part of an import in the current file
        if file in self._imports and parent.get_parent(node_id) and parent.get_parent(node_id).type == 'call':
            possible_imports = list(self._imports[file].keys())
            import_ids = [i for _, (i, _) in self._imports[file].items()]
            paths = [p for _, (_, p) in self._imports[file].items()]
                                    
            txt = parent.get_vertex(node_id).text
            if any([re.match(r'(^' + s + r'\.|^' + s + r'$)', txt) for s in possible_imports]):
                func, import_id, path = [
                    (f, i, p if i.startswith('aliased_import') else p + '.' + f if p else f) for f, i, p in zip(possible_imports, import_ids, paths)
                    if txt.startswith(f)
                ][0]

                func_new = (txt if path not in txt else txt[txt.find(path)+1+len(path):]) \
                    if not import_id.startswith('aliased_import') \
                    else (path[path.rfind('.')+1:] if txt == func else txt[txt.find(func) + len(func) + 1:])
                path_new = (path[:path.rfind(txt)-1] if len(path) - path.rfind(txt) == len(txt) else path) \
                    if not import_id.startswith('aliased_import') \
                    else (path[:path.rfind('.')] if '.' in path else path)
                
                # find which file we are importing the constant from
                imported_from = [f for f in self._relative_files if path_new.replace('.', '/') in f]
                if imported_from:
                    imported_from = imported_from[0]
                    if imported_from in self._function_definitions:
                        if func_new in self._function_definitions[imported_from]:
                            # add edge
                            self._edges_to_add.append((node_id, self._function_definitions[imported_from][func_new]))
                            self._edges_to_add.append((self._function_definitions[imported_from][func_new], node_id))
                    else:
                        self._delayed_call_edges_to_add.append((node_id, imported_from, func_new))
                

        
        # check if the call is an class attribute and find its definition
        if parent.get_parent(node_id) and parent.get_parent(node_id).type == 'call':
            txt = parent.get_vertex(node_id).text
            if '.' in txt:
                object_ = txt[:txt.find('.')]
                # check if object has a type
                if file in self._assignments:
                    if object_ in self._assignments[file]:
                        class_, object_node_id = self._assignments[file][object_]
                        # check if object type is defined in the current file
                        if file in self._classes:
                            if class_ in self._classes[file]:
                                if txt[txt.find('.')+1:] in self._classes[file][class_]:
                                    # add edge
                                    self._edges_to_add.append((node_id, self._classes[file][class_][txt[txt.find('.')+1:]]))
                                    self._edges_to_add.append((self._classes[file][class_][txt[txt.find('.')+1:]], node_id))             

        # connect identifiers to their assignments
        txt = parent.get_vertex(node_id).text
        if parent.get_parent(node_id) and parent.get_parent(node_id).type != 'assignment':
            if file in self._assignments:
                if txt in self._assignments[file]:
                    # add edge
                    self._edges_to_add.append((node_id, self._assignments[file][txt][1]))
                    # self._edges_to_add.append((self._assignments[file][txt][1], node_id))

        # recurse over neighbors/children
        for neighbor in parent.get_vertex(node_id).get_connections():
            self._second_loop(neighbor.id, parent, file)

    def _class_attribute(self, file: str, class_name: str, parent: G, class_root_node_id: str) -> None:
        # record all class attributes
        for child in parent.get_vertex(class_root_node_id).get_connections():
            if child.type == 'function_definition':
                # add a dictionary entry for the function name
                function_name = list(parent.get_vertex(child.id).get_connections())[0].text
                self._classes[file][class_name][function_name] = child.id

            # traverse the rest of the function definition and add all attributes
            self._class_attribute(file, class_name, parent, child.id)


    def _call_to_definition(self, call_node: N, parent: G, file: str) -> None:
        # get the full function name for a specific call node
        function_name = [func for (func, id) in self._function_calls[file].items() if id == call_node.id]
        if not function_name:
            return
        function_name = function_name[0]
        
        # check if the call is an import and find which file its imported from
        # TODO:

        
        # function_name = list(parent.get_vertex(call_node.id).get_connections())[0]
        # print(function_name, function_name.text)
        # if call_node... in self._imports[file]:
        
        # check if the call function is in the list of saved functions
        # for f in self._function_definitions:
        #     for func_name, func_node_id in self._function_definitions[f].items():
        #         if func_node_id == call_node_id:
        #             # add edge
        #             parent.add_edge(call_node_id, func_node_id)
        #             parent.add_edge(func_node_id, call_node_id)
        #             return
        #         if '.' in func_name:
        #             path = func_name[:func_name.rfind('.')]
        #             func_name = func_name[func_name.rfind('.')+1:]
        #             self._call_to_definition(call_node_id, parent, file)
                    
def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--dir", type=str, required=True, help="Path to directory to parse")
    args = arg_parser.parse_args()

    ast = ASTCodebaseParser(args.dir)
    ast.parse_dir()
    ast.convert_to_graphviz()

    # ast.view_k_neighbors("module | ../pygamelib/pygamelib/functions.py_0", 2)

    # import ast
    # print(ast.dump(ast.parse(file), indent = 5))

if __name__ == "__main__":
    main()

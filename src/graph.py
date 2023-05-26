from typing import *

class Node:
    def __init__(self, 
                 id: str,
                 start: str,
                 end: str,
                 text: Optional[str] = None,
                 type: Optional[str] = None,
                 var_name: Optional[str] = None) -> None:
        self._id = id
        self._start = start
        self._end = end
        self._text = text
        self._type = type
        self._var_name = var_name
        self._adjacent : Dict[Node, int] = {}

    @property
    def id(self) -> str:
        return self._id
    
    @id.setter
    def id(self, value: str) -> None:
        raise Exception("id is read-only.")

    @property
    def text(self) -> str:
        return self._text if self._text else ""

    @text.setter
    def text(self, value: str) -> None:
        self._text = value

    @property
    def type(self) -> str:
        return self._type if self._type else ""
    
    @type.setter
    def type(self, value: str) -> None:
        self._type = value

    @property
    def var_name(self) -> str:
        return self._var_name if self._var_name else ""

    @var_name.setter
    def var_name(self, value: str) -> None:
        self._var_name = value

    def __str__(self) -> str:
        return str(self.id) + ' adjacent: ' + str([x.id for x in self._adjacent])

    def add_neighbor(self, neighbor: "Node", weight : float = 1.) -> None:
        self._adjacent[neighbor] = weight

    def get_connections(self) -> List["Node"]:
        return self._adjacent.keys()

    def get_weight(self, neighbor: "Node") -> float:
        return self._adjacent[neighbor]

class Graph:
    def __init__(self) -> None:
        self.vert_dict : Dict[str: Node]= {}
        self.num_vertices : int = 0
    
    def __iter__(self) -> Iterator[Node]:
        return iter(self.vert_dict.values())
    
    def __str__(self) -> str:
        return '----------\n' + \
            '\n-\n'.join(str(node) for node in iter(self)) + \
            '\n----------'

    def add_vertex(self, node: Node) -> Node:
        self.num_vertices = self.num_vertices + 1
        self.vert_dict[node.id] = node
        return node.id

    def get_vertex(self, id: str) -> Node:
        if id in self.vert_dict:
            return self.vert_dict[id]
        else:
            return None
        
    def add_edge(self, from_: str, to_: str, weight: float = 1, bi: bool = False) -> None:
        if from_ not in self.vert_dict:
            raise Exception(f"Vertex {from_} not in graph.")
        if to_ not in self.vert_dict:
            raise Exception(f"Vertex {to_} not in graph.")
        self.vert_dict[from_].add_neighbor(self.vert_dict[to_], weight)
        if bi:
            self.vert_dict[to_].add_neighbor(self.vert_dict[from_], weight)
    
    def get_vertices(self) -> List[str]:
        return list(self.vert_dict.keys())
    
    def get_parent(self, id: str) -> Node:
        for node in self:
            for neighbor in node.get_connections():
                if neighbor.id == id:
                    return node
        return None

if __name__ == "__main__":
    print(Node('a', 'b', 'c'))
    print(Node('a', 'b', 'c').id)

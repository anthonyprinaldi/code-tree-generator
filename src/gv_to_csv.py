import graphviz
import networkx as nx
import argparse
import pandas as pd
import numpy as np

def main(args):
    G = nx.DiGraph(nx.nx_pydot.read_dot(args.file))
    print(G)
    nodes = [n for n in G.nodes()]
    feats = [feat['xlabel'] for node, feat in dict(G.nodes(data=True)).items()]
    node_feats = pd.DataFrame({'node': nodes, 'feat': feats})
    node_feats.to_csv('node_feats.csv', index = False)
    adj = nx.to_numpy_array(G)
    np.savetxt('adj.csv', adj, delimiter = ',', fmt = '%.0f')


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type = str, default = 'tree.gv', help="The DOT file to convert")
    args = parser.parse_args()
    main(args)
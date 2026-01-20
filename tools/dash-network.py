# %%
import networkx as nx
import regex as re
from matplotlib import pyplot as plt


function = re.compile(r"^def ([a-z_]*)\(")
fout = re.compile(r'^    Output\("([a-z_]*)", "([a-z_]*)"[\),]')
fin = re.compile(r'^    Input\("([a-z_]*)", "([a-z_]*)"\),')
graph = nx.DiGraph()
with open("phroc-dash-2.py", "r") as f:
    code = f.read().splitlines()
for line in code[::-1]:
    if function.match(line):
        func = function.findall(line)[0]
    elif fout.match(line):
        o = fout.findall(line)[0]
        graph.add_edge(func, "::".join(o))
    elif fin.match(line):
        i = fin.findall(line)[0]
        graph.add_edge("::".join(i), func)

fig, ax = plt.subplots(dpi=300, figsize=(20, 10))
startpoint = "get_samples_table_user_changes"
startpoint = "restore_session"
nodelist = nx.descendants(graph, startpoint) | {startpoint}
graph = graph.subgraph(nodelist)
pos = nx.nx_agraph.graphviz_layout(graph, prog="dot")
nx.draw_networkx(
    graph,
    ax=ax,
    pos=pos,
    with_labels=False,
    node_color=["xkcd:azure" if "::" in n else "xkcd:strawberry" for n in graph.nodes],
    arrowstyle="-|>",
    arrowsize=20,
)
text = nx.draw_networkx_labels(
    graph,
    ax=ax,
    pos=pos,
    labels={n: n.replace("::", "\n") for n in graph.nodes},
)
# for _, t in text.items():
#     t.set_rotation(-15)
fig.tight_layout()
fig.savefig("output.png")

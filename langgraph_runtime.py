"""
langgraph_runtime.py

A lightweight LangGraph-like runtime shim used for the interview/demo.
It provides Node and Graph primitives similar to many workflow SDKs.
Replace this module with a real LangGraph SDK adapter when porting.
"""

from typing import Callable, Dict, Optional, Any, Tuple


class Node:
    """
    Node: wrap an action function. The action function receives (ctx, input_text)
    and returns a tuple: (output_text, next_node_key (optional), updated_data (optional dict))
    """
    def __init__(self, key: str, action: Callable[[Dict[str, Any], str], Tuple[str, Optional[str], Dict[str, Any]]]):
        self.key = key
        self._action = action

    def run(self, ctx: Dict[str, Any], message: str):
        return self._action(ctx, message)


class Graph:
    """
    Graph: holds nodes and edges, executes routing in a ReAct-style loop by using
    the Supervisor node (decision logic) and calling node.run().
    """

    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.supervisor_key: Optional[str] = None

    def add_node(self, node: Node):
        self.nodes[node.key] = node

    def set_supervisor(self, key: str):
        self.supervisor_key = key

    def run_once(self, ctx: Dict[str, Any], message: str):
        """
        Execute the supervisor to decide which node to run, then run it.
        Supervisor node should return (node_to_call, None, optional)
        """
        if not self.supervisor_key:
            raise RuntimeError("Supervisor not set on graph.")
        # Supervisor decides
        sup = self.nodes[self.supervisor_key]
        sup_out_text, sup_next, sup_data = sup.run(ctx, message)
        # Supervisor's sup_out_text is debug / not shown; sup_next is node key
        node_key = sup_next
        if not node_key:
            # default to fallback
            node_key = ctx.get("_fallback_node", "regular_chat")
        node = self.nodes.get(node_key)
        if not node:
            return f"Node '{node_key}' not found.", ctx
        out_text, next_node, data = node.run(ctx, message)
        # update context
        if data:
            ctx.update(data)
        # optionally allow node to suggest next node by setting ctx['_next_node']
        if next_node:
            ctx['_next_node'] = next_node
        return out_text, ctx

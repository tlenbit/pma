from .base import DirectoryABC, Node
from .note import Note


def get_children_notes(root: Node):
    result = []

    stack: list[Node] = [root]

    while stack:
        cur = stack.pop()
        if isinstance(cur, Note):
            result.append(cur)
        if isinstance(cur, DirectoryABC):
            stack.extend(cur.get_children())

    return result

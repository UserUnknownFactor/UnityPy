# -*- coding: utf-8 -*-
from __future__ import annotations
import os
from ..enums import ClassIDType
from ..classes import GameObject

class GameObjectNode(object):
    "GameObject Tree structure"

    SPACER =  '    '
    BRANCH = '│   '
    TEE =    '├── '
    LAST =   '└── '

    def __init__(self, name: str='', game_obj: GameObject=None, parent: GameObjectNode=None, children: list=None, attachments: list=None):
        self.name: str = name
        self.content: GameObject = game_obj
        self.parent: GameObjectNode = parent
        self.children: list = []
        self.attachments: list = []
        if children is not None:
            for child in children:
                self.add_child(child)
        if attachments is not None:
            for attachment in attachments:
                self.add_attachment(attachment)

    def __repr__(self):
        typ = ((':' + self.content.type.name) if self.content.type != ClassIDType.GameObject else '')
        return f"<Tree: {self.name}{typ} (children: {len(self.children)}; attachments: {len(self.attachments)})>"

    def add_child(self, node):
        if node is None:
            return
        assert isinstance(node, GameObjectNode)
        node.parent = self
        self.children.append(node)

    def add_attachment(self, node):
        if node is None:
            return
        self.attachments.append(node)

    def find_path_up(self):
        path = [allowed_path(self.name)] if self.name else []
        p = self
        while p := p.parent:
            path += [allowed_path(p.name)]
        return os.sep.join(reversed(path)).strip("\\")

    def find_child(self, path_id):
        if not path_id: return None
        if self.content.m_pathID == self.m_pathID: return self
        for node in self.attachments:
            if node.m_pathID == path_id:
                return node
        for node in self.children:
            if len(node.children):
                ret = node.find_child(path_id)
                if ret is not None:
                    return ret
        return None

    def print_tree(self, prefix: str=''):
        contents = self.attachments
        pointers = [self.TEE] * (len(contents) - 1) + ([self.LAST] if not len(self.children) else [self.TEE])
        for pointer, node in zip(pointers, contents):
            yield prefix + pointer + node.type.name + f" (m_fileID: {node.m_fileID}; m_pathID: {node.m_pathID})"
        contents = self.children
        pointers = [self.TEE] * (len(contents) - 1) + [self.LAST]
        for pointer, node in zip(pointers, contents):
            yield prefix + pointer + node.name
            extension = self.BRANCH if pointer == self.TEE else self.SPACER
            yield from node.print_tree(prefix=prefix+extension)

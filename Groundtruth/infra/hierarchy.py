from __future__ import annotations

from .util import cloneable, parse_bound
from copy import deepcopy, copy
from enum import Enum
from typing import Deque, Generator, List, Set, Tuple, Union, cast, Dict
from collections import deque
import xml.etree.ElementTree as ET
import logging

ActionType = Enum('ActionType', ['SWIPE', 'RESTART', 'BACK', 'CLICK', 'LONGCLICK', 'TEXT', 'CHECK'])

class Element:
    _index: int
    _resource_id: str; _class: str; _package: str; _content_desc: str
    _text: str; _static_text: str; _dynamic_text: str
    _checkable: bool; _checked: bool; _clickable: bool; _focusable: bool; _focused: bool
    _enabled: bool ; _scrollable: bool; _long_clickable: bool
    _password: bool
    _selected: bool
    _visible_to_user: bool
    _bounds: Tuple[int, int, int, int]
    
    @cloneable
    def __init__(self, _from: Union[ET.Element, Element, dict, None] = None):
        assert not isinstance(_from, Element)
        if _from == None:
            self._attrib = None
            return 

        get = (lambda x, y="": _from.get(x, default=y)) if isinstance(_from, ET.Element) else \
            (lambda x, y="": cast(dict, _from).get(x, y))
        self._attrib = _from.attrib if type(_from) == ET.Element else _from
        self._index = int(get('index'))
        self._resource_id = get('resource-id').split('/')[-1].strip()
        self._class = get('class').strip()
        self._package = get('package').strip()
        self._checkable = get('checkable') == 'true'
        self._checked = get('checked') == 'true'
        self._clickable = get('clickable') == 'true'
        self._focusable = get('focusable') == 'true'
        self._focused = get('focused') == 'true'
        self._enabled = get('enabled') == 'true'
        self._scrollable = get('scrollable') == 'true'
        self._long_clickable = get('long-clickable') == 'true'
        self._password = get('password') == 'true'
        self._selected = get('selected') == 'true'
        self._visible_to_user = get('visible-to-user', 'true') == 'true'
        self._bounds = cast(Tuple[int, int, int, int], 
                            tuple(map(int, parse_bound(get('bounds')))))
        self._content_desc = get('content-desc').strip()
        self._text = get('text').strip()

        assert len(self._bounds) == 4, self._bounds
        self._dynamic_text = self._content_desc if len(self._content_desc) > 0 else self._text
        self._static_text = type(self).extract_static_text(self._dynamic_text)

    @staticmethod
    def extract_static_text(text: str) -> str:
        return text
    
    def is_shown_to_user(self) -> bool:
        return self._visible_to_user

    def is_interactable(self) -> bool:
        return self.is_shown_to_user() and len(self._available_actions()) > 0

    def get_mid_point(self) -> Tuple[int, int]:
        return (self._bounds[0] + self._bounds[2]) // 2, (self._bounds[1] + self._bounds[3]) // 2

    def __str__(self) -> str: # type: ignore
        return f"{self._class}@{self._package}/{self._resource_id}#{self._content_desc}#{self._static_text}"

    def __hash__(self) -> int: # type: ignore
        return hash(str(self))

    def to_widget(self) -> Union[Widget, None]:
        if not self.is_shown_to_user():
            return None
        try:
            return Widget(self, cast(List[Union[ActionType, str]], self._available_actions()))
        except Exception as e:
            raise e

    def _available_actions(self) -> List[ActionType]:
        ret = []
        if self._class == "android.widget.EditText":
            ret.append(ActionType.TEXT)
        else:
            if self._checkable:
                ret.append(ActionType.CHECK)
            if self._clickable:
                ret.append(ActionType.CLICK)
            if self._long_clickable:
                ret.append(ActionType.LONGCLICK)
        if self._scrollable:
            ret.append(ActionType.SWIPE)
        return ret

    def __str__(self) -> str:
        description = []
        if len(self._content_desc) > 0:
            description.append(f"accessibility information: {self._content_desc}")
        if len(self._resource_id) > 0:
            description.append(f"resource_id: {self._resource_id.split('/')[-1]}")
        if len(self._text) > 0:
            description.append(f"text: {self._text}")
        return f"a View{' (' + ', '.join(description) + ')' if len(description) != 0 else ''}"

    def is_dull(self) -> bool:
        return len(self._content_desc) == 0 \
                and len(self._resource_id) == 0 \
                and len(self._text) == 0

Element = Element

class Widget(Element):
    _action_types: List[ActionType]

    @cloneable
    def __init__(self, _from: ET.Element|Element|Widget|dict|None = None,
                 _action_types: Union[List[Union[ActionType, str]], None] = None):
        assert not isinstance(_from, Widget)
        super().__init__(_from)
        if _from != None:
            # here we should do a inferrence
            self._action_types = [(ActionType[ty.upper()] if isinstance(ty, str) else ty) for ty in _action_types] \
                    if _action_types is not None else self._available_actions()
    def to_events(self) -> List[Event]:
        #print(self._action_types)
        return [Event(self, a) for a in self._action_types]

class Event(Widget):
    _action: ActionType
    _params: list

    @cloneable
    def __init__(self, _from: ET.Element|Widget|Event|dict|None = None, 
                 _action: Union[ActionType, str, None] = None, _params: list = []):
        super().__init__(_from)
        assert _action is not None
        self._action = ActionType[_action.upper()] if isinstance(_action, str) else _action
        self._params = [x for x in _params]
        if _from is not None:
            # the event in source testcase may not satisfy this property
            # assert self._action in self._action_types
            pass
            
    @staticmethod
    def restart() -> Event:
        return Event(_action=ActionType.RESTART, _from=None)

    @staticmethod
    def back() -> Event:
        return Event(_action=ActionType.BACK, _from=None)

    def add_param(self, param: str):
        self._params = [param]

    def need_param(self) -> bool:
        return self._action == ActionType.TEXT

    def __str__(self) -> str:
        if self._action == ActionType.RESTART:
            return "restart"
        elif self._action == ActionType.BACK:
            return "back"
        elif self._action == ActionType.TEXT:
            return super().__str__() + f" to edit text {', '.join(self._params)}"
        else:
            return super().__str__() + f" to {self._action.name.lower()} {', '.join(self._params)}"
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Event):
            return False
        return self._text == other._text and self._action == other._action \
                and self._content_desc == other._content_desc and self._resource_id == other._resource_id \
                and self._class == other._class

class UIHierarchy:
    STATIC_TEXTS:Set[str] = set()

    _nodes: List[Node]
    _children: List[Node]
    class Node(Element):
        _depth: int
        _children: List[Node]
        @cloneable
        def __init__(self, _from: Union[Node, Element, ET.Element], _children: List[Node] = [], _depth: int = 1):
            assert not isinstance(_from, Node)
            super().__init__(_from)
            self._children = _children
            self._depth = _depth

        def add_child(self, child: Node):
            self._children.append(child)

        def add_children(self, children: List[Node]):
            for child in children:
                self.add_child(child)

        def __iter__(self):
            return iter(self._children)

        def __deepcopy__(self, memo):
            # only instance of kid can be copied
            result = type(self).__new__(type(self))
            for k, v in self.__dict__.items():
                if k == "_children":
                    setattr(result, k, copy(v))
                else:
                    setattr(result, k, deepcopy(v, memo))
            return result

    @cloneable
    def __init__(self, _from: Union[UIHierarchy, ET.ElementTree, ET.Element]):
        assert not isinstance(_from, UIHierarchy)
        if isinstance(_from, ET.ElementTree):
            _from = _from.getroot()
        self._nodes = []
        self._children = self._build_children(_from)

    def _build_children(self, _from) -> List[Node]:
        return [self._build_from_element(ch) for ch in cast(ET.Element, _from)]
    
    def _build_from_element(self, cur_elem: ET.Element) -> Node:
        q: Deque[Tuple[Node, ET.Element]] = deque()
        def process_elem(elem, father: Node|None = None):
            node = type(self).Node(elem, [], father._depth+1 if father is not None else 1)
            self._nodes.append(node)
            for ch in elem:
                q.append((node, ch))
            return node
        ret = process_elem(cur_elem)
        while len(q) > 0:
            father, child_elem = q.popleft()
            child = process_elem(child_elem, father)
            father.add_child(child)
        return ret

    def events(self) -> List[Event]:
        return sum(map(lambda x: cast(Widget, x.to_widget()).to_events(),
                   filter(lambda x: x.is_interactable(), self._nodes)), [])

    def widgets(self) -> List[Widget]:
        return [cast(Widget, node.to_widget()) for node in \
                   filter(lambda x: x.is_interactable(), self._nodes)]
    
    def __iter__(self):
        return iter(self._nodes)

    def __str__(self) -> str:
        ret = ""
        q: Deque[Node] = deque(self._children)
        while len(q) > 0:
            node = q.popleft()
            ret += "\t"*node._depth + str(node) + '\n'
            for child in reversed(list(node)): # reverse to assure order
                q.appendleft(child)
        return ret

    def find_element(self, match_rule: Dict[str, str], match_type: str = "equal", must_include_point: (int, int) | None = None) -> Element | None:
        if match_type == "equal":
            for node in self._nodes:
                if all([(key in node._attrib and node._attrib[key] == value) for key, value in match_rule.items()]):
                    if must_include_point is not None:
                        x, y = must_include_point
                        if node._bounds[0] <= x <= node._bounds[2] and node._bounds[1] <= y <= node._bounds[3]:
                            return node
                    else:
                        return node
        elif match_type == "include":
            for node in self._nodes:
                if all([(key in node._attrib and value in node._attrib[key]) for key, value in match_rule.items()]):
                    if must_include_point is not None:
                        x, y = must_include_point
                        if node._bounds[0] <= x <= node._bounds[2] and node._bounds[1] <= y <= node._bounds[3]:
                            return node
                    else:
                        return node
        else:
            raise ValueError("match_type should be 'equal' or 'include'")
        return None

Node = UIHierarchy.Node


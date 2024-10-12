from typing import Any, TypedDict, Union, cast, List, Tuple
from enum import IntEnum
from .hierarchy import Element

class ActionType(IntEnum):
    NONE = 0

    CLICK = 1
    SWIPE = 2
    TEXT = 3
    LONGCLICK = 4

    BACK = 5
    ENTER = 6

    RESTART = 7
    STOP = 8

    def __str__(self) -> str:
        actions = {
            ActionType.NONE: "none",
            ActionType.CLICK: "click",
            ActionType.SWIPE: "swipe",
            ActionType.TEXT: "input",
            ActionType.LONGCLICK: "longclick",
            ActionType.BACK: "back",
            ActionType.ENTER: "enter",
            ActionType.RESTART: "restart",
            ActionType.STOP: "stop",
        }
        return actions.get(self, "unknown")

class Action(TypedDict):
    action_type: ActionType
    coords: List[Tuple[int, int]]
    message: str
    clear: bool
    element: Element

def none_action() -> Action:
    return {"action_type": ActionType.NONE}

def back_action() -> Action:
    return {"action_type": ActionType.BACK}

def enter_action() -> Action:
    return {"action_type": ActionType.ENTER}

def restart_action() -> Action:
    return {"action_type": ActionType.RESTART}

def stop_action() -> Action:
    return {"action_type": ActionType.STOP}

def click_action(element: Element = None, coord: Tuple[int, int] = None) -> Action:
    if element is not None:
        return {"action_type": ActionType.CLICK, "element": element}
    elif coord is not None:
        return {"action_type": ActionType.CLICK, "coords": [coord]}
    else:
        raise Exception("Click action must have either (element field) or (coord field).")

def swipe_action(element: Element = None, coord_from: Tuple[int, int] = None, coord_to: Tuple[int, int] = None) -> Action:
    if element is not None:
        return {"action_type": ActionType.SWIPE, "element": element}
    elif coord_from is not None and coord_to is not None:
        return {"action_type": ActionType.SWIPE, "coords": [coord_from, coord_to]}
    else:
        raise Exception("Swipe action must have either (element field) or (coord_from field and coord_to field).")

def text_action(message: str, clear: bool = True, element: Element = None, coord: Tuple[int, int] = None) -> Action:
    if message is None:
        raise Exception("Text action must have (message field).")
    if element is not None:
        return {"action_type": ActionType.TEXT, "element": element, "message": message, "clear": clear}
    elif coord is not None:
        return {"action_type": ActionType.TEXT, "coords": [coord], "message": message, "clear": clear}
    else:
        raise Exception("Text action must have either (element field) or (coord field).")

def longclick_action(element: Element = None, coord: Tuple[int, int] = None) -> Action:
    if element is not None:
        return {"action_type": ActionType.LONGCLICK, "element": element}
    elif coord is not None:
        return {"action_type": ActionType.LONGCLICK, "coords": [coord]}
    else:
        raise Exception("Longclick action must have either (element field) or (coord field).")

def interact_action(action_type: ActionType, message: str = None, clear: bool = True, element: Element = None, coord: Tuple[int, int] = None, coord_from: Tuple[int, int] = None, coord_to: Tuple[int, int] = None) -> Action:
    match action_type:
        case ActionType.CLICK:
            if element is not None:
                return {"action_type": action_type, "element": element}
            elif coord is not None:
                return {"action_type": action_type, "coords": [coord]}
            else:
                raise Exception("Click action must have either (element field) or (coord field).")
        case ActionType.SWIPE:
            if element is not None:
                return {"action_type": action_type, "element": element}
            elif coord_from is not None and coord_to is not None:
                return {"action_type": action_type, "coords": [coord_from, coord_to]}
            else:
                raise Exception("Swipe action must have either (element field) or (coord_from field and coord_to field).")
        case ActionType.TEXT:
            if message is None:
                raise Exception("Text action must have (message field).")
            if element is not None:
                return {"action_type": action_type, "element": element, "message": message, "clear": clear}
            elif coord is not None:
                return {"action_type": action_type, "coords": [coord], "message": message, "clear": clear}
            else:
                raise Exception("Text action must have either (element field) or (coord field).")
        case ActionType.LONGCLICK:
            if element is not None:
                return {"action_type": action_type, "element": element}
            elif coord is not None:
                return {"action_type": action_type, "coords": [coord]}
            else:
                raise Exception("Longclick action must have either (element field) or (coord field).")
        case _:
            raise Exception("Invalid action type for interact action.")
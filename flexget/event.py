"""
Provides small event framework
"""
from collections import defaultdict
from enum import Enum
from typing import Callable, Dict, List, Union

from loguru import logger

logger = logger.bind(name='event')


class EventType(Enum):
    forget = 'forget'

    config__register = 'config.register'

    manager__before_config_load = 'manager.before_config_load'
    manager__before_config_validate = 'manager.before_config_validate'
    manager__config_updated = 'manager.config_updated'
    manager__db_cleanup = 'manager.db_cleanup'
    manager__db_vacuum = 'manager.db_vacuum'
    manager__initialize = 'manager.initialize'
    manager__upgrade = 'manager.upgrade'
    manager__db_upgraded = 'manager.db_upgraded'
    manager__startup = 'manager.startup'
    manager__execute_started = 'manager.execute.started'
    manager__execute_completed = 'manager.execute.completed'
    manager__daemon_started = 'manager.daemon.started'
    manager__daemon_completed = 'manager.daemon.completed'
    manager__lock_acquired = 'manager.lock_acquired'
    manager__shutdown_requested = 'manager.shutdown_requested'
    manager__shutdown = 'manager.shutdown'
    manager__subcommand_inject = 'manager.subcommand.inject'

    options__register = 'options.register'

    plugin__register = 'plugin.register'

    task_execute_before_plugin = 'task.execute.before_plugin'
    task_execute_after_plugin = 'task.execute.after_plugin'
    task_execute_started = 'task.execute.started'
    task_execute_completed = 'task.execute.completed'


_events: Dict[Union[EventType, str], List[Callable]] = defaultdict(list)


class Event:
    """Represents one registered event."""

    def __init__(self, event_type: Union[EventType, str], func: Callable, priority: int = 128):
        self.event_type = event_type
        self.name = event_type.value if isinstance(event_type, EventType) else event_type
        self.func = func
        self.priority = priority

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    def __eq__(self, other):
        return self.priority == other.priority

    def __lt__(self, other):
        return self.priority < other.priority

    def __gt__(self, other):
        return self.priority > other.priority

    def __str__(self):
        return f'<Event(name={self.name},func={self.func.__name__},priority={self.priority})>'

    __repr__ = __str__

    def __hash__(self):
        return hash((self.event_type, self.func, self.priority))


def event(event_type: EventType, priority: int = 128) -> Callable[[Callable], Callable]:
    """Register event to function with a decorator"""

    def decorator(func):
        add_event_handler(event_type, func, priority)
        return func

    return decorator


def get_events(event_type: Union[EventType, str]) -> List[Event]:
    """
    :param EventType event_type: event name
    :return: List of :class:`Event` for *name* ordered by priority
    """
    if event_type not in _events:
        raise KeyError(f'No such event {event_type}')
    _events[event_type].sort(reverse=True)
    return _events[event_type]


def add_event_handler(
    event_type: Union[EventType, str], func: Callable, priority: int = 128
) -> Event:
    """
    :param EventType event_type: Event type
    :param function func: Function that acts as event handler
    :param priority: Priority for this hook
    :return: Event created
    :rtype: Event
    :raises Exception: If *func* is already registered in an event
    """
    for event_ in _events[event_type]:
        if event_.func == func:
            raise ValueError(
                f'{func.__name__} has already been registered as event listener under name {event_type}'
            )
    logger.trace('registered function {} to event {}', func.__name__, event_type)
    event_ = Event(event_type, func, priority)
    _events[event_type].append(event_)
    return event_


def remove_event_handlers(event_type: Union[EventType, str]):
    """Removes all handlers for given event `event_type`."""
    _events.pop(event_type, None)


def remove_event_handler(event_type: Union[EventType, str], func: Callable):
    """Remove `func` from the handlers for event `event_type`."""
    for e in _events[event_type]:
        if e.func is func:
            _events[event_type].remove(e)


def fire_event(event_type: Union[EventType, str], *args, **kwargs):
    """
    Trigger an event with *name*. If event is not hooked by anything nothing happens. If a function that hooks an event
    returns a value, it will replace the first argument when calling next function.

    :param event_type: Type of event to be called
    :param args: List of arguments passed to handler function
    :param kwargs: Key Value arguments passed to handler function
    """
    if event_type in _events:
        for event in get_events(event_type):
            result = event(*args, **kwargs)
            if result is not None:
                args = (result,) + args[1:]
    return args and args[0]

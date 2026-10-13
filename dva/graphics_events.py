"""Bounded, optional visual notifications; no timing, damage or randomness."""


def emit(run, event_name, **data):
    events = getattr(run, '_visual_events', None)
    if events is not None:
        if len(events) >= 128:
            del events[0]
        events.append(dict(data, event=event_name))


def target(zombie):
    return {'target': id(zombie), 'kind': zombie.kind,
            'direction': zombie.direction, 'distance': zombie.distance}

"""What each EMOTIV headset actually gives this app.

Two different sources of truth, deliberately kept apart:

* The table below is what we know BEFORE connecting, from the headset id alone.
  It is used to describe a device in the picker and to decide which streams to
  ask for. It can be wrong about a model we have never seen.

* The channel names Cortex reports on subscribe are the truth AFTER connecting.
  `layout_for()` takes those names and places them, so a headset we do not
  recognise still draws correctly — the app never assumes five sensors again.

The one capability that cannot be discovered by trying is facial expressions:
MN8 has no `fac` stream at all, so asking for it fails the subscription rather
than degrading. That is why `has_facial` is a stated fact here.
"""

# Approximate 10-20 positions, projected onto a circle seen from above.
# x runs left(-1) to right(+1), y runs front(-1) to back(+1); the nose is at
# (0, -1). Only the sites EMOTIV headsets use are listed.
SENSOR_POSITIONS = {
    "AF3": (-0.32, -0.72), "AF4": (0.32, -0.72), "AFz": (0.0, -0.76),
    "F7": (-0.66, -0.52), "F3": (-0.34, -0.46), "Fz": (0.0, -0.44),
    "F4": (0.34, -0.46), "F8": (0.66, -0.52),
    "FC5": (-0.58, -0.23), "FC1": (-0.22, -0.22), "FC2": (0.22, -0.22),
    "FC6": (0.58, -0.23),
    "T7": (-0.86, 0.0), "C3": (-0.44, 0.0), "Cz": (0.0, 0.0),
    "C4": (0.44, 0.0), "T8": (0.86, 0.0),
    "CP5": (-0.58, 0.23), "CP1": (-0.22, 0.22), "CP2": (0.22, 0.22),
    "CP6": (0.58, 0.23),
    "P7": (-0.66, 0.52), "P3": (-0.34, 0.46), "Pz": (0.0, 0.52),
    "P4": (0.34, 0.46), "P8": (0.66, 0.52),
    "O1": (-0.28, 0.84), "Oz": (0.0, 0.88), "O2": (0.28, 0.84),
}

INSIGHT_CHANNELS = ["AF3", "T7", "Pz", "T8", "AF4"]
EPOC_CHANNELS = ["AF3", "F7", "F3", "FC5", "T7", "P7", "O1",
                 "O2", "P8", "T8", "FC6", "F4", "F8", "AF4"]
MN8_CHANNELS = ["T7", "T8"]

# Keyed by the prefix of the headset id Cortex reports, longest match first.
DEVICES = {
    "INSIGHT2": {"name": "EMOTIV Insight 2", "channels": INSIGHT_CHANNELS, "has_facial": True},
    "INSIGHT": {"name": "EMOTIV Insight", "channels": INSIGHT_CHANNELS, "has_facial": True},
    "EPOCX": {"name": "EMOTIV EPOC X", "channels": EPOC_CHANNELS, "has_facial": True},
    "EPOCPLUS": {"name": "EMOTIV EPOC+", "channels": EPOC_CHANNELS, "has_facial": True},
    "EPOCFLEX": {"name": "EMOTIV EPOC Flex", "channels": [], "has_facial": True},
    "EPOC": {"name": "EMOTIV EPOC", "channels": EPOC_CHANNELS, "has_facial": True},
    "MN8": {"name": "EMOTIV MN8", "channels": MN8_CHANNELS, "has_facial": False},
    "FLEX2": {"name": "EMOTIV Flex 2", "channels": [], "has_facial": True},
    "FLEX": {"name": "EMOTIV Flex", "channels": [], "has_facial": True},
}

UNKNOWN = {"name": "", "channels": [], "has_facial": True}


def describe(headset_id: str) -> dict:
    """Everything we can say about a headset from its id.

    An id we do not recognise comes back with no channels and facial expressions
    assumed present — the subscription result will correct us either way, and
    assuming a capability the person then cannot use is a smaller failure than
    hiding one they have.
    """
    upper = (headset_id or "").upper()
    for prefix in sorted(DEVICES, key=len, reverse=True):
        if upper.startswith(prefix):
            info = dict(DEVICES[prefix])
            info["prefix"] = prefix
            info["known"] = True
            return info
    info = dict(UNKNOWN)
    info["prefix"] = ""
    info["known"] = False
    return info


def streams_for(headset_id: str, want_facial: bool = True) -> list:
    """The streams to subscribe to for this headset.

    `dev` carries contact quality, `eq` carries EEG quality, `com` the mental
    commands, `fac` the facial expressions where they exist.
    """
    streams = ["com", "dev", "eq"]
    if want_facial and describe(headset_id)["has_facial"]:
        streams.append("fac")
    return streams


def has_facial(headset_id: str) -> bool:
    return describe(headset_id)["has_facial"]


def layout_for(channels) -> list:
    """Place channel names on the head, in draw order.

    Returns [(name, x, y), …] with x and y in -1..1. Names we have no position
    for are spread evenly around the rim rather than dropped, so an unfamiliar
    headset still shows every sensor it actually has.
    """
    import math

    names = [str(c) for c in (channels or [])]
    known = [n for n in names if n in SENSOR_POSITIONS]
    unknown = [n for n in names if n not in SENSOR_POSITIONS]

    placed = [(n, *SENSOR_POSITIONS[n]) for n in known]

    for i, name in enumerate(unknown):
        angle = (2 * math.pi * i / max(1, len(unknown))) - math.pi / 2
        placed.append((name, 0.78 * math.cos(angle), 0.78 * math.sin(angle)))

    return placed


def quality_percent(values) -> int:
    """Share of sensors at a usable grade, 0-100.

    Cortex grades contact 0-4; 3 and 4 are the usable ones, which is the same
    line the head map draws green at.
    """
    values = list(values or [])
    if not values:
        return 0
    good = sum(1 for v in values if v >= 3)
    return int(round(100.0 * good / len(values)))


def weak_sensors(quality_map) -> list:
    """Names of the sensors that are not usable right now, in map order."""
    return [name for name, value in (quality_map or {}).items() if value < 3]

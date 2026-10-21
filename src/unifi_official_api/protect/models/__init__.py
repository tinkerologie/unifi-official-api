"""Models for UniFi Protect API."""

from __future__ import annotations

from .alarm import AlarmHub, ArmProfile, ArmProfileSettings, ArmSchedule
from .application import (
    ApplicationInfo,
    POSLineItem,
    PosLineItem,
    POSLocation,
    PosLocation,
    POSTransactionRequest,
    PosTransactionRequest,
    POSTransactionResponse,
    PosTransactionResponse,
    POSTransactionType,
    PosTransactionType,
)
from .bridge import Bridge
from .camera import Camera, CameraChannel, CameraState, CameraType, RecordingMode, VideoMode
from .chime import Chime, ChimeRingSetting
from .doorlock import DoorLock, Doorlock
from .event import Event, EventType, SmartDetectType
from .files import DeviceFile, FileType, RTSPSStream, TalkbackSession
from .fob import Fob, FobArmControlSettings, FobKeypadSettings, KeypadFob
from .light import Light, LightMode
from .link_station import (
    LinkStation,
    LinkStationThreadNetwork,
    LinkStationThreadState,
)
from .liveview import LiveView, LiveViewSlot
from .nvr import NVR, StorageInfo
from .relay import Relay, RelayOutput
from .sensor import (
    BatteryStatus,
    MotionSettings,
    Sensor,
    SensorLedSettings,
    SensorType,
)
from .siren import Siren, SirenLedSettings, SirenStatus
from .speaker import Speaker, SpeakerFeatureFlags, SpeakerState
from .ulp_user import ULPUser, UlpUser, UlpUserStatus
from .user import ProtectUser, User, UserGroup
from .viewer import Viewer, ViewerState
from .viewport import Viewport

__all__ = [
    "NVR",
    "AlarmHub",
    "ApplicationInfo",
    "ArmProfile",
    "ArmProfileSettings",
    "ArmSchedule",
    "BatteryStatus",
    "Bridge",
    "Camera",
    "CameraChannel",
    "CameraState",
    "CameraType",
    "Chime",
    "ChimeRingSetting",
    "DeviceFile",
    "DoorLock",
    "Doorlock",
    "Event",
    "EventType",
    "FileType",
    "Fob",
    "FobArmControlSettings",
    "FobKeypadSettings",
    "KeypadFob",
    "Light",
    "LightMode",
    "LinkStation",
    "LinkStationThreadNetwork",
    "LinkStationThreadState",
    "LiveView",
    "LiveViewSlot",
    "MotionSettings",
    "POSLineItem",
    "POSLocation",
    "POSTransactionRequest",
    "POSTransactionResponse",
    "POSTransactionType",
    "PosLineItem",
    "PosLocation",
    "PosTransactionRequest",
    "PosTransactionResponse",
    "PosTransactionType",
    "ProtectUser",
    "RTSPSStream",
    "RecordingMode",
    "Relay",
    "RelayOutput",
    "Sensor",
    "SensorLedSettings",
    "SensorType",
    "Siren",
    "SirenLedSettings",
    "SirenStatus",
    "SmartDetectType",
    "Speaker",
    "SpeakerFeatureFlags",
    "SpeakerState",
    "StorageInfo",
    "TalkbackSession",
    "ULPUser",
    "UlpUser",
    "UlpUserStatus",
    "User",
    "UserGroup",
    "VideoMode",
    "Viewer",
    "ViewerState",
    "Viewport",
]


import ctypes
from ctypes import c_uint32, c_void_p, c_int32, byref, POINTER

_IS_MAC = (sys.platform == "darwin")
if _IS_MAC:
    _carbon = ctypes.CDLL('/System/Library/Frameworks/Carbon.framework/Carbon')

    # --- Function signatures ---
    GetApplicationEventTarget = _carbon.GetApplicationEventTarget
    GetApplicationEventTarget.restype = c_void_p  # EventTargetRef

    InstallEventHandler = _carbon.InstallEventHandler
    RegisterEventHotKey = _carbon.RegisterEventHotKey
    UnregisterEventHotKey = _carbon.UnregisterEventHotKey
    UnregisterEventHotKey.restype = c_int32
    UnregisterEventHotKey.argtypes = [c_void_p]

    # --- Constants (correct) ---
    kEventClassKeyboard = 0x6B657962  # 'keyb'
    kEventHotKeyPressed = 5

    # Carbon modifier masks
    cmdKey     = 1 << 8
    shiftKey   = 1 << 9
    optionKey  = 1 << 11
    controlKey = 1 << 12

    # --- Structs ---
    class EventTypeSpec(ctypes.Structure):
        _fields_ = [("eventClass", c_uint32),
                    ("eventKind",  c_uint32)]

    class EventHotKeyID(ctypes.Structure):
        _fields_ = [("signature", c_uint32),
                    ("id",        c_uint32)]

    # --- Callback type ---
    EventHandlerUPP = ctypes.CFUNCTYPE(c_int32, c_void_p, c_void_p, c_void_p)

    # Finish argtypes now that types exist
    InstallEventHandler.restype  = c_int32
    InstallEventHandler.argtypes = [
        c_void_p,                 # target
        EventHandlerUPP,          # handler
        c_uint32,                 # numTypes
        POINTER(EventTypeSpec),   # types
        c_void_p,                 # userData
        POINTER(c_void_p),        # outHandler
    ]

    RegisterEventHotKey.restype  = c_int32
    RegisterEventHotKey.argtypes = [
        c_uint32,                 # hotKeyCode
        c_uint32,                 # hotKeyModifiers
        POINTER(EventHotKeyID),   # hotKeyID
        c_void_p,                 # eventTarget
        c_uint32,                 # options
        POINTER(c_void_p),        # outRef
    ]

    # --- Globals to keep references alive ---
    _HOTKEY_REF = c_void_p()
    _EVENT_HANDLER_REF = c_void_p()
    _HOTKEY_CB_REF = None  # prevent GC

    def install_global_hotkey(on_fire, vk_code=49, modifiers=(cmdKey | shiftKey)):
        """
        Registers a global hotkey (default: Cmd+Shift+Space).
        """
        if not _IS_MAC:
            print("[Scaffold] Global hotkey skipped (non-macOS)")
            return False

        def _py_handler():
            try:
                on_fire()
            except Exception as e:
                print(f"[Scaffold] Hotkey handler error: {e}")

        global _HOTKEY_CB_REF, _EVENT_HANDLER_REF, _HOTKEY_REF

        @EventHandlerUPP
        def _hotkey_handler(callRef, eventRef, userData):
            _py_handler()
            return 0  # noErr

        _HOTKEY_CB_REF = _hotkey_handler  # keep alive

        ets = EventTypeSpec(kEventClassKeyboard, kEventHotKeyPressed)
        target = GetApplicationEventTarget()
        status = InstallEventHandler(c_void_p(target), _HOTKEY_CB_REF, 1, byref(ets), None, byref(_EVENT_HANDLER_REF))
        if status != 0:
            print(f"[Scaffold] InstallEventHandler failed: {status}")
            return False

        hotkey_id = EventHotKeyID(signature=0x53636166, id=1)  # 'Scaf'
        status = RegisterEventHotKey(
            c_uint32(vk_code),
            c_uint32(modifiers),
            byref(hotkey_id),
            c_void_p(target),
            c_uint32(0),
            byref(_HOTKEY_REF),
        )
        if status != 0:
            print(f"[Scaffold] RegisterEventHotKey failed: {status}")
            return False

        print("[Scaffold] Global hotkey registered: Cmd+Shift+Space")
        return True

    def uninstall_global_hotkey():
        if not _IS_MAC:
            return
        global _HOTKEY_REF
        if _HOTKEY_REF:
            try:
                UnregisterEventHotKey(_HOTKEY_REF)
            except Exception:
                pass
            _HOTKEY_REF = c_void_p()
            print("[Scaffold] Global hotkey unregistered")
else:
    def install_global_hotkey(on_fire, vk_code=49, modifiers=0): return False
    def uninstall_global_hotkey(): return

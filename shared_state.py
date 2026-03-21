import queue
import threading
from dataclasses import dataclass, field

@dataclass
class SharedState:
    temperature: float | None = None
    humidity: float | None = None
    distance_cm: float | None = None
    gas_value: int = 0
    soil_value: int = 0

    color_r: int = 0
    color_g: int = 0
    color_b: int = 0
    color_clear: int = 0
    lux: float | None = None
    detected_color: str = "desconocido"

    gas_alert: bool = False
    temp_alert: bool = False
    soil_dry: bool = False
    meteor_level: str = "sin_lectura"

    fans_on: bool = False
    rgb_color: str = "apagado"
    status_text: str = "Iniciando"

    camouflage_active: bool = False
    camouflage_until: float = 0.0
    recent_colors: list[str] = field(default_factory=list)
    recent_color_times: list[float] = field(default_factory=list)

    last_good_temp: float | None = None
    last_good_humidity: float | None = None

    total_gas_alerts: int = 0
    total_meteor_events: int = 0
    total_messages: int = 0

    dashboard_message: str = ""
    dashboard_message_until: float = 0.0

state = SharedState()
state_lock = threading.Lock()
stop_event = threading.Event()
mongo_queue = queue.Queue()
command_queue = queue.Queue()

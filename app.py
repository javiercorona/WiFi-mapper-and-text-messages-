# core/app.py
import asyncio
from dataclasses import dataclass
from typing import Dict, List, Optional
import matplotlib.pyplot as plt
import pyqtgraph as pg
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from messaging import MessageManager, TextMessage, CommandMessage
from mapping import Heatmapper, DeviceTracker
from security import CryptoManager, TPMSupport
from visualization import MapWidget, MessageWidget

@dataclass
class AppConfig:
    wifi_scan_interval: float = 5.0
    message_retention_days: int = 7
    max_concurrent_messages: int = 10

class WiFiMeshApp:
    def __init__(self, config: AppConfig):
        self.config = config
        
        # Core Components
        self.crypto = CryptoManager(tpm_fallback=True)
        self.message_manager = MessageManager(
            crypto=self.crypto,
            retention_days=config.message_retention_days
        )
        self.heatmapper = Heatmapper()
        self.device_tracker = DeviceTracker()
        
        # UI Components
        self.map_widget = MapWidget()
        self.message_widget = MessageWidget()
        
        # Integrated Visualization
        self._setup_unified_ui()

    def _setup_unified_ui(self):
        """Combine mapping and messaging in single view"""
        self.main_window = pg.GraphicsLayoutWidget()
        
        # Top: Mapping display
        self.main_window.addItem(self.map_widget, row=0, col=0)
        
        # Bottom: Split message/map controls
        splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        splitter.addWidget(self.message_widget)
        splitter.addWidget(pg.PlotWidget())  # Mini-map
        
        self.main_window.addItem(splitter, row=1, col=0)
        
        # Connect signals
        self.message_widget.new_message.connect(self._send_message)
        self.map_widget.device_selected.connect(self._show_device_messages)

    async def run(self):
        """Main application loop"""
        tasks = [
            self._scan_loop(),
            self._message_loop(),
            self._update_ui()
        ]
        await asyncio.gather(*tasks)

    async def _scan_loop(self):
        """Periodic WiFi scanning"""
        while True:
            scan_data = await self._perform_scan()
            self.heatmapper.update(scan_data)
            self.device_tracker.update_devices(scan_data)
            await asyncio.sleep(self.config.wifi_scan_interval)

    async def _message_loop(self):
        """Handle incoming/outgoing messages"""
        while True:
            msg = await self.message_manager.receive()
            if isinstance(msg, TextMessage):
                self.message_widget.display_message(msg)
            elif isinstance(msg, CommandMessage):
                self._handle_command(msg)

    async def _update_ui(self):
        """Refresh visualization"""
        while True:
            self.map_widget.update(
                heatmap=self.heatmapper.current_heatmap,
                devices=self.device_tracker.active_devices
            )
            await asyncio.sleep(0.1)

    def _send_message(self, text: str, target: Optional[str] = None):
        """Send text message to specific device or broadcast"""
        msg = TextMessage(
            sender=self.crypto.device_id,
            content=text,
            recipient=target
        )
        self.message_manager.queue_message(msg)
        
        # Visual feedback
        self.map_widget.highlight_communication(
            source=self.crypto.device_id,
            target=target
        )

    def _show_device_messages(self, device_id: str):
        """Display message history with selected device"""
        messages = self.message_manager.get_conversation(device_id)
        self.message_widget.show_conversation(messages)

# messaging/message.py
class TextMessage:
    def __init__(self, sender: str, content: str, recipient: Optional[str] = None):
        self.timestamp = time.time()
        self.sender = sender
        self.content = content
        self.recipient = recipient  # None = broadcast

class MessageManager:
    def __init__(self, crypto: CryptoManager, retention_days: int):
        self.crypto = crypto
        self.messages = MessageStore(retention_days)
        
    async def receive(self) -> Union[TextMessage, CommandMessage]:
        """Decrypt and validate incoming messages"""
        # Implementation using Protocol Buffers
        
    def queue_message(self, message: Union[TextMessage, CommandMessage]):
        """Encrypt and send message"""
        # Handles both direct and multicast

# visualization/widgets.py
class MapWidget(pg.PlotWidget):
    device_selected = QtCore.Signal(str)
    
    def update(self, heatmap, devices):
        """Update map with new scanning data"""
        self.clear()
        self.plot_heatmap(heatmap)
        self.plot_devices(devices)
        
    def highlight_communication(self, source: str, target: Optional[str]):
        """Visualize message paths"""
        if target:
            self.plot_line(source, target, color='green')
        else:
            self.plot_broadcast(source)

class MessageWidget(QtWidgets.QTextEdit):
    new_message = QtCore.Signal(str, Optional[str])
    
    def display_message(self, message: TextMessage):
        """Append message to conversation view"""
        prefix = "[Direct] " if message.recipient else "[Broadcast] "
        self.append(f"{prefix}{message.sender}: {message.content}")
        
    def show_conversation(self, messages: List[TextMessage]):
        """Display full conversation history"""
        self.clear()
        for msg in messages:
            self.append(f"{msg.sender}: {msg.content}")

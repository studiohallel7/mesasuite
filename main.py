#!/usr/bin/python3
# 📘 SOFIA MOBILE RUNTIME - OMOE NATIVE HARDWARE EDITION (FULL MERGE + DYNAMIC APPS + SCAN FIX)
# Arquitetura: Semântica + HAL Real + JNI + Active Desktop + Micro-Universo + Dynamic Loader
# Novidades: Lançador de Apps Internos (.appicon), Varredura de Sistema, Multitarefa Híbrida, Applets Menu
# Autor: Dono & Aurora
# Status: FINALIZADO.

import os
import sys
import subprocess
import time
import json
import shutil
import mimetypes
import socket
import threading
import webbrowser
import shlex
import importlib.util # Essencial para carregar apps dinâmicos
from abc import ABC, abstractmethod
from datetime import datetime

# Kivy / KivyMD Imports
from kivymd.app import MDApp
from kivy.lang import Builder
from kivy.core.window import Window
from kivy.animation import Animation
from kivy.metrics import dp
from kivymd.uix.card import MDCard
from kivy.clock import Clock
from kivy.properties import NumericProperty, BooleanProperty, StringProperty, ListProperty, DictProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import Image
from kivymd.uix.button import MDIconButton, MDFlatButton, MDRaisedButton, MDFloatingActionButton
from kivy.uix.floatlayout import FloatLayout
from kivymd.uix.floatlayout import MDFloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivymd.uix.list import OneLineAvatarIconListItem, TwoLineAvatarIconListItem, OneLineIconListItem
from kivymd.uix.label import MDLabel, MDIcon
from kivymd.uix.menu import MDDropdownMenu
from kivy.uix.scrollview import ScrollView
from kivymd.uix.textfield import MDTextFieldRect, MDTextField
from kivy.uix.modalview import ModalView
from kivy.graphics import Color, Ellipse, Rectangle, RoundedRectangle
from kivy.utils import platform
from kivy.core.clipboard import Clipboard
from kivy.storage.jsonstore import JsonStore # Persistência
from kivymd.uix.gridlayout import MDGridLayout # Para o Picker

# ============================================================================
# 🔧 CAMADA DE ABSTRAÇÃO DE HARDWARE (HAL) - IMPLEMENTAÇÃO REAL (JNI)
# ============================================================================
IS_ANDROID = platform == 'android'

if IS_ANDROID:
    from jnius import autoclass, cast
    from android.runnable import run_on_ui_thread

    # --- MAPEAMENTO DE CLASSES JAVA ---
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    Context = autoclass('android.content.Context')
    Intent = autoclass('android.content.Intent')
    Settings = autoclass('android.provider.Settings')
    Uri = autoclass('android.net.Uri')
    AudioManager = autoclass('android.media.AudioManager')
    BatteryManager = autoclass('android.os.BatteryManager')
    WifiManager = autoclass('android.net.wifi.WifiManager')
    BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
    CameraManager = autoclass('android.hardware.camera2.CameraManager')
    ActivityManager = autoclass('android.app.ActivityManager')

    # Constantes Android
    FLAG_ACTIVITY_NEW_TASK = 268435456

    class AndroidUtils:
        @staticmethod
        def get_activity():
            return PythonActivity.mActivity

        @staticmethod
        def get_context():
            return AndroidUtils.get_activity().getApplicationContext()

        @staticmethod
        def get_package_manager():
            return AndroidUtils.get_context().getPackageManager()

        @staticmethod
        def toast(text):
            try:
                Toast = autoclass('android.widget.Toast')
                String = autoclass('java.lang.String')
                Toast.makeText(AndroidUtils.get_context(), String(text), Toast.LENGTH_SHORT).show()
            except Exception as e:
                print(f"Erro Toast: {e}")

        # --- GERENCIAMENTO DE PROCESSOS ---
        @staticmethod
        def kill_background_process(package_name):
            try:
                am = cast('android.app.ActivityManager', AndroidUtils.get_activity().getSystemService(Context.ACTIVITY_SERVICE))
                # Requer permissão KILL_BACKGROUND_PROCESSES no buildozer.spec
                am.killBackgroundProcesses(package_name)
                AndroidUtils.toast(f"Bordoada aplicada em {package_name}! RAM liberada.")
            except Exception as e:
                print(f"Erro ao matar processo {package_name}: {e}")
                AndroidUtils.toast(f"Falha ao matar: {e}")

        # --- CONTROLE DE BRILHO ---
        @staticmethod
        def has_write_settings_permission():
            try:
                return Settings.System.canWrite(AndroidUtils.get_context())
            except:
                return False

        @staticmethod
        def request_write_settings_permission():
            try:
                intent = Intent(Settings.ACTION_MANAGE_WRITE_SETTINGS)
                uri = Uri.parse("package:" + AndroidUtils.get_context().getPackageName())
                intent.setData(uri)
                intent.addFlags(FLAG_ACTIVITY_NEW_TASK)
                AndroidUtils.get_activity().startActivity(intent)
                AndroidUtils.toast("Permita modificar configurações para ajustar brilho.")
            except Exception as e:
                print(f"Erro permissão settings: {e}")

        @staticmethod
        def set_brightness(value_0_to_100):
            if not AndroidUtils.has_write_settings_permission():
                AndroidUtils.request_write_settings_permission()
                return
            try:
                val = int((value_0_to_100 / 100.0) * 255)
                content_resolver = AndroidUtils.get_context().getContentResolver()
                Settings.System.putInt(content_resolver, Settings.System.SCREEN_BRIGHTNESS, val)
            except Exception as e:
                print(f"Erro brilho: {e}")

        # --- CONTROLE DE VOLUME ---
        @staticmethod
        def set_volume(value_0_to_100):
            try:
                audio_service = cast('android.media.AudioManager', AndroidUtils.get_activity().getSystemService(Context.AUDIO_SERVICE))
                max_vol = audio_service.getStreamMaxVolume(AudioManager.STREAM_MUSIC)
                target_vol = int((value_0_to_100 / 100.0) * max_vol)
                audio_service.setStreamVolume(AudioManager.STREAM_MUSIC, target_vol, 0)
            except Exception as e:
                print(f"Erro volume: {e}")

        @staticmethod
        def get_volume():
            try:
                audio_service = cast('android.media.AudioManager', AndroidUtils.get_activity().getSystemService(Context.AUDIO_SERVICE))
                curr = audio_service.getStreamVolume(AudioManager.STREAM_MUSIC)
                maxx = audio_service.getStreamMaxVolume(AudioManager.STREAM_MUSIC)
                return (curr / maxx) * 100
            except:
                return 50

        # --- LANTERNA (TORCH) ---
        @staticmethod
        def toggle_torch(status):
            try:
                camera_manager = cast('android.hardware.camera2.CameraManager', AndroidUtils.get_activity().getSystemService(Context.CAMERA_SERVICE))
                # Geralmente a câmera 0 é a traseira com flash
                camera_id = camera_manager.getCameraIdList()[0]
                camera_manager.setTorchMode(camera_id, status)
            except Exception as e:
                print(f"Erro lanterna: {e}")

        # --- WI-FI (COMPLEXO) ---
        @staticmethod
        def get_wifi_manager():
            return cast('android.net.wifi.WifiManager', AndroidUtils.get_activity().getSystemService(Context.WIFI_SERVICE))

        @staticmethod
        def is_wifi_enabled():
            try:
                return AndroidUtils.get_wifi_manager().isWifiEnabled()
            except:
                return False

        @staticmethod
        def set_wifi_enabled(enable):
            try:
                # Android < 10 (Q) permite toggle direto
                wm = AndroidUtils.get_wifi_manager()
                success = wm.setWifiEnabled(enable)
                if not success:
                    # Android 10+ bloqueia. Abrimos o painel flutuante.
                    AndroidUtils.open_settings_panel(Settings.ACTION_WIFI_SETTINGS)
            except Exception as e:
                print(f"Erro WiFi Toggle: {e}")
                AndroidUtils.open_settings_panel(Settings.ACTION_WIFI_SETTINGS)

        @staticmethod
        def get_scan_results():
            """Obtém lista de redes Wi-Fi nativamente (Requer Location)"""
            try:
                wm = AndroidUtils.get_wifi_manager()
                wm.startScan() # Pode ser throttled pelo Android
                results = wm.getScanResults()
                networks = []
                if results:
                    for r in results.toArray():
                        ssid = r.SSID
                        level = r.level # dBm
                        quality = max(0, min(100, int((level + 100) * 2)))
                        if ssid:
                            networks.append({'ssid': ssid, 'quality': quality, 'level': level})
                networks.sort(key=lambda x: x['quality'], reverse=True)
                return networks
            except Exception as e:
                print(f"Erro Scan WiFi: {e}")
                return []

        @staticmethod
        def get_current_ssid():
            try:
                wm = AndroidUtils.get_wifi_manager()
                info = wm.getConnectionInfo()
                ssid = info.getSSID()
                # Remove aspas que o Android coloca
                if ssid: return ssid.replace('"', '')
                return "Desconectado"
            except: return "Erro WiFi"

        # --- BLUETOOTH ---
        @staticmethod
        def get_bluetooth_adapter():
            return BluetoothAdapter.getDefaultAdapter()

        @staticmethod
        def is_bluetooth_enabled():
            try:
                adapter = AndroidUtils.get_bluetooth_adapter()
                return adapter.isEnabled() if adapter else False
            except: return False

        @staticmethod
        def set_bluetooth_enabled(enable):
            try:
                adapter = AndroidUtils.get_bluetooth_adapter()
                if not adapter: return
                if enable:
                    # Tentar habilitar sem pedir permissão (raramente funciona no Android novo)
                    if not adapter.enable():
                          # Fallback: Abrir configurações
                          AndroidUtils.open_settings_panel(Settings.ACTION_BLUETOOTH_SETTINGS)
                else:
                    adapter.disable()
            except Exception as e:
                 print(f"Erro BT: {e}")
                 AndroidUtils.open_settings_panel(Settings.ACTION_BLUETOOTH_SETTINGS)

        # --- UTILITÁRIOS GERAIS ---
        @staticmethod
        def open_settings_panel(panel_action):
            try:
                intent = Intent(panel_action)
                intent.addFlags(FLAG_ACTIVITY_NEW_TASK)
                AndroidUtils.get_activity().startActivity(intent)
            except Exception as e:
                AndroidUtils.toast("Erro ao abrir painel.")

else:
    # MOCK (Apenas para não quebrar no PC, mas o usuário usará no Android)
    class AndroidUtils:
        @staticmethod
        def set_brightness(v): print(f"[PC] Brilho: {v}")
        @staticmethod
        def set_volume(v): print(f"[PC] Volume: {v}")
        @staticmethod
        def get_volume(): return 50
        @staticmethod
        def toggle_torch(s): print(f"[PC] Lanterna: {s}")
        @staticmethod
        def toast(t): print(f"[PC] Toast: {t}")
        @staticmethod
        def is_wifi_enabled(): return True
        @staticmethod
        def set_wifi_enabled(e): print(f"[PC] Wifi: {e}")
        @staticmethod
        def get_current_ssid(): return "Rede_PC_Simulada"
        @staticmethod
        def get_scan_results(): return [{'ssid': 'Rede_Teste', 'quality': 90, 'level': -40}]
        @staticmethod
        def is_bluetooth_enabled(): return False
        @staticmethod
        def set_bluetooth_enabled(e): print(f"[PC] BT: {e}")
        @staticmethod
        def open_settings_panel(a): print(f"[PC] Config: {a}")
        @staticmethod
        def kill_background_process(p): print(f"[PC] Simulando Kill em {p}")
        @staticmethod
        def get_activity(): return None
        @staticmethod
        def get_package_manager(): return None

    # Placeholders para evitar erro de import
    class Settings:
        ACTION_WIFI_SETTINGS = "wifi"
        ACTION_BLUETOOTH_SETTINGS = "bt"
        ACTION_SETTINGS = "settings"
        ACTION_AIRPLANE_MODE_SETTINGS = "airplane"

# --- CONFIGURAÇÃO ---
# Define o tamanho apenas se não for Android (no Android a janela se adapta)
if platform != 'android':
    Window.size = (380, 740)

# Caminho de ícones: no Android lê do storage onde o instalador fez push,
# no PC continua usando a pasta assets/ local para desenvolvimento.
if platform == 'android':
    ICONS_ROOT = "/storage/emulated/0/SophiaOS/mobile_icons"
else:
    ICONS_ROOT = "assets/mobile_icons"
DEFAULT_PORT = 5005

CRITICAL_HOST_APPS = [
    "com.nu.production", "br.gov.meugovbr", "br.com.intermedium",
    "com.itau.personalite", "com.santander.app"
]

ICON_ALIASES = {
    "view-grid": ["view-app-grid", "apps"],
    "microsoft-edge": ["microsoft-edge", "web-browser"],
    "folder": ["system-file-manager", "folder"],
    "opera": ["opera-browser", "web-browser"],
    "cog-outline": ["preferences-system", "settings"],
    "console": ["utilities-terminal", "terminal"],
    "store": ["software-store", "software-center"],
    "shopping": ["system-software-install"],
    "calculator": ["accessories-calculator"],
    "pencil": ["accessories-text-editor"],
    "wifi": ["network-wireless"],
    "bluetooth": ["bluetooth-active"],
    "airplane": ["airplane-mode"],
    "flashlight": ["display-brightness"],
    "access-point": ["network-wireless-hotspot"],
    "screen-rotation": ["rotation-allowed"],
    "moon-waning-crescent": ["night-light"],
    "plus": ["list-add", "add"],
    "text": ["text-x-generic", "text-x-script"],
    "image": ["image-x-generic"],
    "video": ["video-x-generic"],
    "audio": ["audio-x-generic"],
    "pdf": ["application-pdf"],
    "text-html": ["text-html", "web-browser"],
    "app-native": ["system-run", "application-x-executable"],
    "app-encap": ["package-x-generic", "application-x-archive"],
    "multimedia-photo-viewer": ["multimedia-photo-viewer", "image-x-generic"],
    "notebook-edit": ["accessories-text-editor", "text-x-generic"],
    "unknown": ["unknown", "application-x-executable"],
    "magnify": ["system-search", "search"],
    "arrow-left": ["go-previous", "back"],
    "folder-plus": ["folder-new", "folder-add"],
    "file-plus-outline": ["document-new", "document-add"],
    "refresh": ["view-refresh", "reload"],
    "history": ["document-revert", "history"],
    "clock": ["preferences-system-time"],
    "monitor": ["computer", "system-file-manager"],
    "web": ["web-browser", "internet-web-browser"],
    "bell-ring-outline": ["notifications"],
    "weather-partly-cloudy": ["weather"]
}

# ============================================================================
# 📦 LÓGICA DO NÚCLEO (CONTAINER & APPICON)
# ============================================================================

class MicroAndroidContainer:
    @staticmethod
    def run(package_name):
        print(f"📦 [Micro-Android] Inicializando sandbox para: {package_name}")
        SofiaShell._launch_android_intent_raw(package_name)

class AppIcon(ABC):
    def __init__(self, path):
        self.path = path
        self.name = os.path.basename(path)
        self.icon = "app-encap"

    @abstractmethod
    def execute(self):
        pass

    @abstractmethod
    def get_display_name(self):
        pass

    @abstractmethod
    def get_display_icon(self):
        pass

    @staticmethod
    def factory(path):
        if os.path.isdir(path) and path.endswith(".appicon"):
            return UniversalDotAppIcon(path)
        elif path.endswith(".webicon"):
            return WebAppIcon(path)
        elif path.startswith("android:"):
            return AndroidHostAppIcon(path)
        else:
            return None

class UniversalDotAppIcon(AppIcon):
    def __init__(self, path):
        super().__init__(path)
        self.manifest = {}
        self._load_manifest()

    def _load_manifest(self):
        manifest_path = os.path.join(self.path, "app.manifest")
        try:
            if os.path.exists(manifest_path):
                with open(manifest_path, 'r') as f:
                    self.manifest = json.load(f)
        except Exception as e:
            print(f"⚠️ [Manifesto] Erro ao ler {self.name}: {e}")

    def get_display_name(self):
        # Tenta ler das chaves novas ou antigas
        return self.manifest.get("nome_exibicao") or \
               self.manifest.get("mobile", {}).get("nome_exibicao") or \
               self.name.replace(".appicon", "")

    def get_display_icon(self):
        icon_name = self.manifest.get("icon") or self.manifest.get("icon_name", "app-encap")
        # Procura ícone local na pasta do app
        for ext in [".png", ".svg", ".jpg"]:
            local_icon = os.path.join(self.path, f"{icon_name}{ext}")
            if os.path.exists(local_icon): return local_icon
        return icon_name

    def execute(self):
        print(f"🚀 [AppIcon] Executando: {self.name}")
        app = MDApp.get_running_app()

        # Leitura flexível do manifesto (suporta a versão antiga 'mobile' e a nova direta)
        tipo = self.manifest.get("tipo") or self.manifest.get("mobile", {}).get("mode")
        entry_point = self.manifest.get("entry_point") or self.manifest.get("mobile", {}).get("entry_point")
        app_id = self.manifest.get("id_semantico", self.name)

        # Rota para Apps Nativos Kivy (Mesa Notas, etc)
        if tipo == "mobile_kivy" or tipo == "kivy_native":
            if entry_point:
                app.launch_dynamic_widget(self.path, entry_point, app_id, self.manifest)
                return

        # Rota para Links Web
        elif tipo == "web_url":
            url = self.manifest.get("url") or self.manifest.get("mobile", {}).get("url")
            if url:
                webbrowser.open(url)
                return

        # Rota para Container Android
        android_pkg = self.manifest.get("android_package")
        if IS_ANDROID and android_pkg:
            SofiaShell.execute_android_package(android_pkg)
            return

        # Fallback
        SofiaShell.show_toast("Tipo de aplicativo desconhecido ou inválido.")

    def _run_script(self, path):
        os.system(f"python3 {path}")

class WebAppIcon(AppIcon):
    def execute(self):
        url = self._read_url()
        if url: webbrowser.open(url)

    def get_display_name(self):
        return self.name.replace(".webicon", "")

    def get_display_icon(self):
        return "text-html"

    def _read_url(self):
        try:
            with open(self.path, 'r') as f:
                for line in f:
                    if line.startswith("URL="): return line.split("=", 1)[1].strip()
        except: pass
        return None

class AndroidHostAppIcon(AppIcon):
    def __init__(self, path):
        super().__init__(path)
        self.package = path.split(":", 1)[1]

    def execute(self):
        SofiaShell.execute_android_package(self.package)

    def get_display_name(self):
        return self.package

    def get_display_icon(self):
        return "android"

# ============================================================================
# 🐚 SOFIA SHELL
# ============================================================================

class SofiaShell:
    @staticmethod
    def execute(path):
        app = MDApp.get_running_app()
        app.vibrate()
        app_icon = AppIcon.factory(path)

        if app_icon:
            print(f"✨ SofiaShell delegando abstração: {app_icon.get_display_name()}")
            app_icon.execute()
        elif os.path.isfile(path):
            UniversalViewer(path).open()
        else:
            app.navigate_to(path)

    @staticmethod
    def execute_android_package(package_name):
        app = MDApp.get_running_app()

        if package_name in CRITICAL_HOST_APPS:
            SofiaShell.show_toast("🔒 Modo Host Seguro Ativado")
            SofiaShell._launch_android_intent_raw(package_name)
            if app: app.register_android_task(package_name) # <- AVISA A SOPHIA
            return

        SofiaShell.show_toast(f"📦 Iniciando Container...\n{package_name}")
        MicroAndroidContainer.run(package_name)
        if app: app.register_android_task(package_name) # <- AVISA A SOPHIA

    @staticmethod
    def _launch_android_intent_raw(package):
        if IS_ANDROID:
            try:
                pm = AndroidUtils.get_package_manager()
                intent = pm.getLaunchIntentForPackage(package)
                if intent:
                    intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                    AndroidUtils.get_activity().startActivity(intent)
                    return True
            except Exception as e:
                print(f"Erro ao lançar Intent: {e}")
                SofiaShell.show_toast("Erro: App não instalado.")
            return False
        else:
            print(f"Simulação: Lançando {package}")
            return True

    @staticmethod
    def show_toast(text):
        if IS_ANDROID:
            AndroidUtils.toast(text)
        else:
            # Fallback para Desktop: Usa a nova Bubble Notification
            app = MDApp.get_running_app()
            if app:
                app.spawn_bubble(text, "information-outline")

# ============================================================================
# 📡 REDE VIGIA E UTILITÁRIOS (COM AUTHENTICAÇÃO)
# ============================================================================

class VigiaNetworkClient:
    def __init__(self, app_ref):
        self.app = app_ref
        self.sock = None
        self.connected = False
        self.ip = None

    def connect(self, ip, pin, port=DEFAULT_PORT):
        self.ip = ip
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5)
            self.sock.connect((ip, port))

            # --- HANDSHAKE DE AUTENTICAÇÃO ---
            print(f"🔐 Enviando PIN para {ip}...")
            auth_payload = json.dumps({"auth_pin": pin}).encode('utf-8')
            self.sock.sendall(auth_payload)

            # Espera resposta de confirmação (até 1KB é suficiente para status)
            resp = self.sock.recv(1024)
            if not resp:
                print("⛔ Servidor fechou conexão durante Auth.")
                self.sock.close()
                return False

            resp_data = json.loads(resp.decode('utf-8'))

            if resp_data.get("status") != "auth_ok":
                print("⛔ PIN Recusado pelo Gateway.")
                self.sock.close()
                return False
            # ---------------------------------

            self.sock.settimeout(None)
            self.connected = True
            print(f"✅ Conectado e Autenticado em {ip}:{port}")
            self.app.spawn_bubble("Vigia Conectado!", "lan-connect")
            threading.Thread(target=self.listen_loop, daemon=True).start()
            # Não precisa pedir list_desktop aqui, o gateway já manda no _send_initial_state após auth
            return True
        except Exception as e:
            print(f"❌ Falha na conexão/auth: {e}")
            self.connected = False
            return False

    def send_command(self, data):
        if not self.connected or not self.sock: return
        try:
            msg = json.dumps(data).encode('utf-8')
            self.sock.sendall(msg)
        except Exception as e:
            print(f"Erro no envio: {e}")
            self.connected = False
            Clock.schedule_once(lambda dt: self.app.on_connection_lost(), 0)

    def listen_loop(self):
        buffer = ""
        decoder = json.JSONDecoder()
        while self.connected:
            try:
                chunk = self.sock.recv(4096)
                if not chunk:
                    self.connected = False
                    break
                buffer += chunk.decode('utf-8')
                while buffer:
                    buffer = buffer.strip()
                    if not buffer: break
                    try:
                        obj, idx = decoder.raw_decode(buffer)
                        Clock.schedule_once(lambda dt, m=obj: self.process_message(m), 0)
                        buffer = buffer[idx:]
                    except ValueError:
                        break
            except Exception as e:
                print(f"Erro na escuta (Socket): {e}")
                self.connected = False
                break
        Clock.schedule_once(lambda dt: self.app.on_connection_lost(), 0)

    def process_message(self, msg):
        cmd = msg.get("type") or msg.get("command")
        if "files" in msg:
            self.app.update_remote_files(msg["files"])
        elif cmd == "batch_update" or cmd == "fs_event":
            self.send_command({"command": "list_desktop"})

class MetadataManager:
    @staticmethod
    def get_sidecar_path(file_path):
        directory = os.path.dirname(file_path)
        filename = os.path.basename(file_path)
        return os.path.join(directory, f".{filename}.json")
    @staticmethod
    def get_versions_dir(file_path):
        directory = os.path.dirname(file_path)
        return os.path.join(directory, ".versions")
    @staticmethod
    def get_attributes(file_path):
        json_path = MetadataManager.get_sidecar_path(file_path)
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r') as f: return json.load(f)
            except: return {}
        return {}
    @staticmethod
    def set_attribute(file_path, key, value):
        attrs = MetadataManager.get_attributes(file_path)
        attrs[key] = value
        json_path = MetadataManager.get_sidecar_path(file_path)
        try:
            with open(json_path, 'w') as f: json.dump(attrs, f)
        except Exception as e: print(f"Erro ao salvar: {e}")
    @staticmethod
    def save_version(file_path):
        if not os.path.exists(file_path) or os.path.isdir(file_path): return False
        versions_dir = MetadataManager.get_versions_dir(file_path)
        if not os.path.exists(versions_dir): os.makedirs(versions_dir)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = os.path.basename(file_path)
        backup_name = f"{timestamp}_{filename}"
        backup_path = os.path.join(versions_dir, backup_name)
        try:
            shutil.copy2(file_path, backup_path)
            return True
        except: return False
    @staticmethod
    def get_versions(file_path):
        versions_dir = MetadataManager.get_versions_dir(file_path)
        if not os.path.exists(versions_dir): return []
        filename = os.path.basename(file_path)
        versions = []
        for f in os.listdir(versions_dir):
            if f.endswith(filename) and f != filename:
                versions.append(os.path.join(versions_dir, f))
        versions.sort(reverse=True)
        return versions
    @staticmethod
    def restore_version(file_path, version_path):
        try:
            MetadataManager.save_version(file_path)
            shutil.copy2(version_path, file_path)
            return True
        except: return False

# ============================================================================
# 🖥️ INTERFACE E COMPONENTES UI (DIÁLOGOS E WIDGETS)
# ============================================================================

class WifiDialog(ModalView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (0.85, 0.7)
        self.background_color = (0, 0, 0, 0.6)
        self.auto_dismiss = True

        card = MDCard(orientation='vertical', radius=[20,], md_bg_color=(0.98, 0.98, 0.98, 1), padding=dp(0))
        header = MDCard(size_hint_y=None, height=dp(60), radius=[20, 20, 0, 0], md_bg_color=(0.9, 0.9, 0.9, 1), padding=dp(15), elevation=0)
        header.add_widget(MDIcon(icon="wifi", pos_hint={"center_y": .5}))
        header.add_widget(MDLabel(text="Redes Disponíveis", font_style="H6", bold=True, pos_hint={"center_y": .5}, padding_x=dp(10)))
        header.add_widget(MDIconButton(icon="close", pos_hint={"center_y": .5}, on_release=lambda x: self.dismiss()))
        card.add_widget(header)

        scroll = ScrollView()
        self.list_layout = BoxLayout(orientation='vertical', size_hint_y=None)
        self.list_layout.bind(minimum_height=self.list_layout.setter('height'))

        self.populate_networks()
        scroll.add_widget(self.list_layout)
        card.add_widget(scroll)

        action_bar = BoxLayout(size_hint_y=None, height=dp(50), padding=dp(5))
        scan_btn = MDRaisedButton(text="ESCANEAR NOVAMENTE", size_hint_x=1, on_release=lambda x: self.populate_networks())
        action_bar.add_widget(scan_btn)
        card.add_widget(action_bar)

        self.add_widget(card)

    def populate_networks(self):
        self.list_layout.clear_widgets()
        # Chama a HAL Nativa
        networks = AndroidUtils.get_scan_results()

        if not networks:
             self.list_layout.add_widget(MDLabel(text="Nenhuma rede encontrada.\nVerifique GPS/Permissões.", halign="center", size_hint_y=None, height=dp(100)))
             return

        for net in networks:
            ssid = net['ssid']
            quality = net['quality']
            icon_sig = "wifi-strength-4"
            if quality < 30: icon_sig = "wifi-strength-1"
            elif quality < 60: icon_sig = "wifi-strength-2"
            elif quality < 80: icon_sig = "wifi-strength-3"

            item = TwoLineAvatarIconListItem(
                text=ssid,
                secondary_text=f"Sinal: {quality}% ({net['level']} dBm)",
                on_release=lambda x, s=ssid: self.select_network(s)
            )
            item.add_widget(MDIconButton(icon=icon_sig))
            self.list_layout.add_widget(item)

    def select_network(self, ssid):
        SofiaShell.show_toast(f"Selecionado: {ssid}. Conecte via Sistema.")
        AndroidUtils.open_settings_panel(Settings.ACTION_WIFI_SETTINGS)
        self.dismiss()

class WallpaperPicker(ModalView):
    def __init__(self, callback, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (0.9, 0.8)
        self.background_color = (0, 0, 0, 0.85) # Fundo escuro (Dark Mode)
        self.auto_dismiss = True
        self.callback = callback

        # Layout Principal
        card = MDCard(orientation='vertical', radius=[16,], md_bg_color=(0.12, 0.12, 0.12, 1), padding=dp(0))

        # Cabeçalho
        header = BoxLayout(size_hint_y=None, height=dp(56), padding=dp(15))
        lbl = MDLabel(text="Mudar Visual", theme_text_color="Custom", text_color=(1,1,1,1), font_style="H6", bold=True)
        close_btn = MDIconButton(icon="close", theme_text_color="Custom", text_color=(1,0.3,0.3,1), on_release=self.dismiss)
        header.add_widget(lbl)
        header.add_widget(close_btn)
        card.add_widget(header)

        # Área de Rolagem com Grid
        scroll = ScrollView()
        self.grid = MDGridLayout(cols=3, adaptive_height=True, padding=dp(10), spacing=dp(10))

        # Carrega imagens da pasta assets (Padrão)
        self.load_images("assets")

        scroll.add_widget(self.grid)
        card.add_widget(scroll)
        self.add_widget(card)

    def load_images(self, folder):
        valid_exts = [".jpg", ".jpeg", ".png", ".webp"]
        if not os.path.exists(folder): return

        for f in sorted(os.listdir(folder)):
            if any(f.lower().endswith(ext) for ext in valid_exts):
                full_path = os.path.join(folder, f)

                # Card da miniatura
                # Usando MDCard com ripple=True para substituir o ButtonBehavior cru (mais estável)
                img_card = MDCard(size_hint=(None, None), size=(dp(90), dp(160)), ripple_behavior=True)
                img_widget = Image(source=full_path, allow_stretch=True, keep_ratio=False, size_hint=(1,1))
                img_card.add_widget(img_widget)

                # O Pulo do Gato: Bind com lambda pra passar o caminho certo
                img_card.bind(on_release=lambda x, p=full_path: self.select_image(p))

                self.grid.add_widget(img_card)

    def select_image(self, path):
        # Toca uma vibraçãozinha pra dar gosto
        MDApp.get_running_app().vibrate()
        self.callback(path)
        self.dismiss()

class SmartIcon(ButtonBehavior, FloatLayout):
    icon_name = StringProperty("")
    source_path = StringProperty("")
    icon_size = NumericProperty(dp(48))

    def on_icon_name(self, instance, value):
        if not value:
            self.source_path = ""
            return

        if os.path.exists(value):
            self.source_path = value
            return

        targets = [value]
        if value in ICON_ALIASES: targets.extend(ICON_ALIASES[value])
        if value not in targets: targets.append(value)

        if not os.path.exists(ICONS_ROOT):
             self.source_path = ""
             return

        app_instance = MDApp.get_running_app()
        current_theme_style = app_instance.theme_cls.theme_style if app_instance else "Light"
        theme_folder = "Colloid-Light" if current_theme_style == "Light" else "Colloid-Dark"
        SYMBOLIC_PATH = os.path.join(ICONS_ROOT, theme_folder, "status", "symbolic")

        for t in targets:
            icon_file = f"{t}-symbolic.png"
            full_symbolic = os.path.join(SYMBOLIC_PATH, icon_file)
            if os.path.exists(full_symbolic):
                self.source_path = full_symbolic
                return
            icon_file_pure = f"{t}.png"
            full_pure = os.path.join(SYMBOLIC_PATH, icon_file_pure)
            if os.path.exists(full_pure):
                self.source_path = full_pure
                return

        for root, dirs, files in os.walk(ICONS_ROOT):
            for t in targets:
                if f"{t}.png" in files:
                    full = os.path.join(root, f"{t}.png")
                    self.source_path = full
                    return
        self.source_path = ""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.image = Image(
            source=self.source_path,
            size_hint=(None, None), size=(self.icon_size, self.icon_size),
            pos_hint={"center_x": .5, "center_y": .5},
            allow_stretch=True, keep_ratio=True, mipmap=True
        )
        self.bind(icon_size=self._update_image_size, source_path=self._update_image_source)
        self.add_widget(self.image)

    def _update_image_size(self, instance, value): self.image.size = (value, value)
    def _update_image_source(self, instance, value): self.image.source = value

class DockIcon(SmartIcon):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.icon_size = dp(36)
        self.size_hint = (None, None)
        self.size = (dp(44), dp(44))
        self.pos_hint = {"center_y": .5}

class AppGridIcon(SmartIcon):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.icon_size = dp(48)
        self.size_hint = (None, None)
        self.size = (dp(64), dp(64))

class HistoryDialog(ModalView):
    def __init__(self, file_path, callback_refresh, **kwargs):
        super().__init__(**kwargs)
        self.file_path = file_path
        self.callback_refresh = callback_refresh
        self.size_hint = (0.85, None)
        self.height = dp(450)
        self.background_color = (0, 0, 0, 0.6)
        self.auto_dismiss = True
        card = MDCard(orientation='vertical', radius=[20,], md_bg_color=(0.98, 0.98, 0.98, 1), padding=dp(20), spacing=dp(10))
        card.add_widget(MDLabel(text="Histórico de Versões", halign="center", font_style="H6", bold=True, size_hint_y=None, height=dp(40)))
        scroll = ScrollView(size_hint=(1, 1))
        self.list_layout = BoxLayout(orientation='vertical', size_hint_y=None)
        self.list_layout.bind(minimum_height=self.list_layout.setter('height'))
        versions = MetadataManager.get_versions(file_path)
        if not versions: self.list_layout.add_widget(MDLabel(text="Nenhuma versão salva.", halign="center", theme_text_color="Hint"))
        else:
            for v_path in versions:
                fname = os.path.basename(v_path)
                try:
                    parts = fname.split('_', 2)
                    date_str = f"{parts[0]} {parts[1].replace('-', ':')}"
                except: date_str = fname
                item = OneLineAvatarIconListItem(text=date_str, on_release=lambda x, p=v_path: self.confirm_restore(p))
                item.add_widget(MDIconButton(icon="backup-restore", pos_hint={"center_x": .9, "center_y": .5}))
                self.list_layout.add_widget(item)
        scroll.add_widget(self.list_layout)
        card.add_widget(MDIconButton(icon="close", on_release=self.dismiss, pos_hint={'center_x': .5}))
        self.add_widget(card)
    def confirm_restore(self, version_path):
        if MetadataManager.restore_version(self.file_path, version_path):
            self.callback_refresh()
            self.dismiss()

class PropertiesDialog(ModalView):
    def __init__(self, file_path, callback_refresh, **kwargs):
        super().__init__(**kwargs)
        self.file_path = file_path
        self.callback_refresh = callback_refresh
        self.size_hint = (0.85, None)
        self.height = dp(500)
        self.background_color = (0, 0, 0, 0.6)
        self.auto_dismiss = False
        self.attrs = MetadataManager.get_attributes(file_path)
        card = MDCard(orientation='vertical', radius=[20,], md_bg_color=(0.98, 0.98, 0.98, 1), padding=dp(20), spacing=dp(10))
        card.add_widget(MDLabel(text="Propriedades Semânticas", halign="center", font_style="H6", bold=True, size_hint_y=None, height=dp(40)))
        card.add_widget(MDLabel(text=f"Arquivo: {os.path.basename(file_path)}", theme_text_color="Secondary", font_style="Caption", size_hint_y=None, height=dp(20)))
        card.add_widget(MDLabel(text="Estado (Papel):", font_style="Caption", size_hint_y=None, height=dp(20)))
        self.state_scroll = ScrollView(size_hint_y=None, height=dp(50))
        self.state_box = BoxLayout(size_hint_x=None, spacing=dp(5))
        self.state_box.bind(minimum_width=self.state_box.setter('width'))
        states = [("neutro", "Neutro"), ("materia_prima", "Matéria-Prima"), ("referencia", "Em Andamento"), ("finalizado", "Finalizado")]
        current_state = self.attrs.get("state", "neutro")
        self.state_btns = []
        for s_key, s_label in states:
            btn = MDFlatButton(text=s_label, theme_text_color="Custom", text_color=(1,1,1,1) if s_key == current_state else (0.5,0.5,0.5,1), md_bg_color=(0.2, 0.6, 1, 1) if s_key == current_state else (0.9,0.9,0.9,1))
            btn.bind(on_release=lambda x, k=s_key: self.set_state(k))
            self.state_box.add_widget(btn)
            self.state_btns.append((btn, s_key))
        self.state_scroll.add_widget(self.state_box)
        card.add_widget(self.state_scroll)
        self.selected_state = current_state
        self.tags_field = MDTextField(text=", ".join(self.attrs.get("tags", [])), hint_text="Tags", mode="rectangle")
        card.add_widget(self.tags_field)
        self.desc_field = MDTextField(text=self.attrs.get("description", ""), hint_text="Descrição", mode="rectangle", multiline=True, size_hint_y=None, height=dp(80))
        card.add_widget(self.desc_field)
        self.url_field = MDTextField(text=self.attrs.get("origin_url", ""), hint_text="URL de Origem", mode="rectangle")
        card.add_widget(self.url_field)
        buttons_box = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
        buttons_box.add_widget(Widget())
        cancel_btn = MDIconButton(icon="close", on_release=self.dismiss)
        save_btn = MDIconButton(icon="content-save", theme_text_color="Custom", text_color=(0, 0.5, 1, 1), on_release=self.save_properties)
        buttons_box.add_widget(cancel_btn)
        buttons_box.add_widget(save_btn)
        card.add_widget(Widget(size_hint_y=1))
        card.add_widget(buttons_box)
        self.add_widget(card)
    def set_state(self, key):
        self.selected_state = key
        for btn, k in self.state_btns:
            if k == key:
                btn.md_bg_color = (0.2, 0.6, 1, 1); btn.text_color = (1, 1, 1, 1)
            else:
                btn.md_bg_color = (0.9, 0.9, 0.9, 1); btn.text_color = (0.5, 0.5, 0.5, 1)
    def save_properties(self, *args):
        raw_tags = self.tags_field.text
        tags_list = [t.strip() for t in raw_tags.split(',') if t.strip()]
        MetadataManager.set_attribute(self.file_path, "tags", tags_list)
        MetadataManager.set_attribute(self.file_path, "description", self.desc_field.text)
        MetadataManager.set_attribute(self.file_path, "origin_url", self.url_field.text)
        MetadataManager.set_attribute(self.file_path, "state", self.selected_state)
        self.callback_refresh()
        self.dismiss()

class ContextMenu(ModalView):
    file_path = StringProperty("")
    def __init__(self, file_path, callback_refresh, **kwargs):
        super().__init__(**kwargs)
        self.file_path = file_path
        self.callback_refresh = callback_refresh
        self.size_hint = (None, None)
        self.width = dp(220)
        self.height = dp(340)
        self.background_color = (0, 0, 0, 0)
        self.auto_dismiss = True
        card = MDCard(orientation='vertical', radius=[16,], md_bg_color=(0.95, 0.95, 0.95, 0.95), padding=dp(10), spacing=dp(5))
        card.add_widget(MDLabel(text=os.path.basename(file_path), halign="center", font_style="Subtitle2", size_hint_y=None, height=dp(30), theme_text_color="Custom", text_color=(0.3, 0.3, 0.3, 1)))
        card.add_widget(self._build_btn("folder-open", "Abrir", self.action_open))
        card.add_widget(self._build_btn("pencil", "Renomear", self.action_rename))
        card.add_widget(self._build_btn("information-outline", "Propriedades", self.action_properties))
        if not os.path.isdir(file_path): card.add_widget(self._build_btn("history", "Histórico / Salvar", self.action_history))
        card.add_widget(MDLabel(text="Status:", font_style="Caption", size_hint_y=None, height=dp(20)))
        status_box = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(5))
        status_box.add_widget(self._build_color_btn((0.2, 0.8, 0.2, 1), "aprovado"))
        status_box.add_widget(self._build_color_btn((1, 0.8, 0, 1), "revisao"))
        status_box.add_widget(self._build_color_btn((1, 0.3, 0.3, 1), "pendente"))
        status_box.add_widget(self._build_color_btn((0.8, 0.8, 0.8, 1), None))
        card.add_widget(status_box)
        card.add_widget(Widget(size_hint_y=1))
        card.add_widget(self._build_btn("trash", "Excluir", self.action_delete, color=(0.8, 0.2, 0.2, 1)))
        self.add_widget(card)
    def _build_btn(self, icon, text, callback, color=(0.2, 0.2, 0.2, 1)):
        btn = MDIconButton(icon=icon, theme_text_color="Custom", text_color=color, on_release=callback)
        box = BoxLayout(size_hint_y=None, height=dp(40))
        box.add_widget(btn); box.add_widget(MDLabel(text=text, theme_text_color="Custom", text_color=color))
        return box
    def _build_color_btn(self, color, status_key):
        card = MDCard(md_bg_color=color, radius=[10,], ripple_behavior=True)
        card.bind(on_release=lambda x: self.action_set_status(status_key))
        container = BoxLayout(size_hint=(1, 1))
        container.add_widget(card)
        return container
    def action_open(self, *args):
        self.dismiss()
        SofiaShell.execute(self.file_path)
    def action_rename(self, *args): self.dismiss()
    def action_history(self, *args):
        self.dismiss(); MetadataManager.save_version(self.file_path)
        HistoryDialog(self.file_path, self.callback_refresh).open()
    def action_delete(self, *args):
        try:
            if os.path.isdir(self.file_path): shutil.rmtree(self.file_path)
            else: os.remove(self.file_path)
            sidecar = MetadataManager.get_sidecar_path(self.file_path)
            if os.path.exists(sidecar): os.remove(sidecar)
            v_dir = MetadataManager.get_versions_dir(self.file_path)
            if os.path.exists(v_dir): shutil.rmtree(v_dir)
            self.callback_refresh(); self.dismiss()
        except: pass
    def action_set_status(self, status):
        MetadataManager.set_attribute(self.file_path, "status", status)
        self.callback_refresh(); self.dismiss()
    def action_properties(self, *args):
        self.dismiss(); PropertiesDialog(self.file_path, self.callback_refresh).open()

class UniversalViewer(ModalView):
    def __init__(self, file_path, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (0.9, 0.85)
        self.background_color = (0, 0, 0, 0.5)
        self.auto_dismiss = True
        card = MDCard(orientation='vertical', radius=[20,], md_bg_color=(0.98, 0.98, 0.98, 0.95), padding=dp(0), elevation=4)
        header = MDFloatLayout(size_hint_y=None, height=dp(50), md_bg_color=(0.9, 0.9, 0.9, 1))
        close_btn = MDIconButton(icon="close", pos_hint={"center_y": .5, "right": 0.98}, theme_text_color="Custom", text_color=(0.8, 0.2, 0.2, 1), on_release=lambda x: self.dismiss())
        title = MDLabel(text=os.path.basename(file_path), halign="center", pos_hint={"center_y": .5}, font_style="Subtitle1", bold=True)
        header.add_widget(title); header.add_widget(close_btn)
        card.add_widget(header)
        content_area = BoxLayout(padding=dp(10))
        mime_type, _ = mimetypes.guess_type(file_path)

        if file_path.endswith(".webicon"):
             url = self.read_key_val(file_path, "URL")
             content_area.orientation = 'vertical'
             content_area.add_widget(MDIcon(icon="web", halign="center", font_size="64sp", size_hint_y=None, height=dp(100)))
             content_area.add_widget(MDLabel(text=f"Link Web:\n{url}", halign="center"))
             content_area.add_widget(MDFlatButton(text="ABRIR NO NAVEGADOR", pos_hint={'center_x': .5}))
             content_area.add_widget(Widget())

        elif mime_type and mime_type.startswith('image'):
            img = Image(source=file_path, allow_stretch=True, keep_ratio=True)
            content_area.add_widget(img)

        elif mime_type and (mime_type.startswith('text') or file_path.endswith(('.py', '.json', '.md', '.txt'))):
            try:
                with open(file_path, 'r', encoding='utf-8') as f: content = f.read()
                self.text_editor = MDTextFieldRect(text=content, size_hint=(1, 1), multiline=True, background_normal='', background_color=(1, 1, 1, 0))
                content_area.add_widget(self.text_editor)
                save_btn = MDIconButton(icon="content-save", pos_hint={"center_y": .5, "x": 0.02}, theme_text_color="Custom", text_color=(0.2, 0.6, 0.2, 1), on_release=lambda x: self.save_file(file_path, self.text_editor.text))
                header.add_widget(save_btn)
            except Exception as e: content_area.add_widget(MDLabel(text=f"Erro: {e}", halign="center"))

        else:
            icon = MDIconButton(icon="file-question", icon_size=dp(64), pos_hint={"center_x": .5, "center_y": .5})
            lbl = MDLabel(text="Formato não suportado.", halign="center")
            box = BoxLayout(orientation='vertical')
            box.add_widget(Widget()); box.add_widget(icon); box.add_widget(lbl); box.add_widget(Widget())
            content_area.add_widget(box)

        card.add_widget(content_area)
        self.add_widget(card)

    def read_key_val(self, path, key):
        try:
            with open(path, 'r') as f:
                for line in f:
                    if line.startswith(f"{key}="): return line.split("=", 1)[1].strip()
        except: return "Inválido"
        return "N/A"

    def save_file(self, path, content):
        try:
            MetadataManager.save_version(path)
            with open(path, 'w', encoding='utf-8') as f: f.write(content)
            self.dismiss()
        except: pass

# ============================================================================
# 🔔 CARDS DE NOTIFICAÇÃO E RSS
# ============================================================================

class NotificationCard(MDCard):
    def __init__(self, title, text, icon_name="bell-outline", **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = dp(75)
        self.radius = [18,]
        self.md_bg_color = (1, 1, 1, 0.15) # Translúcido estilo Glass
        self.padding = dp(12)
        self.spacing = dp(15)
        self.ripple_behavior = True

        # Ícone à esquerda
        self.add_widget(MDIcon(
            icon=icon_name,
            theme_text_color="Custom",
            text_color=(1,1,1,1),
            pos_hint={"center_y": .5},
            font_size="28sp"
        ))

        # Textos (Título e Descrição)
        text_box = BoxLayout(orientation='vertical', pos_hint={"center_y": .5})
        text_box.add_widget(MDLabel(
            text=title, font_style="Subtitle2", bold=True,
            theme_text_color="Custom", text_color=(1,1,1,1), shorten=True
        ))
        text_box.add_widget(MDLabel(
            text=text, font_style="Caption",
            theme_text_color="Custom", text_color=(0.9,0.9,0.9,1), shorten=True
        ))
        self.add_widget(text_box)

        # Botão de Fechar à direita
        close_btn = MDIconButton(
            icon="close",
            theme_text_color="Custom",
            text_color=(1,1,1,0.6),
            pos_hint={"center_y": .5}
        )
        close_btn.bind(on_release=self.dismiss)
        self.add_widget(close_btn)

    def dismiss(self, *args):
        # Animação de encolher e sumir (efeito mola)
        anim = Animation(opacity=0, height=0, d=0.3, t='out_quad')
        anim.bind(on_complete=lambda *x: self.parent.remove_widget(self) if self.parent else None)
        anim.start(self)

class RSSFeedCard(MDCard):
    def __init__(self, title, source_name, link, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = dp(85)
        self.radius = [18,]
        self.md_bg_color = (0.1, 0.5, 0.8, 0.15) # Um tom levemente azulado para diferenciar
        self.padding = dp(12)
        self.spacing = dp(15)
        self.ripple_behavior = True
        self.link = link

        # Ícone de RSS/Jornal
        self.add_widget(MDIcon(
            icon="newspaper-variant-outline",
            theme_text_color="Custom",
            text_color=(0.5, 0.8, 1, 1),
            pos_hint={"center_y": .5},
            font_size="28sp"
        ))

        # Textos
        text_box = BoxLayout(orientation='vertical', pos_hint={"center_y": .5})
        text_box.add_widget(MDLabel(
            text=source_name.upper(), font_style="Overline", bold=True,
            theme_text_color="Custom", text_color=(0.5, 0.8, 1, 1), shorten=True
        ))
        text_box.add_widget(MDLabel(
            text=title, font_style="Caption", bold=True,
            theme_text_color="Custom", text_color=(1,1,1,1), shorten=True, max_lines=2
        ))
        self.add_widget(text_box)

    def on_release(self):
        # Quando clica no card, abre a notícia e depois some com ele do feed
        webbrowser.open(self.link)
        self.dismiss()

    def dismiss(self, *args):
        anim = Animation(opacity=0, height=0, d=0.3, t='out_quad')
        anim.bind(on_complete=lambda *x: self.parent.remove_widget(self) if self.parent else None)
        anim.start(self)

class AppletShelfCard(ButtonBehavior, BoxLayout):
    applet_data = DictProperty({})

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.size_hint = (None, None)
        self.size = (dp(80), dp(100))
        self.padding = dp(8)

        with self.canvas.before:
            Color(1, 1, 1, 0.1)
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[16])

        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    # O clique simples que você pediu!
    def on_release(self):
        app = MDApp.get_running_app()
        app.vibrate()
        app.open_applet_shelf_menu(self)

class DesktopApplet(BoxLayout):
    icon_name = StringProperty("application-cog")
    label_text = StringProperty("Applet")
    applet_data = DictProperty({})

    def __init__(self, applet_data, **kwargs):
        super().__init__(**kwargs)
        self.applet_data = applet_data
        self.orientation = 'vertical'
        self.size_hint = (None, None)
        self.size = (dp(85), dp(100))
        self.padding = dp(5)
        self.spacing = dp(2)

        self.icon_widget = SmartIcon(icon_name=self.icon_name, icon_size=dp(48))
        self.icon_widget.pos_hint = {'center_x': 0.5}

        from kivy.uix.label import Label
        self.label_widget = Label(
            text=self.label_text, halign='center', valign='top',
            font_size='12sp', color=(0.2, 0.2, 0.2, 1),
            size_hint_y=None, height=dp(40),
            text_size=(dp(80), None), shorten=True, shorten_from='right'
        )
        self.add_widget(self.icon_widget)
        self.add_widget(self.label_widget)

# ============================================================================
# 🖱️ DESKTOP ITEM COM DRAG & DROP (FÍSICA + INTEGRAÇÃO VIGIA + GRAB FIX)
# ============================================================================
class DesktopItem(ButtonBehavior, BoxLayout):
    icon_name = StringProperty("unknown")
    label_text = StringProperty("Arquivo")
    file_path = StringProperty("")
    status_color = ListProperty([0, 0, 0, 0])
    flash_color = ListProperty([0, 0, 0, 0])
    is_remote = BooleanProperty(False)

    # Variáveis internas de controle do Drag
    _touch_start_pos = None
    _is_dragging = False
    _drag_avatar = None
    _long_press_timer = None

    def __init__(self, refresh_callback=None, **kwargs):
        super().__init__(**kwargs)
        self.refresh_callback = refresh_callback
        self.orientation = 'vertical'
        self.size_hint = (None, None)
        self.size = (dp(85), dp(100))
        self.padding = dp(5)
        self.spacing = dp(2)

        with self.canvas.before:
            self.flash_instruction = Color(rgba=self.flash_color)
            self.flash_rect = Rectangle(pos=self.pos, size=self.size)

        self.bind(pos=self._update_rect, size=self._update_rect, flash_color=self._update_color)

        # Construção Visual
        self.icon_widget = SmartIcon(icon_name=self.icon_name, icon_size=dp(48))
        self.icon_widget.pos_hint = {'center_x': 0.5}

        from kivy.uix.label import Label
        self.label_widget = Label(
            text=self.label_text, halign='center', valign='top',
            font_size='12sp', color=(0.2, 0.2, 0.2, 1),
            outline_color=(1, 1, 1, 0.8), outline_width=0,
            size_hint_y=None, height=dp(40),
            text_size=(dp(80), None), shorten=True, shorten_from='right'
        )
        self.add_widget(self.icon_widget)
        self.add_widget(self.label_widget)
        self.bind(icon_name=self._update_icon, label_text=self._update_label)
        self.update_status_visual()
        self.check_if_new()

    def _update_rect(self, *args): self.flash_rect.pos = self.pos; self.flash_rect.size = self.size
    def _update_color(self, *args): self.flash_instruction.rgba = self.flash_color
    def _update_icon(self, instance, value): self.icon_widget.icon_name = value
    def _update_label(self, instance, value): self.label_widget.text = value

    # --- LÓGICA DE TOQUE E ARRASTO (DRAG & DROP COM GRAB) ---

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            # O GRAB É CRUCIAL: Impede o ScrollView de roubar o evento
            touch.grab(self)

            # 1. Avisa o Pai (Mesa) para não abrir o menu de fundo
            parent = self.parent
            while parent:
                if isinstance(parent, ActiveDesktopBackground):
                    parent.cancel_timer()
                    break
                parent = parent.parent

            # 2. Prepara o terreno
            self._touch_start_pos = touch.pos
            self._is_dragging = False
            self._drag_avatar = None

            # 3. Inicia timer de clique longo (Menu de Contexto)
            if not self.is_remote:
                self._long_press_timer = Clock.schedule_once(self._do_long_press, 0.6)

            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        # Verifica se o toque é nosso via grab
        if touch.grab_current is self:
            if self._touch_start_pos:
                # Calcula distância percorrida
                dx = abs(touch.x - self._touch_start_pos[0])
                dy = abs(touch.y - self._touch_start_pos[1])

                # Se moveu mais que 15dp, assume que é ARRASTO, não clique
                if (dx > dp(15) or dy > dp(15)) and not self._is_dragging:
                    self._start_drag(touch)

                # Se já está arrastando, atualiza a posição do fantasma
                if self._is_dragging and self._drag_avatar:
                    win_x, win_y = self.parent.to_window(touch.x, touch.y)
                    self._drag_avatar.center = (win_x, win_y)

            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        # Libera o toque apenas se for nosso
        if touch.grab_current is self:
            touch.ungrab(self)

            # Limpa o timer de clique longo se soltou rápido
            if self._long_press_timer:
                self._long_press_timer.cancel()
                self._long_press_timer = None

            # --- LÓGICA DO DROP (SOLTAR) ---
            if self._is_dragging:
                app = MDApp.get_running_app()
                desktop_grid = app.root.ids.desktop_grid
                dropped_on_applet = False

                # 1. Verifica se soltou em cima de algum DesktopApplet (Para Executar)
                for widget in desktop_grid.children:
                    if isinstance(widget, DesktopApplet):
                        if widget.collide_point(touch.x, touch.y):
                            self._trigger_applet_action(widget.applet_data)
                            dropped_on_applet = True
                            break

                # 2. Se NÃO for applet, tenta MUDAR DE LUGAR na mesa
                if not dropped_on_applet:
                    alvo_reposicionamento = None
                    for widget in desktop_grid.children:
                        # Ignora a si mesmo e os applets
                        if widget is not self and not isinstance(widget, DesktopApplet):
                            if widget.collide_point(touch.x, touch.y):
                                alvo_reposicionamento = widget
                                break

                    if alvo_reposicionamento:
                        # A Mágica: Troca o arquivo de posição na grade do Kivy
                        index_alvo = desktop_grid.children.index(alvo_reposicionamento)
                        desktop_grid.remove_widget(self)
                        desktop_grid.add_widget(self, index=index_alvo)

                        # Limpa o fantasma sem fazer bumerangue (já achou a casa nova)
                        if self._drag_avatar:
                            app.root.remove_widget(self._drag_avatar)
                        self._drag_avatar = None
                        self.opacity = 1.0
                        self._is_dragging = False
                        self._touch_start_pos = None
                        self.vibrate_light()
                        return True

                # 3. Animação de Sucesso no Applet ou Bumerangue se soltou no vazio
                if dropped_on_applet:
                    if self._drag_avatar:
                        app.root.remove_widget(self._drag_avatar)
                    self._drag_avatar = None
                    self.opacity = 1.0
                else:
                    # Desistência: O Efeito Bumerangue!
                    if self._drag_avatar:
                        orig_x, orig_y = self.to_window(self.x, self.y)
                        anim_return = Animation(pos=(orig_x, orig_y), d=0.4, t='out_back')

                        def clear_ghost(*args):
                            if self._drag_avatar and self._drag_avatar.parent:
                                app.root.remove_widget(self._drag_avatar)
                            self._drag_avatar = None
                            self.opacity = 1.0

                        anim_return.bind(on_complete=clear_ghost)
                        anim_return.start(self._drag_avatar)
                    else:
                        self.opacity = 1.0

                self._is_dragging = False
                self._touch_start_pos = None
                return True

            # Se não estava arrastando, foi um clique normal para abrir o arquivo
            if self.collide_point(*touch.pos):
                if not self._is_dragging:
                    self.on_release_action()

            self._touch_start_pos = None
            return True
        return super().on_touch_up(touch)

    # --- MÉTODOS AUXILIARES DO DRAG ---

    def _start_drag(self, touch):
        """Inicializa o modo de arrasto e cria o avatar visual"""
        self._is_dragging = True

        # Cancela o menu de contexto, pois virou arrasto
        if self._long_press_timer:
            self._long_press_timer.cancel()
            self._long_press_timer = None

        self.vibrate_light()

        from kivymd.uix.card import MDCard
        from kivymd.uix.label import MDIcon

        app = MDApp.get_running_app()
        # Cria o fantasma
        self._drag_avatar = MDCard(
            size_hint=(None, None), size=self.size,
            md_bg_color=(1, 1, 1, 0.3), radius=[16,], elevation=4
        )
        icon = MDIcon(icon=self.icon_name, font_size="48sp", pos_hint={"center_x": .5, "center_y": .6})
        lbl = MDLabel(text=self.label_text, halign="center", font_style="Caption", pos_hint={"center_x": .5, "y": 0.1}, theme_text_color="Custom", text_color=(1,1,1,1))

        self._drag_avatar.add_widget(icon)
        self._drag_avatar.add_widget(lbl)

        # Adiciona na raiz (acima de tudo)
        app.root.add_widget(self._drag_avatar)
        self.opacity = 0.4

        # Posiciona imediatamente onde está o dedo
        win_x, win_y = self.parent.to_window(touch.x, touch.y)
        self._drag_avatar.center = (win_x, win_y)

    def _trigger_applet_action(self, applet_data):
        """O Cérebro Mágico: Decide o comando e onde executar (Local vs Vigia)"""
        app = MDApp.get_running_app()

        # 1. Identifica MIME Type
        mime_type, _ = mimetypes.guess_type(self.file_path)
        if not mime_type: mime_type = "application/octet-stream"

        print(f"🧩 Drop detectado! Arquivo: {self.file_path} ({mime_type}) -> Applet: {applet_data.get('name')}")

        target_action = None

        # 2. Busca Trigger Específico (Drop Triggers)
        # Ex: "image/png": "converter_png"
        drop_triggers = applet_data.get("drop_triggers", {})
        trigger_id = drop_triggers.get(mime_type)

        # Tenta wildcard (ex: image/*)
        if not trigger_id:
            for key, val in drop_triggers.items():
                if key.endswith("/*") and mime_type.startswith(key[:-2]):
                    trigger_id = val
                    break

        if trigger_id:
            # Acha a ação correspondente ao ID
            target_action = next((a for a in applet_data.get("actions", []) if a.get("id") == trigger_id), None)

        # 3. Fallback: Busca a primeira ação compatível na lista de ações
        if not target_action:
            for action in applet_data.get("actions", []):
                triggers = action.get("triggers", {})
                accepted_mimes = triggers.get("mimetype", [])
                if any(m == "*" or m == mime_type or (m.endswith("/*") and mime_type.startswith(m[:-2])) for m in accepted_mimes):
                    target_action = action
                    break

        if not target_action:
            app.spawn_bubble("Este applet não aceita este arquivo.", "file-cancel")
            return

        # 4. Monta o Comando
        cmd_template = target_action.get("command", "")
        if not cmd_template:
            app.spawn_bubble("Applet sem comando definido.", "alert")
            return

        # Escapa o caminho do arquivo para evitar injeção/erros de espaço
        safe_path = shlex.quote(self.file_path)
        real_cmd = cmd_template.replace("%F", safe_path).replace("%f", safe_path)

        app.spawn_bubble(f"Executando: {applet_data.get('name')}", "rocket-launch")

        # 5. DECISÃO HÍBRIDA: PC (Vigia) ou Celular (Local)?
        # Comandos pesados vão para o PC se estiver conectado
        heavy_keywords = ["ffmpeg", "convert", "7z", "tar", "make", "docker", "gimp"]
        is_heavy = any(k in real_cmd for k in heavy_keywords)

        if app.is_connected and is_heavy:
            # Manda pro Vigia
            app.spawn_bubble("Enviando processamento para o PC...", "monitor-share")
            app.network.send_command({
                "command": "remote_exec_raw",
                "shell_command": real_cmd,
                "origin_file": self.file_path
            })
        else:
            # Executa no Android (Termux environment ou shell simples)
            print(f"⚙️ Executando localmente: {real_cmd}")
            threading.Thread(target=lambda: os.system(real_cmd)).start()

    # --- UTILITÁRIOS ---

    def vibrate_light(self):
        if platform == 'android':
            try:
                from jnius import autoclass
                Context = autoclass('android.content.Context')
                activity = autoclass('org.kivy.android.PythonActivity').mActivity
                vibrator = activity.getSystemService(Context.VIBRATOR_SERVICE)
                vibrator.vibrate(25)
            except: pass

    def check_if_new(self):
        if self.is_remote: return
        try:
            mtime = os.path.getmtime(self.file_path)
            if (time.time() - mtime) < 3.0: self.trigger_flash()
        except: pass

    def trigger_flash(self):
        self.flash_color = [1, 1, 0, 0.6]
        anim = Animation(flash_color=[1, 1, 0, 0], duration=1.5, t='out_cubic')
        anim.start(self)

    def update_status_visual(self):
        if self.is_remote: return
        attrs = MetadataManager.get_attributes(self.file_path)
        status = attrs.get("status")
        if status == "aprovado": self.status_color = [0.2, 0.8, 0.2, 1]
        elif status == "revisao": self.status_color = [1, 0.8, 0, 1]
        elif status == "pendente": self.status_color = [1, 0.3, 0.3, 1]
        else: self.status_color = [0, 0, 0, 0]
        self.canvas.after.clear()
        if self.status_color[3] > 0:
            with self.canvas.after:
                Color(*self.status_color)
                Ellipse(pos=(self.x + self.width - dp(30), self.y + self.height - dp(45)), size=(dp(12), dp(12)))

    def _do_long_press(self, dt):
        self._long_press_timer = None
        if not self._is_dragging and not self.is_remote:
            app = MDApp.get_running_app()
            app.vibrate()
            ContextMenu(self.file_path, self.refresh_callback).open()

    def on_release_action(self):
        app = MDApp.get_running_app()
        if self.is_remote:
             app.send_remote_open(self.label_text)
        else:
            SofiaShell.execute(self.file_path)

# ============================================================================
# 🖱️ INTERAÇÃO DE BACKGROUND (CLIQUE LONGO NA ÁREA VAZIA)
# ============================================================================
class ActiveDesktopBackground(MDFloatLayout):
    _long_touch_timer = None
    _touch_origin = None

    def on_touch_down(self, touch):
        # 1. Se o toque for fora da nossa área, ignora
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)

        # 2. INICIA O CRONÔMETRO IMEDIATAMENTE (Modo Otimista)
        self._touch_origin = touch.pos
        self._long_touch_timer = Clock.schedule_once(
            lambda dt: self._open_context_menu(touch), 0.6
        )

        # 3. Passa a batata quente pros filhos (Ícones, ScrollView)
        # Se um ícone for clicado, ele vai retornar True.
        child_handled = super().on_touch_down(touch)

        # 4. Se um ÍCONE pegou o clique, o timer será cancelado pelo próprio ícone (via cancel_timer)

        return child_handled

    def on_touch_move(self, touch):
        # Se moveu o dedo (Scroll), cancela o menu de fundo!
        if self._touch_origin:
            dx = abs(touch.x - self._touch_origin[0])
            dy = abs(touch.y - self._touch_origin[1])
            if dx > dp(10) or dy > dp(10):
                self.cancel_timer()
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        # Se soltou o dedo (clique rápido), cancela o menu de fundo
        self.cancel_timer()
        return super().on_touch_up(touch)

    def cancel_timer(self):
        if self._long_touch_timer:
            self._long_touch_timer.cancel()
            self._long_touch_timer = None

    def _open_context_menu(self, touch):
        # Confirmação final: O app ainda está com o timer ativo?
        if self._long_touch_timer:
            app = MDApp.get_running_app()
            if app:
                app.vibrate()
                app.open_background_menu(touch.pos)
            self._long_touch_timer = None

# ============================================================================
# 📦 CONTAINER DE JANELA (GESTOS SWIPE-TO-HOME)
# ============================================================================
class AppWindowContainer(MDFloatLayout):
    """
    Um container que envolve os apps e adiciona a lógica de gestos (Swipe to Home).
    """
    def __init__(self, app_content, app_id, host_app, **kwargs):
        super().__init__(**kwargs)
        self.app_id = app_id
        self.host_app = host_app
        self.size_hint = (1, 1)

        # 1. Adiciona o conteúdo do app (Mesa Notas, etc)
        self.add_widget(app_content)

        # 2. A "Home Bar" (Aquele tracinho embaixo)
        self.home_bar = Widget(
            size_hint=(None, None),
            size=(dp(120), dp(5)),
            pos_hint={'center_x': 0.5, 'y': 0.02}
        )
        # Desenha o tracinho visualmente
        with self.home_bar.canvas:
            Color(0.8, 0.8, 0.8, 0.5) # Cinza claro translúcido
            self.bar_rect = Rectangle(
                pos=self.home_bar.pos, size=self.home_bar.size
            )

        self.home_bar.bind(pos=self._update_bar, size=self._update_bar)
        self.add_widget(self.home_bar)

        # Variáveis de controle do gesto
        self._touch_start_y = None

    def _update_bar(self, *args):
        self.bar_rect.pos = self.home_bar.pos
        self.bar_rect.size = self.home_bar.size

    def on_touch_down(self, touch):
        # Detecta toque na zona inferior (10% da tela)
        if touch.y < Window.height * 0.1:
            self._touch_start_y = touch.y
            # Não consumimos o toque (return True) pra não bloquear cliques em botões baixos do app,
            # mas ficamos de olho no movimento.
            super().on_touch_down(touch)
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if self._touch_start_y:
            diff = touch.y - self._touch_start_y
            # Se arrastou pra cima significativamente
            if diff > dp(50):
                # Efeito elástico: move a janela um pouco pra cima pra dar feedback
                self.y = diff * 0.2
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if self._touch_start_y:
            diff = touch.y - self._touch_start_y

            # SE ARRASTOU BASTANTE PRA CIMA (> 100dp) -> MINIMIZA
            if diff > dp(80):
                self.host_app.minimize_internal_app(self.app_id)
            else:
                # Se soltou antes, volta pro lugar (cancela o gesto)
                Animation(y=0, d=0.2, t='out_quad').start(self)

            self._touch_start_y = None
        return super().on_touch_up(touch)

# ============================================================================
# 🎨 KV LAYOUT (UI DEFINITION - FULL MERGED)
# ============================================================================

KV = '''
#:import hex kivy.utils.get_color_from_hex
#:import MDIcon kivymd.uix.label.MDIcon
#:import dp kivy.metrics.dp
#:import Window kivy.core.window.Window

<GlassLayer@MDCard>:
    md_bg_color: 0.96, 0.96, 0.96, 0.95
    radius: [22, 22, 22, 22]
    elevation: 0
    padding: dp(0)

<SmartIcon>:
    size_hint: None, None

<QuickToggle@MDCard>:
    size_hint: None, None
    size: dp(50), dp(50)
    radius: [25,]
    md_bg_color: (0, 0.48, 1, 1) if self.is_active else (0.7, 0.7, 0.7, 0.6)
    elevation: 0
    ripple_behavior: True
    pos_hint: {"center_y": .5}
    is_active: False
    icon_name: "help"
    padding: dp(0)

    SmartIcon:
        icon_name: root.icon_name
        icon_size: dp(24)
        size_hint: 1, 1
        pos_hint: {"center_x": .5, "center_y": .5}

<ControlBar@MDCard>:
    size_hint_y: None
    height: dp(54)
    radius: [16,]
    md_bg_color: 1, 1, 1, 0.6
    elevation: 0
    padding: dp(10)
    spacing: dp(15)

MDFloatLayout:
    id: main_layout

    Image:
        id: wallpaper_image
        source: app.current_wallpaper
        allow_stretch: True
        keep_ratio: False
        size_hint: 1, 1

    Carousel:
        id: desktop_carousel
        direction: 'right'
        size_hint: 1, 1
        pos_hint: {'top': 1}
        index: 1 # Inicia na Mesa

        # 1. PÁGINA ESQUERDA: FEED & NOTIFICAÇÕES
        MDFloatLayout:
            id: page_feed

            MDLabel:
                text: "Feed"
                pos_hint: {"center_x": .5, "top": 0.94}
                halign: "center"
                font_style: "H5"
                bold: True
                theme_text_color: "Custom"
                text_color: 1, 1, 1, 0.9
                size_hint_y: None
                height: dp(40)

            # A lista rolável que vai receber os cards
            ScrollView:
                pos_hint: {"center_x": .5, "top": 0.86}
                size_hint: 0.92, 0.86
                shows_vertical_scroll_indicator: False

                MDBoxLayout:
                    id: feed_list
                    orientation: 'vertical'
                    adaptive_height: True
                    spacing: dp(12)
                    padding: [dp(5), dp(10), dp(5), dp(100)] # Espaço sobrando embaixo pro Dock não cobrir

                    # Mensagem padrão quando está vazio (a gente oculta ela depois via código)
                    MDLabel:
                        id: empty_feed_label
                        text: "Tudo tranquilo por aqui."
                        halign: "center"
                        theme_text_color: "Custom"
                        text_color: 1, 1, 1, 0.5
                        font_style: "Caption"
                        size_hint_y: None
                        height: dp(100)

        # 2. PÁGINA CENTRAL: DESKTOP LOCAL
        ActiveDesktopBackground:
            id: page_local

            BoxLayout:
                orientation: 'vertical'
                pos_hint: {'top': 1}
                size_hint_y: None
                height: root.height - dp(80)
                padding: [dp(15), dp(40), dp(15), 0]
                spacing: dp(10)

                BoxLayout:
                    size_hint_y: None
                    height: dp(45)
                    spacing: dp(10)

                    MDIconButton:
                        icon: "arrow-left"
                        theme_text_color: "Custom"
                        text_color: 0.2, 0.2, 0.2, 1
                        md_bg_color: 1, 1, 1, 0.6
                        size_hint: None, None
                        size: dp(45), dp(45)
                        opacity: 1 if app.current_path != app.get_mesa_path() else 0
                        disabled: True if app.current_path == app.get_mesa_path() else False
                        on_release: app.navigate_up()

                    MDCard:
                        radius: [22,]
                        md_bg_color: 0.95, 0.95, 0.95, 0.85
                        elevation: 1
                        padding: [dp(15), 0, dp(15), 0]

                        MDIcon:
                            icon: "magnify"
                            pos_hint: {"center_y": .5}
                            theme_text_color: "Hint"

                        TextInput:
                            id: search_field
                            hint_text: f"Buscar em {app.current_folder_name}..."
                            background_color: 0, 0, 0, 0
                            foreground_color: 0.2, 0.2, 0.2, 1
                            cursor_color: 0, 0.5, 1, 1
                            font_size: "16sp"
                            size_hint_y: 1
                            multiline: False
                            padding_y: [self.height / 2.0 - (self.line_height / 2.0) * len(self._lines), 0]
                            on_text: app.filter_desktop_items(self.text)

                    MDIconButton:
                        id: create_btn
                        icon: "plus"
                        theme_text_color: "Custom"
                        text_color: 0.2, 0.2, 0.2, 1
                        md_bg_color: 1, 1, 1, 0.6
                        size_hint: None, None
                        size: dp(45), dp(45)
                        on_release: app.open_creation_menu()

                ScrollView:
                    size_hint: 1, 1
                    effect_cls: "ScrollEffect"

                    GridLayout:
                        id: desktop_grid
                        cols: 4
                        padding: dp(0)
                        spacing: dp(10)
                        size_hint_y: None
                        height: self.minimum_height
                        row_default_height: dp(100)
                        row_force_default: True

        # 3. PÁGINA DIREITA: VIGIA
        MDFloatLayout:
            id: page_remote

            MDLabel:
                text: "Vigia PC Link" if app.is_connected else "Vigia Desconectado"
                pos_hint: {"center_x": .5, "top": 0.96}
                halign: "center"
                font_style: "H6"
                theme_text_color: "Custom"
                text_color: 1, 1, 1, 0.8
                size_hint_y: None
                height: dp(30)

            BoxLayout:
                orientation: 'vertical'
                pos_hint: {'top': 0.9}
                size_hint_y: None
                height: root.height - dp(100)
                padding: [dp(15), dp(10), dp(15), 0]
                opacity: 1 if app.is_connected else 0
                disabled: not app.is_connected

                ScrollView:
                    size_hint: 1, 1
                    effect_cls: "ScrollEffect"

                    GridLayout:
                        id: remote_grid
                        cols: 4
                        padding: dp(0)
                        spacing: dp(10)
                        size_hint_y: None
                        height: self.minimum_height
                        row_default_height: dp(100)
                        row_force_default: True

            MDCard:
                size_hint: None, None
                size: dp(280), dp(250)
                pos_hint: {"center_x": .5, "center_y": .5}
                radius: [20,]
                md_bg_color: 0.95, 0.95, 0.95, 0.9
                orientation: "vertical"
                padding: dp(20)
                spacing: dp(10)
                opacity: 1 if not app.is_connected else 0
                disabled: app.is_connected

                MDIcon:
                    icon: "monitor-off"
                    halign: "center"
                    font_size: "48sp"
                    theme_text_color: "Custom"
                    text_color: 0.5, 0.5, 0.5, 1

                MDTextField:
                    id: ip_input
                    hint_text: "IP do Computador"
                    text: app.stored_ip
                    mode: "rectangle"

                MDTextField:
                    id: pin_input
                    hint_text: "PIN (veja no /tmp/vigia_pin)"
                    text: app.stored_pin
                    mode: "rectangle"
                    password: True
                    password_mask: "•"

                MDRaisedButton:
                    text: "CONECTAR AO DESKTOP"
                    md_bg_color: 0, 0.4, 0.8, 1
                    size_hint_x: 1
                    on_release: app.toggle_vigia_connection()

    # ZONA DE GATILHO INVISÍVEL NO TOPO (SWIPE DETECTOR GAVETA)
    Widget:
        size_hint_y: None
        height: dp(40)
        pos_hint: {"top": 1}
        on_touch_move: app.on_top_swipe(self, args[1])

    # INDICADORES DE PÁGINA (3 PONTOS)
    MDBoxLayout:
        orientation: 'horizontal'
        size_hint: None, None
        size: dp(70), dp(20)
        pos_hint: {"center_x": .5, "y": 0.12}
        spacing: dp(8)

        MDIcon:
            icon: "circle" if desktop_carousel.index == 0 else "circle-outline"
            font_size: "10sp"
            theme_text_color: "Custom"
            text_color: 1, 1, 1, 1
        MDIcon:
            icon: "circle" if desktop_carousel.index == 1 else "circle-outline"
            font_size: "10sp"
            theme_text_color: "Custom"
            text_color: 1, 1, 1, 1
        MDIcon:
            icon: "circle" if desktop_carousel.index == 2 else "circle-outline"
            font_size: "10sp"
            theme_text_color: "Custom"
            text_color: 1, 1, 1, 1

    GlassLayer:
        id: app_launcher
        size_hint: None, None
        width: root.width - dp(20)
        height: dp(480)
        pos_hint: {"center_x": .5}
        y: -dp(600)

        MDFloatLayout:
            MDLabel:
                text: "Todos os Aplicativos"
                halign: "center"
                pos_hint: {"top": 1}
                size_hint_y: None
                height: dp(40)
                font_style: "Subtitle2"
                theme_text_color: "Custom"
                text_color: 0.3, 0.3, 0.3, 1

            ScrollView:
                pos_hint: {"top": 0.9}
                size_hint: 1, 0.9

                GridLayout:
                    id: main_menu_grid
                    cols: 4
                    padding: dp(10)
                    spacing: dp(15)
                    size_hint_y: None
                    height: self.minimum_height

    # PAINEL INFERIOR (CONTROLE RÁPIDO)
    GlassLayer:
        id: quick_panel
        size_hint: None, None
        size: dp(340), dp(520)
        pos_hint: {"center_x": .5}
        y: -dp(800)

        MDBoxLayout:
            orientation: 'vertical'

            MDBoxLayout:
                size_hint_y: None
                height: dp(90)
                padding: dp(10)
                orientation: 'vertical'

                MDLabel:
                    text: app.clock_time
                    font_style: "H3"
                    halign: "center"
                    bold: True
                    theme_text_color: "Custom"
                    text_color: 0.2, 0.2, 0.2, 1
                    size_hint_y: None
                    height: dp(50)
                    pos_hint: {"center_x": .5}

                MDLabel:
                    text: app.clock_date
                    font_style: "Subtitle1"
                    halign: "center"
                    theme_text_color: "Custom"
                    text_color: 0.4, 0.4, 0.4, 1
                    size_hint_y: None
                    height: dp(30)

            MDBoxLayout:
                orientation: 'vertical'
                padding: [dp(20), dp(10), dp(20), dp(20)]
                spacing: dp(15)

                MDGridLayout:
                    cols: 4
                    rows: 2
                    adaptive_height: True
                    spacing: dp(18)
                    size_hint_y: None
                    height: dp(130)
                    pos_hint: {"center_x": .5}
                    id: quick_toggles_grid

                    QuickToggle:
                        id: tog_wifi
                        icon_name: "wifi"
                        is_active: app.is_wifi_on
                        on_release: app.tog_wifi(self)
                    QuickToggle:
                        id: tog_bluetooth
                        icon_name: "bluetooth"
                        is_active: app.is_bt_on
                        on_release: app.tog_bt(self)
                    QuickToggle:
                        id: tog_airplane
                        icon_name: "airplane"
                        on_release: app.tog_airplane(self)
                    QuickToggle:
                        icon_name: "moon-waning-crescent"
                    QuickToggle:
                        id: tog_flashlight
                        icon_name: "flashlight"
                        is_active: app.is_flash_on
                        on_release: app.tog_flash(self)
                    QuickToggle:
                        icon_name: "screen-rotation"
                    QuickToggle:
                        icon_name: "cog-outline"
                        on_release: app.open_android_settings()
                    QuickToggle:
                        icon_name: "access-point"

                Widget:
                    size_hint_y: 0.2

                ControlBar:
                    MDIcon:
                        icon: "white-balance-sunny"
                        theme_text_color: "Custom"
                        text_color: 0.4, 0.4, 0.4, 1
                        pos_hint: {"center_y": .5}
                    MDSlider:
                        id: brightness_slider
                        min: 0
                        max: 100
                        value: 75
                        color: 0.2, 0.2, 0.2, 1
                        hint: False
                        on_value: app.set_brightness(self.value)

                ControlBar:
                    MDIcon:
                        icon: "volume-high"
                        theme_text_color: "Custom"
                        text_color: 0.4, 0.4, 0.4, 1
                        pos_hint: {"center_y": .5}
                    MDSlider:
                        id: volume_slider
                        min: 0
                        max: 100
                        value: 50
                        color: 0.2, 0.2, 0.2, 1
                        hint: False
                        on_value: app.set_volume(self.value)

                Widget:

            MDBoxLayout:
                size_hint_y: None
                height: dp(50)
                padding: [dp(20), 0, dp(20), dp(10)]
                spacing: dp(10)

                MDCard:
                    radius: [12,]
                    md_bg_color: 1, 1, 1, 0.5
                    elevation: 0
                    padding: dp(8)
                    spacing: dp(8)
                    ripple_behavior: True
                    on_release: app.open_network_menu()

                    SmartIcon:
                        icon_name: "wifi"
                        icon_size: dp(16)
                        size_hint: None, None
                        size: dp(16), dp(16)
                        pos_hint: {"center_y": .5}

                    MDBoxLayout:
                        orientation: 'vertical'
                        pos_hint: {"center_y": .5}
                        MDLabel:
                            text: "Rede Atual"
                            font_style: "Caption"
                            theme_text_color: "Secondary"
                        MDLabel:
                            text: app.current_ssid
                            bold: True

                    MDIcon:
                        icon: "chevron-right"
                        pos_hint: {"center_y": .5}

    # GAVETA SUPERIOR (TOP SHELF) - APPLETS INTELIGENTES
    GlassLayer:
        id: top_shelf
        size_hint: None, None
        width: root.width - dp(20)
        height: dp(250)
        pos_hint: {"center_x": .5}
        y: root.height
        radius: [0, 0, 22, 22]
        padding: dp(15)

        MDBoxLayout:
            orientation: 'vertical'
            MDLabel:
                text: "Gaveta de Applets"
                font_style: "Subtitle2"
                halign: "center"
                size_hint_y: None
                height: dp(30)

            # O Grid onde os Applets vão nascer
            ScrollView:
                MDGridLayout:
                    id: shelf_grid
                    cols: 4
                    spacing: dp(10)
                    adaptive_height: True

    # ZONA DE GATILHO INVISÍVEL NO FUNDO DA TELA (MULTITAREFAS)
    Widget:
        size_hint_y: None
        height: dp(20)
        pos_hint: {"bottom": 1}
        on_touch_move: app.on_bottom_swipe(self, args[1])

    GlassLayer:
        id: mini_drawer
        size_hint: None, None
        width: root.width - dp(20)
        height: dp(140)
        pos_hint: {"center_x": .5}
        y: dp(15)
        radius: [22, 22, 22, 22]
        opacity: 0

        GridLayout:
            id: overflow_grid
            cols: 6
            pos_hint: {"center_y": .5}
            padding: dp(10)
            spacing: dp(10)
            size_hint: 1, None
            height: self.minimum_height
            adaptive_height: True

    GlassLayer:
        id: dock_pill
        size_hint: None, None
        size: root.width - dp(20), dp(60)
        pos_hint: {"center_x": .5}
        y: dp(15)
        radius: [22, 22, 22, 22]

        on_touch_move: app.on_dock_swipe(*args)
        on_touch_up: app.on_dock_release(*args)

        BoxLayout:
            orientation: 'horizontal'
            padding: [dp(10), 0, dp(10), 0]
            spacing: dp(2)

            DockIcon:
                icon_name: "view-grid"
                on_release: app.toggle_menu()

            BoxLayout:
                id: dock_apps_box
                orientation: 'horizontal'
                size_hint_x: None
                width: self.minimum_width
                spacing: dp(2)

            Widget:

            MDCard:
                id: dock_clock_card
                size_hint: None, None
                size: dp(65), dp(44)
                radius: [12,]
                md_bg_color: 0, 0, 0, 0.05
                elevation: 0
                orientation: "vertical"
                pos_hint: {"center_y": .5}
                spacing: 0
                padding: dp(2)
                clips_children: True

                MDLabel:
                    id: clock_lbl
                    text: app.clock_time
                    halign: "center"
                    font_style: "Caption"
                    bold: True
                    font_size: "11sp"
                    theme_text_color: "Custom"
                    text_color: 0.2, 0.2, 0.2, 1
                    size_hint_y: 0.6
                    opacity: 1 if self.parent.width > 30 else 0

                BoxLayout:
                    alignment: 'center'
                    spacing: dp(2)
                    size_hint_y: 0.4
                    opacity: 1 if self.parent.width > 30 else 0
                    SmartIcon:
                        icon_name: "wifi"
                        icon_size: dp(12)
                        size: dp(12), dp(12)
                    MDIcon:
                        icon: "battery-80"
                        font_size: "11sp"
                        theme_text_color: "Custom"
                        text_color: 0.4, 0.4, 0.4, 1
                        size_hint: None, None
                        size: dp(12), dp(12)

            DockIcon:
                icon_name: "cog-outline"
                on_release: app.toggle_quick_settings()

    # TELA DE PROCESSOS ATIVOS (TASK SWITCHER)
    MDFloatLayout:
        id: task_switcher
        size_hint: 1, 1
        pos_hint: {"center_x": .5}
        y: -Window.height # Nasce escondido embaixo
        md_bg_color: 0, 0, 0, 0.85 # Fundo escurecido que foca nos cards

        MDLabel:
            text: "Processos em Execução"
            halign: "center"
            pos_hint: {"top": 0.9}
            font_style: "H6"
            theme_text_color: "Custom"
            text_color: 1, 1, 1, 1
            size_hint_y: None
            height: dp(40)

        # O Carrossel Horizontal
        ScrollView:
            size_hint: 1, 0.6
            pos_hint: {"center_y": .5}
            do_scroll_y: False
            do_scroll_x: True
            shows_horizontal_scroll_indicator: False

            MDBoxLayout:
                id: task_list
                orientation: 'horizontal'
                size_hint_x: None
                width: self.minimum_width
                padding: dp(30)
                spacing: dp(20)

        # Botão de Bordoada Global (Mata Tudo)
        MDFloatingActionButton:
            icon: "broom"
            md_bg_color: 0.8, 0.2, 0.2, 1
            pos_hint: {"center_x": .5, "y": 0.08}
            on_release: app.kill_all_tasks()
            elevation: 2
'''

class SophiaMobileApp(MDApp):
    is_drawer_open = False
    is_panel_open = False
    is_shelf_open = BooleanProperty(False)
    swipe_start_y = 0

    is_vigia_open = False
    is_connected = BooleanProperty(False)
    remote_files = ListProperty([])
    stored_ip = StringProperty("192.168.0.100")
    stored_pin = StringProperty("")

    # Estados de Hardware
    is_flash_on = BooleanProperty(False)
    is_wifi_on = BooleanProperty(True)
    is_bt_on = BooleanProperty(False)
    is_air_on = BooleanProperty(False)

    clock_time = StringProperty("00:00")
    clock_date = StringProperty("")
    battery_percent = StringProperty("50%")
    theme_style_str = StringProperty("Light")

    # Nome da Rede Wi-Fi (Dinâmico)
    current_ssid = StringProperty("Desconectado")

    # Dock limpo: Apenas o Gerenciador de Arquivos (Interno) e Web (Genérico)
    pinned_apps = ListProperty(["folder", "web"])

    # Novo: Papel de Parede Atual (com persistência)
    current_wallpaper = StringProperty("assets/wallpaper.jpg")

    known_mesa_files = ListProperty([])
    current_path = StringProperty("")
    current_folder_name = StringProperty("Mesa")
    menu = None
    bg_menu = None  # Menu de fundo
    mobile_applets = []

    # NOVA: Guarda os applets vivos da Mesa
    active_desktop_applets = ListProperty([])

    # --- TASK SWITCHER VARS ---
    is_task_switcher_open = BooleanProperty(False)
    running_internal_apps = {}
    running_android_apps = {}

    # --- CONSTANTES DO UNIVERSO ---
    SOPHIA_ROOT = ""
    MESA_DIR = ""
    APPS_DIR = ""
    SYS_DIR = ""
    APPLETS_DIR = ""

    def build(self):
        # 🌟 CORREÇÃO: MODO IMERSIVO APENAS NO ANDROID
        # Se for PC, respeita o tamanho (380, 740) definido no topo do script.
        if platform == 'android':
            Window.fullscreen = 'auto'

        self.theme_cls.theme_style = "Light"
        self.theme_cls.primary_palette = "Blue"
        self.theme_style_str = self.theme_cls.theme_style
        self.network = VigiaNetworkClient(self)

        Clock.schedule_interval(self.update_clock, 1)
        self.update_clock(0)
        self.update_battery(0)
        Clock.schedule_interval(self.update_battery, 60)

        # Loop de Hardware Real
        Clock.schedule_interval(self.check_hardware_status, 2)

        Window.bind(on_resize=self.on_window_resize)
        Window.bind(on_keyboard=self.on_keyboard)
        self.request_android_permissions()

        # INICIA UNIVERSO (Define os caminhos)
        self.init_sophia_universe()

        return Builder.load_string(KV)

    # --- UNIVERSO SOPHIA (FILE SYSTEM) ---
    def init_sophia_universe(self):
        # Descobre a raiz real do aparelho (ou PC para testes)
        if platform == 'android':
            from android.storage import primary_external_storage_path
            base_dir = primary_external_storage_path()
        else:
            base_dir = os.path.expanduser("~") # Fallback pra rodar no Linux/Windows

        # Define a fronteira do nosso sistema parasita
        self.SOPHIA_ROOT = os.path.join(base_dir, "SophiaOS")
        self.MESA_DIR = os.path.join(self.SOPHIA_ROOT, "Mesa")
        self.APPS_DIR = os.path.join(self.SOPHIA_ROOT, "Aplicativos")
        self.SYS_DIR = os.path.join(self.SOPHIA_ROOT, "Sistema")
        self.APPLETS_DIR = os.path.join(self.SYS_DIR, "Applets")

        # O Fiat Lux! Cria o universo se ele não existir
        pastas_essenciais = [self.MESA_DIR, self.APPS_DIR, self.SYS_DIR, self.APPLETS_DIR]
        for pasta in pastas_essenciais:
            os.makedirs(pasta, exist_ok=True)

        print(f"🌌 Universo Sophia iniciado em: {self.SOPHIA_ROOT}")

    def on_start(self):
        # Carregar configurações persistentes
        self.store = JsonStore("sophia_config.json")

        # Carregar Wallpaper Salvo (Lógica Robusta)
        if self.store.exists('display'):
            saved_wp = self.store.get('display').get('wallpaper')
            if saved_wp and os.path.exists(saved_wp):
                self.current_wallpaper = saved_wp

        self.current_path = self.get_mesa_path()
        self.current_folder_name = os.path.basename(self.current_path)
        Clock.schedule_once(self.refresh_dock_icons)
        Clock.schedule_once(self.setup_creation_menu)
        Clock.schedule_interval(self.check_mesa_changes, 2)
        self.ensure_mesa_dir()
        self.refresh_desktop_items()
        self.scan_android_apps()

        # --- CARREGA OS APPLETS (JSON) ---
        self.populate_top_shelf_applets()

        # --- INICIA SERVIÇO DE NOTÍCIAS RSS ---
        self.start_rss_service()

        # Sincroniza Hardware Inicial
        self.check_hardware_status(0)
        if IS_ANDROID:
            vol = AndroidUtils.get_volume()
            self.root.ids.volume_slider.value = vol

    # --- CARREGADOR DINÂMICO DE APPS ---
    def launch_dynamic_widget(self, app_path, entry_point, app_id, manifest):
        """Transforma um arquivo .py solto em uma janela do sistema (COM GESTOS)"""
        full_path = os.path.join(app_path, entry_point)

        if not os.path.exists(full_path):
            self.spawn_bubble(f"Erro: {entry_point} não encontrado!", "alert")
            return

        # Verifica se já está rodando
        if app_id in self.running_internal_apps:
            self.resume_task(f"internal:{app_id}")
            return

        try:
            # 1. Carregamento Dinâmico
            spec = importlib.util.spec_from_file_location(f"dynamic_app_{app_id}", full_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            if hasattr(module, 'get_widget'):
                app_content = module.get_widget(self)

                # 2. Encapsula no Container de Gestos
                app_window = AppWindowContainer(app_content, app_id, self)
                app_window.y = -Window.height
                self.root.add_widget(app_window)

                Animation(y=0, d=0.4, t='out_back').start(app_window)

                # 5. Registra
                self.running_internal_apps[app_id] = {
                    "widget": app_window,
                    "manifest": manifest,
                    "timestamp": time.time()
                }

            else:
                self.spawn_bubble("O App não tem a função 'get_widget'!", "code-braces")

        except Exception as e:
            print(f"Erro ao lançar app dinâmico: {e}")
            import traceback
            traceback.print_exc()
            self.spawn_bubble(f"Crash ao abrir app: {e}", "bug")

    def minimize_internal_app(self, app_id):
        """Manda o app para o background (sem matar)"""
        if app_id in self.running_internal_apps:
            window = self.running_internal_apps[app_id]["widget"]

            # Animação de "cair" para fora da tela
            anim = Animation(y=-Window.height, opacity=0, d=0.3, t='in_quad')

            def on_minimized(*args):
                window.pos_hint = {}
                window.y = -Window.height

            anim.bind(on_complete=on_minimized)
            anim.start(window)
            self.vibrate()

    # --- LÓGICA DO GERENCIADOR DE TAREFAS (MULTITAREFA) ---
    def register_android_task(self, pkg_name):
        """Anota na prancheta que o Android abriu um processo"""
        nice_name = pkg_name.split('.')[-1].capitalize()
        self.running_android_apps[pkg_name] = {
            "name": nice_name,
            "icon": "android",
            "time_started": time.strftime("%H:%M")
        }

    def on_bottom_swipe(self, instance, touch):
        # Deslize pra cima saindo da borda inferior (< 20px)
        if touch.y < dp(20) and touch.dy > 15 and not self.is_task_switcher_open:
            self.toggle_task_switcher()

        # Deslize pra baixo se a tela já estiver aberta para fechar
        elif self.is_task_switcher_open and touch.dy < -15:
            self.toggle_task_switcher()

    def toggle_task_switcher(self):
        switcher = self.root.ids.task_switcher
        if self.is_task_switcher_open:
            Animation(y=-Window.height, d=0.3, t='out_quad').start(switcher)
            self.is_task_switcher_open = False
        else:
            self.populate_task_switcher()
            Animation(y=0, d=0.3, t='out_back').start(switcher)
            self.is_task_switcher_open = True
            self.vibrate()

    def populate_task_switcher(self):
        """Monta a bandeja puxando de dois mundos diferentes"""
        task_list = self.root.ids.task_list
        task_list.clear_widgets()

        # 1. CARREGA OS APPS INTERNOS (NOSSOS .APPICON)
        for app_id, data in self.running_internal_apps.items():
            manifest = data["manifest"]
            task_data = {
                "name": manifest.get("nome_exibicao", "Ferramenta"),
                "icon": manifest.get("icon", "application"),
                "pkg": f"internal:{app_id}",
                "info": f"Folha Kivy\nStatus: Ativa"
            }
            task_list.add_widget(self._create_task_card(task_data))

        # 2. CARREGA OS APPS ANDROID (O HOSPEDEIRO)
        for pkg, data in self.running_android_apps.items():
            task_data = {
                "name": data["name"],
                "icon": "android",
                "pkg": f"android:{pkg}",
                "info": f"Android Nativo\nInício: {data['time_started']}"
            }
            task_list.add_widget(self._create_task_card(task_data))

    def _create_task_card(self, task_data):
        from kivymd.uix.card import MDCard
        from kivymd.uix.label import MDLabel, MDIcon
        from kivy.uix.boxlayout import BoxLayout
        from kivymd.uix.button import MDIconButton

        card = MDCard(
            orientation='vertical',
            size_hint=(None, None),
            size=(dp(220), dp(300)),
            md_bg_color=(0.1, 0.1, 0.1, 0.8),
            radius=[16,],
            padding=dp(15),
            ripple_behavior=True
        )
        card.bind(on_release=lambda x, p=task_data["pkg"]: self.resume_task(p))

        # Cabeçalho com Ícone e Nome
        header = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(40), spacing=dp(10))
        header.add_widget(MDIcon(icon=task_data["icon"], theme_text_color="Custom", text_color=(1,1,1,1), font_size="24sp", size_hint_x=None, width=dp(30)))
        header.add_widget(MDLabel(text=task_data["name"], bold=True, theme_text_color="Custom", text_color=(1,1,1,1)))

        # A Mágica: A Informação Útil Centralizada
        info_label = MDLabel(
            text=task_data.get("info", "Rodando em segundo plano"),
            halign="center",
            valign="center",
            font_style="Caption",
            theme_text_color="Custom", text_color=(0.7, 0.9, 1, 1),
            size_hint_y=1
        )

        # Rodapé com o botão de matar o processo
        footer = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(40))
        footer.add_widget(Widget()) # Espaçador
        footer.add_widget(MDIconButton(
            icon="close-circle-outline",
            theme_text_color="Custom", text_color=(1, 0.3, 0.3, 1),
            on_release=lambda x, c=card, p=task_data["pkg"]: self.kill_single_task(c, p)
        ))

        card.add_widget(header)
        card.add_widget(info_label)
        card.add_widget(footer)

        return card

    def resume_task(self, pkg_string):
        self.toggle_task_switcher() # Desce a bandeja

        # Desempacota pra saber de qual mundo veio
        task_type, real_id = pkg_string.split(':', 1)

        if task_type == "internal":
            # Puxa a "Folha" (hospedeira) de volta pra tela
            if real_id in self.running_internal_apps:
                window_widget = self.running_internal_apps[real_id]["widget"]
                # Força update de layout caso tenha perdido
                window_widget.pos_hint = {'center_x': 0.5, 'center_y': 0.5}
                # Se minimizou com y negativo, reseta para 0
                Animation(y=0, opacity=1, d=0.3, t='out_back').start(window_widget)

        elif task_type == "android":
            # Dá um cutucão no Android pra trazer o Activity pra frente
            SofiaShell._launch_android_intent_raw(real_id)

    def kill_single_task(self, card_widget, pkg_string):
        # A física do descarte (Swipe Up)
        anim = Animation(y=card_widget.y + dp(100), opacity=0, d=0.2, t='out_quad')
        task_type, real_id = pkg_string.split(':', 1)

        def on_dead(*args):
            if card_widget.parent:
                self.root.ids.task_list.remove_widget(card_widget)

            # Matando um app nosso (libera a UI do Kivy)
            if task_type == "internal":
                if real_id in self.running_internal_apps:
                    window_widget = self.running_internal_apps[real_id]["widget"]
                    self.root.remove_widget(window_widget) # Destrói o widget
                    del self.running_internal_apps[real_id]

            # A BORDOADA no Android zumbi (ActivityManager JNI)
            elif task_type == "android":
                if real_id in self.running_android_apps:
                    del self.running_android_apps[real_id]
                if platform == 'android':
                    AndroidUtils.kill_background_process(real_id)
                else:
                    SofiaShell.show_toast(f"Simulando Bordoada em {real_id}")

        anim.bind(on_complete=on_dead)
        anim.start(card_widget)
        self.vibrate()

    def kill_all_tasks(self):
        # A Vassoura Mágica: Mata tudo sem dó
        task_list = self.root.ids.task_list

        # 1. Mata apps internos
        for app_id in list(self.running_internal_apps.keys()):
            window_widget = self.running_internal_apps[app_id]["widget"]
            self.root.remove_widget(window_widget)
        self.running_internal_apps.clear()

        # 2. Mata apps Android
        for pkg_name in list(self.running_android_apps.keys()):
            if platform == 'android':
                AndroidUtils.kill_background_process(pkg_name)
        self.running_android_apps.clear()

        # 3. Limpa a UI
        task_list.clear_widgets()

        self.spawn_bubble("RAM completamente limpa!", "memory")
        Clock.schedule_once(lambda dt: self.toggle_task_switcher(), 0.5)

    # --- LÓGICA DE FEED E NOTIFICAÇÕES ---
    def push_notification(self, title, text, icon_name="bell-ring-outline", show_bubble=True):
        # Opcionalmente lança aquela bolha pop-up que já codamos
        if show_bubble:
            self.spawn_bubble(text, icon_name)

        feed_list = self.root.ids.feed_list
        empty_label = self.root.ids.empty_feed_label

        # Esconde a mensagem de "Tudo tranquilo" se for o primeiro aviso
        if empty_label in feed_list.children:
            feed_list.remove_widget(empty_label)

        # Cria o card e adiciona no TOPO da lista (index=len garante ir pro começo no Kivy)
        card = NotificationCard(title=title, text=text, icon_name=icon_name)

        # Começa invisível e com altura zero para nascer animado
        target_height = card.height
        card.height = 0
        card.opacity = 0
        feed_list.add_widget(card, index=len(feed_list.children))

        Animation(height=target_height, opacity=1, d=0.4, t='out_back').start(card)

    def start_rss_service(self):
        """Inicia a busca de notícias em segundo plano para não travar a UI"""
        # Suas fontes de leitura diária
        urls = [
            "https://br-linux.org/feed/",
            "https://gizmodo.uol.com.br/feed/"
        ]
        import threading
        threading.Thread(target=self._fetch_rss_worker, args=(urls,), daemon=True).start()

    def _fetch_rss_worker(self, urls):
        try:
            import feedparser
        except ImportError:
            print("⚠️ Biblioteca 'feedparser' não encontrada. RSS desativado.")
            return

        for url in urls:
            try:
                feed = feedparser.parse(url)
                source_name = feed.feed.get('title', 'Notícia')

                # Pega as 3 últimas notícias de cada feed
                for entry in feed.entries[:3]:
                    title = entry.get('title', 'Sem título')
                    link = entry.get('link', '')

                    # Manda pra Main Thread do Kivy desenhar na tela
                    Clock.schedule_once(
                        lambda dt, t=title, s=source_name, l=link: self.add_rss_to_feed(t, s, l)
                    )
                    import time
                    time.sleep(0.2) # Pausa rápida pra animação de entrada ficar em cascata
            except Exception as e:
                print(f"Erro ao baixar RSS {url}: {e}")

    def add_rss_to_feed(self, title, source_name, link):
        feed_list = self.root.ids.feed_list
        empty_label = self.root.ids.empty_feed_label

        if empty_label in feed_list.children:
            feed_list.remove_widget(empty_label)

        card = RSSFeedCard(title=title, source_name=source_name, link=link)

        target_height = card.height
        card.height = 0
        card.opacity = 0

        # Joga as notícias mais pro final da lista pra dar prioridade aos avisos do sistema no topo
        feed_list.add_widget(card)

        Animation(height=target_height, opacity=1, d=0.4, t='out_back').start(card)

    # --- LOGICA DE APPLETS (MENU SUSPENSO) ---
    def open_applet_shelf_menu(self, card_widget):
        self.vibrate()

        menu_items = [
            {
                "text": "Adicionar à Mesa",
                "viewclass": "OneLineIconListItem",
                "icon": "pin-outline",
                "height": dp(56),
                "on_release": lambda c=card_widget: self._applet_menu_callback("add", c)
            },
            {
                "text": "Configurar Applet",
                "viewclass": "OneLineIconListItem",
                "icon": "cog-outline",
                "height": dp(56),
                "on_release": lambda c=card_widget: self._applet_menu_callback("config", c)
            }
        ]

        self.applet_shelf_menu = MDDropdownMenu(
            caller=card_widget,
            items=menu_items,
            width_mult=4.5,
            radius=[16, 16, 16, 16]
        )
        self.applet_shelf_menu.open()

    def _applet_menu_callback(self, action, card_widget):
        self.applet_shelf_menu.dismiss()

        if action == "add":
            self.add_applet_to_desktop(card_widget.applet_data)
        elif action == "config":
            self.spawn_bubble(f"Ajustar: {card_widget.applet_data.get('name')}", "hammer-wrench")
            self.toggle_top_shelf()

    def load_pluggable_applets(self):
        """Lê os arquivos JSON e guarda na memória do celular"""
        self.mobile_applets = []
        applets_dir = self.APPLETS_DIR # Usa o diretório do Universo Sophia

        if not os.path.exists(applets_dir):
            try:
                os.makedirs(applets_dir)
            except: pass
            return

        for filename in os.listdir(applets_dir):
            if filename.endswith(".json"):
                try:
                    with open(os.path.join(applets_dir, filename), 'r', encoding='utf-8') as f:
                        applet_data = json.load(f)
                        self.mobile_applets.append(applet_data)
                except Exception as e:
                    print(f"Erro ao ler o applet {filename}: {e}")

        print(f"📚 Luz carregou {len(self.mobile_applets)} applets com sucesso!")

    def populate_top_shelf_applets(self):
        """Gera os ícones físicos na gaveta superior baseados nos JSONs"""
        self.load_pluggable_applets()

        shelf_grid = self.root.ids.shelf_grid
        shelf_grid.clear_widgets()

        for applet in self.mobile_applets:
            # Só carrega os que fazem sentido ter ícone na mesa/gaveta
            if applet.get("display_on_desktop", False) or "drop_triggers" in applet:

                # Cria o Card (agora é o nosso card puro e clicável)
                applet_card = AppletShelfCard()
                applet_card.applet_data = applet

                # Ícone do Applet
                icon_name = applet.get("icon", "application-x-executable")
                applet_icon = SmartIcon(icon_name=icon_name, icon_size=dp(42))
                applet_icon.pos_hint = {"center_x": .5}

                # Nome do Applet
                applet_label = MDLabel(
                    text=applet.get("name", "Applet"),
                    halign="center",
                    font_style="Caption",
                    theme_text_color="Custom",
                    text_color=(1,1,1,1),
                    shorten=True,
                    shorten_from="right"
                )

                applet_card.add_widget(applet_icon)
                applet_card.add_widget(applet_label)
                shelf_grid.add_widget(applet_card)

    def add_applet_to_desktop(self, applet_data):
        # Impede de enchar a mesa com o mesmo applet duplicado
        for existing in self.active_desktop_applets:
            if existing.get("name") == applet_data.get("name"):
                self.spawn_bubble("Este applet já está na Mesa!", "check")
                self.toggle_top_shelf()
                return

        # Guarda na memória permanente e manda a tela atualizar
        self.active_desktop_applets.append(applet_data)
        self.refresh_desktop_items()

        self.spawn_bubble(f"{applet_data.get('name')} fixado na Mesa!", "pin")
        self.toggle_top_shelf() # Fecha a gaveta pra ver a mágica

    def set_wallpaper(self, path):
        # Atualiza a variável (o KV detecta sozinho)
        self.current_wallpaper = path

        # Salvar na memória permanente
        if not hasattr(self, 'store'): self.store = JsonStore("sophia_config.json")
        self.store.put('display', wallpaper=path)

        # Feedback visual
        SofiaShell.show_toast("Visual atualizado!")

    def on_keyboard(self, window, key, scancode, codepoint, modifier):
        if key == 27: # ESC/Back
            if self.is_task_switcher_open:
                self.toggle_task_switcher()
                return True
            if self.root.ids.app_launcher.y > 0:
                self.toggle_menu()
                return True
            if self.root.ids.quick_panel.opacity > 0 and self.is_panel_open:
                self.toggle_quick_settings()
                return True
            if self.is_drawer_open:
                self.anim_mini_drawer(False)
                return True
            if self.is_shelf_open:
                self.toggle_top_shelf()
                return True
            if self.current_path == self.get_mesa_path():
                return True
            self.navigate_up()
            return True
        return False

    def request_android_permissions(self):
        if platform == 'android':
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.CAMERA,
                Permission.VIBRATE,
                Permission.QUERY_ALL_PACKAGES,
                Permission.WRITE_SETTINGS,
                Permission.ACCESS_FINE_LOCATION,
                Permission.ACCESS_COARSE_LOCATION,
                Permission.BLUETOOTH,
                Permission.BLUETOOTH_ADMIN,
                Permission.ACCESS_WIFI_STATE,
                Permission.CHANGE_WIFI_STATE,
                Permission.KILL_BACKGROUND_PROCESSES # CRÍTICO PARA O TASK MANAGER
            ])

    def vibrate(self):
        if platform == 'android':
            try:
                Context = autoclass('android.content.Context')
                activity = autoclass('org.kivy.android.PythonActivity').mActivity
                vibrator = activity.getSystemService(Context.VIBRATOR_SERVICE)
                vibrator.vibrate(50)
            except: pass

    def get_mesa_path(self):
        return self.MESA_DIR

    def ensure_mesa_dir(self):
        path = self.get_mesa_path()
        if not os.path.exists(path):
            try:
                os.makedirs(path)
                with open(os.path.join(path, "Ideias.txt"), "w") as f: f.write("Olá Mundo")
            except Exception as e: print(f"❌ Erro ao criar Mesa: {e}")

    def navigate_to(self, path):
        if os.path.isdir(path):
            self.current_path = path
            self.current_folder_name = os.path.basename(path)
            self.root.ids.search_field.text = ""
            self.refresh_desktop_items()

    def navigate_up(self):
        if self.current_path == self.get_mesa_path(): return
        parent = os.path.dirname(self.current_path)
        self.navigate_to(parent)

    def check_mesa_changes(self, dt):
        if self.root.ids.search_field.text: return
        path = self.current_path
        if not os.path.exists(path): return
        try:
            current_files = sorted(os.listdir(path))
            current_files = [f for f in current_files if not f.startswith('.')]
            if current_files != self.known_mesa_files:
                self.known_mesa_files = current_files
                self.refresh_desktop_items(current_files)
        except Exception as e: print(f"Erro ao ler Mesa: {e}")

    def check_hardware_status(self, dt):
        """Verifica o estado real do hardware e atualiza os botões"""
        self.current_ssid = AndroidUtils.get_current_ssid()
        self.is_wifi_on = AndroidUtils.is_wifi_enabled()
        self.is_bt_on = AndroidUtils.is_bluetooth_enabled()

    def filter_desktop_items(self, text):
        text = text.lower().strip()
        path = self.current_path
        if not os.path.exists(path): return
        try:
            all_items = sorted(os.listdir(path))
        except: return
        filtered_items = []
        for item in all_items:
            if item.startswith('.'): continue
            if not text:
                filtered_items.append(item)
                continue
            if text in item.lower():
                filtered_items.append(item)
                continue
            full_path = os.path.join(path, item)
            attrs = MetadataManager.get_attributes(full_path)
            tags = attrs.get("tags", [])
            match_tag = any(text in tag.lower() for tag in tags)
            status = attrs.get("status", "")
            match_status = text in status.lower() if status else False
            state = attrs.get("state", "")
            match_state = text in state.lower() if state else False
            if match_tag or match_status or match_state:
                filtered_items.append(item)
        self.refresh_desktop_items(filtered_items)

    def refresh_desktop_items(self, items_to_show=None):
        desktop_grid = self.root.ids.desktop_grid
        desktop_grid.clear_widgets() # Limpa tudo

        # 1. A MÁGICA SALVADORA: Desenha os Applets Fixados primeiro
        # Só injeta na área de trabalho principal (raiz da Mesa)
        if self.current_path == self.get_mesa_path():
            for applet_data in self.active_desktop_applets:
                novo_applet = DesktopApplet(
                    applet_data=applet_data,
                    icon_name=applet_data.get("icon", "application-cog"),
                    label_text=applet_data.get("name", "Applet")
                )
                desktop_grid.add_widget(novo_applet)

        # 2. Renderiza os arquivos normais da pasta (Continua igual)
        path = self.current_path
        if items_to_show is None:
            try: items_to_show = sorted(os.listdir(path))
            except: items_to_show = []

        for item in items_to_show:
            if item.startswith('.'): continue
            full_path = os.path.join(path, item)

            app_icon = AppIcon.factory(full_path)

            if app_icon:
                display_text = app_icon.get_display_name()
                icon_name = app_icon.get_display_icon()
            elif os.path.isdir(full_path):
                display_text = item
                icon_name = "folder"
            else:
                display_text = item
                icon_name = "text"
                if item.endswith(".webicon"): icon_name = "text-html"
                elif item.endswith((".png", ".jpg", ".jpeg", ".webp")): icon_name = "image"
                elif item.endswith((".mp4", ".mkv", ".webm")): icon_name = "video"
                elif item.endswith((".mp3", ".wav", ".ogg")): icon_name = "audio"
                elif "pdf" in item.lower(): icon_name = "pdf"
                elif item.endswith((".txt", ".md", ".json", ".py", ".sh")): icon_name = "text"
                else:
                    mime_type, _ = mimetypes.guess_type(full_path)
                    if mime_type and mime_type.startswith('image'): icon_name = "image"
                    elif mime_type and mime_type.startswith('text'): icon_name = "text"

            desktop_item = DesktopItem(
                refresh_callback=lambda: self.check_mesa_changes(0),
                label_text=display_text,
                icon_name=icon_name,
                file_path=full_path,
                is_remote=False
            )
            desktop_grid.add_widget(desktop_item)

    def scan_android_apps(self):
        """
        Lista Apps Nativos do Android E os nossos Apps Internos (.appicon)
        """
        menu_grid = self.root.ids.main_menu_grid
        menu_grid.clear_widgets()

        # 1. Ferramenta Interna de Arquivos (Atalho Fixo)
        icon_files = AppGridIcon(icon_name="folder")
        icon_files.bind(on_release=lambda x: self.navigate_to(self.get_mesa_path()))
        menu_grid.add_widget(icon_files)

        # 2. VARREDURA SOPHIA: Procura .appicon na Mesa e na pasta Aplicativos
        # Locais onde os apps podem morar
        search_paths = [self.MESA_DIR, self.APPS_DIR]

        found_apps = set() # Para evitar duplicatas se o mesmo app estiver nas duas listas

        for directory in search_paths:
            if os.path.exists(directory):
                for item_name in os.listdir(directory):
                    full_path = os.path.join(directory, item_name)

                    # Verifica se é um App Sophia (.appicon)
                    if os.path.isdir(full_path) and item_name.endswith(".appicon"):
                        if item_name in found_apps: continue
                        found_apps.add(item_name)

                        # Usa a Factory para ler o manifesto e pegar o ícone certo
                        app_obj = AppIcon.factory(full_path)

                        if app_obj:
                            # Cria o ícone visual
                            icon = AppGridIcon(icon_name=app_obj.get_display_icon())
                            # O Pulo do Gato: Bind que chama o execute() do objeto AppIcon
                            icon.bind(on_release=lambda x, app=app_obj: app.execute())
                            menu_grid.add_widget(icon)

        # 3. Apps do Sistema Android (Real)
        if platform == 'android':
            try:
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                pm = PythonActivity.mActivity.getPackageManager()
                packages = pm.getInstalledApplications(pm.GET_META_DATA)

                count = 0
                for app_info in packages:
                    # Ignora apps que não têm ícone de lançamento (opcional, mas limpa a lista)
                    if pm.getLaunchIntentForPackage(app_info.packageName) is None:
                        continue

                    pkg_name = app_info.packageName

                    # Cria ícone para o app Android
                    icon = AppGridIcon(icon_name="app-native") # Futuramente podemos extrair o ícone real via JNI
                    icon.bind(on_release=lambda x, p=pkg_name: SofiaShell.execute_android_package(p))
                    menu_grid.add_widget(icon)

                    count += 1
                    if count > 60: break # Limite para não pesar a memória
            except Exception as e:
                print(f"Erro ao listar apps Android: {e}")

    def toggle_vigia_connection(self):
        if self.is_connected:
            self.network.connected = False
            self.on_connection_lost()
        else:
            ip_text = self.root.ids.ip_input.text
            pin_text = self.root.ids.pin_input.text

            if not pin_text:
                SofiaShell.show_toast("Digite o PIN do Vigia!")
                return

            self.stored_ip = ip_text
            self.stored_pin = pin_text

            # Passa o PIN para a conexão
            success = self.network.connect(self.stored_ip, self.stored_pin)
            if success:
                self.is_connected = True
            else:
                SofiaShell.show_toast("Falha: Verifique IP ou PIN.")

    def on_connection_lost(self):
        self.is_connected = False
        self.remote_files = []
        self.root.ids.remote_grid.clear_widgets()
        print("Vigia desconectado.")

    def update_remote_files(self, files):
        print(f"📦 Processando {len(files)} arquivos remotos...")
        self.remote_files = files
        remote_grid = self.root.ids.remote_grid
        remote_grid.clear_widgets()

        for f in files:
            fname = f.get('name', 'Desconhecido')
            is_dir = f.get('is_dir', False)
            attrs = f.get('attributes', {})

            icon_name = "unknown"
            fname_lower = fname.lower()

            if is_dir:
                icon_name = "folder"
            elif fname_lower.endswith(".webicon"):
                icon_name = "text-html"
            elif fname_lower.endswith(".appimage") or fname_lower.endswith(".desktop"):
                icon_name = "console"
            elif fname_lower.endswith((".png", ".jpg", ".jpeg", ".webp")):
                icon_name = "image"
            elif fname_lower.endswith((".mp4", ".mkv", ".webm")):
                icon_name = "video"
            elif fname_lower.endswith((".mp3", ".wav", ".ogg")):
                icon_name = "audio"
            elif fname_lower.endswith(".pdf"):
                icon_name = "pdf"
            elif fname_lower.endswith((".txt", ".md", ".json", ".py", ".sh")):
                icon_name = "text"

            if attrs and attrs.get("__mimetype__") == "inode/directory":
                 icon_name = "folder"

            item = DesktopItem(
                icon_name=icon_name,
                label_text=fname,
                is_remote=True,
                file_path=fname
            )
            remote_grid.add_widget(item)

    def send_remote_open(self, filename):
        print(f"Pedindo para abrir no PC: {filename}")
        self.network.send_command({
            "command": "remote_exec",
            "path": filename
        })

    def setup_creation_menu(self, dt):
        menu_items = [
            # Seção de Arquivos Comuns
            {"text": "Nova Pasta", "viewclass": "OneLineIconListItem", "icon": "folder-plus", "height": dp(56), "on_release": lambda x="folder": self.menu_callback(x)},
            {"text": "Novo Arquivo Texto", "viewclass": "OneLineIconListItem", "icon": "file-document-outline", "height": dp(56), "on_release": lambda x="file": self.menu_callback(x)},

            # Seção de Sistema / Web
            {"text": "Criar Web Link", "viewclass": "OneLineIconListItem", "icon": "web", "height": dp(56), "on_release": lambda x="app_web": self.menu_callback(x)},

            # Seção Avançada (Dev)
            {"text": "Novo App (Dev)", "viewclass": "OneLineIconListItem", "icon": "android-debug-bridge", "height": dp(56), "on_release": lambda x="app_universal": self.menu_callback(x)},

            # Utilitários
            {"text": "Atualizar Tela", "viewclass": "OneLineIconListItem", "icon": "refresh", "height": dp(56), "on_release": lambda x="refresh": self.menu_callback(x)}
        ]
        self.menu = MDDropdownMenu(caller=self.root.ids.create_btn, items=menu_items, width_mult=4.5, max_height=dp(320))

    def open_creation_menu(self):
        if not self.menu: self.setup_creation_menu(0)
        self.menu.open()

    # --- NOVO: Menu de Contexto do Fundo ---
    def open_background_menu(self, touch_pos):
        # Cria um widget invisível temporário onde foi o clique para ancorar o menu
        dummy_anchor = Widget(pos=touch_pos, size=(0,0), size_hint=(None, None))
        self.root.add_widget(dummy_anchor)

        menu_items = [
            {"text": "Nova Pasta", "viewclass": "OneLineIconListItem", "icon": "folder-plus", "height": dp(56), "on_release": lambda x="folder": self._bg_menu_callback(x, dummy_anchor)},
            {"text": "Novo Arquivo", "viewclass": "OneLineIconListItem", "icon": "file-document-outline", "height": dp(56), "on_release": lambda x="file": self._bg_menu_callback(x, dummy_anchor)},
            {"text": "Colar", "viewclass": "OneLineIconListItem", "icon": "content-paste", "height": dp(56), "on_release": lambda x="paste": self._bg_menu_callback(x, dummy_anchor)},
            {"text": "Atualizar", "viewclass": "OneLineIconListItem", "icon": "refresh", "height": dp(56), "on_release": lambda x="refresh": self._bg_menu_callback(x, dummy_anchor)},
            # NOVO ITEM: Papel de Parede (Inserido!)
            {"text": "Papel de Parede", "viewclass": "OneLineIconListItem", "icon": "image", "height": dp(56), "on_release": lambda x="wallpaper": self._bg_menu_callback(x, dummy_anchor)},
            {"text": "Configurações", "viewclass": "OneLineIconListItem", "icon": "cog-outline", "height": dp(56), "on_release": lambda x="settings": self._bg_menu_callback(x, dummy_anchor)},
        ]

        self.bg_menu = MDDropdownMenu(
            caller=dummy_anchor,
            items=menu_items,
            width_mult=4,
        )
        self.bg_menu.bind(on_dismiss=lambda x: self.root.remove_widget(dummy_anchor))
        self.bg_menu.open()

    def _bg_menu_callback(self, action, anchor):
        self.bg_menu.dismiss()
        self.root.remove_widget(anchor)

        if action == "refresh":
            self.refresh_desktop_items()
        elif action == "settings":
            self.toggle_quick_settings()
        elif action == "wallpaper":
             WallpaperPicker(callback=self.set_wallpaper).open()
        elif action == "paste":
            self.paste_from_clipboard()
        else:
            self.ask_name(action)

    def paste_from_clipboard(self):
        try:
            content = Clipboard.paste()
            if content:
                # Tenta criar um arquivo com o conteúdo do clipboard
                timestamp = int(time.time())
                filename = f"Colado_{timestamp}.txt"
                path = os.path.join(self.current_path, filename)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                SofiaShell.show_toast("Conteúdo colado em novo arquivo.")
                self.refresh_desktop_items()
            else:
                SofiaShell.show_toast("Área de transferência vazia.")
        except Exception as e:
            SofiaShell.show_toast(f"Erro ao colar: {e}")

    def menu_callback(self, item_type):
        self.menu.dismiss()
        if item_type == "refresh": self.refresh_desktop_items()
        else: self.ask_name(item_type)

    def ask_name(self, item_type):
        if item_type == "app_universal":
            base_name = "NovoApp.appicon"
            content = json.dumps({
                "id_semantico": "novo_app",
                "nome_exibicao": "Meu App Universal",
                "android_package": "",
                "web_url": "",
                "motor_exec": "motor-bin",
                "ui_exec": "interface.py"
            }, indent=4)
        elif item_type == "app_web":
            base_name = "NovoSite.webicon"
            content = "URL=https://google.com"
        elif item_type == "folder":
            base_name = "Nova Pasta"
            content = ""
        else:
            base_name = "Novo Arquivo.txt"
            content = ""

        target_path = os.path.join(self.current_path, base_name)
        counter = 1
        while os.path.exists(target_path):
            name, ext = os.path.splitext(base_name)
            target_path = os.path.join(self.current_path, f"{name} {counter}{ext}")
            counter += 1
        try:
            if item_type == "folder" or item_type.endswith("appicon"):
                os.makedirs(target_path)
                if item_type.endswith("appicon"):
                    with open(os.path.join(target_path, "app.manifest"), 'w') as f: f.write(content)
            else:
                with open(target_path, 'w') as f: f.write(content)
            self.refresh_desktop_items()
        except Exception as e: print(f"Erro ao criar: {e}")

    def on_window_resize(self, window, width, height): self.refresh_dock_icons()

    def refresh_dock_icons(self, *args):
        dock_box = self.root.ids.dock_apps_box
        overflow_grid = self.root.ids.overflow_grid
        dock_box.clear_widgets(); overflow_grid.clear_widgets()

        total_width = Window.width - dp(20)
        reserved_space = dp(44 + 65 + 44 + 60) # Espaço ocupado por Menu, Relógio, Configs
        available = total_width - reserved_space
        if available < 0: available = 0
        num_fitting = int(available / dp(46))

        for i, app_name in enumerate(self.pinned_apps):
            # Cria o ícone
            icon = DockIcon(icon_name=app_name)

            # --- CORREÇÃO: Adiciona ação de clique ---
            icon.bind(on_release=lambda x, n=app_name: self.on_dock_click(n))
            # -----------------------------------------

            if i < num_fitting: dock_box.add_widget(icon)
            else: overflow_grid.add_widget(icon)

    def on_dock_click(self, name):
        """Gerencia os cliques nos ícones fixos do Dock"""
        self.vibrate()

        if name == "folder":
            # Abre a Mesa (Gerenciador de Arquivos interno)
            self.navigate_to(self.get_mesa_path())

        elif name == "web":
            # Abre o navegador padrão do Android/PC
            webbrowser.open("https://google.com")

        else:
            SofiaShell.show_toast(f"App Dock: {name}")

    def get_theme_style(self): return self.theme_style_str

    def update_clock(self, dt):
        self.clock_time = time.strftime("%H:%M")
        self.clock_date = time.strftime("%A, %d %B")

    def update_battery(self, dt):
        if platform == 'android':
            try:
                BatteryManager = autoclass('android.os.BatteryManager')
                Context = autoclass('android.content.Context')
                activity = autoclass('org.kivy.android.PythonActivity').mActivity
                bm = activity.getSystemService(Context.BATTERY_SERVICE)
                level = bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY)
                self.battery_percent = f"{level}%"
            except:
                self.battery_percent = "N/A"
        else:
            self.battery_percent = "100%"

    def on_dock_swipe(self, instance, touch):
        if self.root.ids.dock_pill.collide_point(*touch.pos):
            if self.swipe_start_y == 0: self.swipe_start_y = touch.y
            diff = touch.y - self.swipe_start_y
            has_overflow = len(self.root.ids.overflow_grid.children) > 0
            if diff > 30 and not self.is_drawer_open and has_overflow: self.anim_mini_drawer(True); self.swipe_start_y = 0
            elif diff < -30 and self.is_drawer_open: self.anim_mini_drawer(False); self.swipe_start_y = 0

    def on_dock_release(self, instance, touch): self.swipe_start_y = 0

    def anim_mini_drawer(self, open_it):
        drawer = self.root.ids.mini_drawer; dock = self.root.ids.dock_pill
        if open_it:
            drawer.opacity = 1; drawer.radius = [22, 22, 0, 0]; dock.radius = [0, 0, 22, 22]
            Animation(y=dp(75), d=0.3, t='out_back').start(drawer); self.is_drawer_open = True
        else:
            anim = Animation(y=dp(15), d=0.2, t='in_cubic')
            anim.bind(on_complete=lambda x, y: setattr(drawer, 'opacity', 0))
            anim.start(drawer); drawer.radius = [22, 22, 22, 22]; dock.radius = [22, 22, 22, 22]
            self.is_drawer_open = False

    def toggle_menu(self):
        self.vibrate()
        menu = self.root.ids.app_launcher
        if self.is_drawer_open: self.anim_mini_drawer(False)
        if menu.y > 0: Animation(y=-dp(600), d=0.3, t='in_cubic').start(menu)
        else:
            if self.is_panel_open: self.toggle_quick_settings()
            Animation(y=dp(85), d=0.4, t='out_back').start(menu)

    def toggle_quick_settings(self):
        self.vibrate()
        panel = self.root.ids.quick_panel; dock_clock = self.root.ids.dock_clock_card
        if self.root.ids.app_launcher.y > 0: self.toggle_menu()
        if self.is_drawer_open: self.anim_mini_drawer(False)
        if self.is_panel_open:
            Animation(y=-dp(800), opacity=0, d=0.3, t='in_cubic').start(panel)
            dock_clock.opacity = 1
            Animation(width=dp(65), opacity=1, d=0.3, t='out_back').start(dock_clock)
            self.is_panel_open = False
        else:
            panel.opacity = 1
            Animation(y=dp(80), d=0.4, t='out_back').start(panel)
            Animation(width=0, opacity=0, d=0.2, t='out_quad').start(dock_clock)
            self.is_panel_open = True

    # --- TOP SHELF LOGIC (NEW) ---
    def on_top_swipe(self, instance, touch):
        # Detecta puxada pra baixo na área superior
        if touch.dy < -15 and not self.is_shelf_open:
            self.toggle_top_shelf()

        # Detecta jogada pra cima se ela já estiver aberta
        elif touch.dy > 15 and self.is_shelf_open:
            self.toggle_top_shelf()

    def toggle_top_shelf(self):
        shelf = self.root.ids.top_shelf
        if self.is_shelf_open:
            Animation(y=Window.height, d=0.3, t='in_cubic').start(shelf)
            self.is_shelf_open = False
        else:
            Animation(y=Window.height - shelf.height, d=0.4, t='out_back').start(shelf)
            self.is_shelf_open = True
            self.vibrate()

    # --- BUBBLE NOTIFICATIONS (NEW) ---
    def spawn_bubble(self, text, icon_name="bell-ring-outline"):
        from kivymd.uix.card import MDCard
        from kivymd.uix.label import MDLabel, MDIcon

        bubble = MDCard(
            radius=[24,],
            md_bg_color=(0.1, 0.1, 0.1, 0.9),
            size_hint=(None, None),
            size=(dp(220), dp(50)),
            pos_hint={"center_x": 0.5},
            y=Window.height - dp(80), # Nasce altinha
            padding=[dp(15), dp(5), dp(15), dp(5)],
            spacing=dp(10),
            opacity=0,
            elevation=2
        )

        bubble.add_widget(MDIcon(icon=icon_name, theme_text_color="Custom", text_color=(1,1,1,1), pos_hint={"center_y": .5}))
        bubble.add_widget(MDLabel(text=text, theme_text_color="Custom", text_color=(1,1,1,1), halign="left", bold=True))

        self.root.add_widget(bubble)
        self.vibrate()

        # Desce dando oi, espera 3s e sobe sumindo
        anim_in = Animation(opacity=1, y=Window.height - dp(120), d=0.3, t='out_back')
        anim_out = Animation(opacity=0, y=Window.height, d=0.3, t='in_back')

        def limpar_bolha(*args):
            self.root.remove_widget(bubble)

        anim_out.bind(on_complete=limpar_bolha)

        anim_in.start(bubble)
        Clock.schedule_once(lambda dt: anim_out.start(bubble), 3.0)

    # --- FUNÇÕES DE HARDWARE (AÇÕES DA UI) ---
    def set_brightness(self, value):
        AndroidUtils.set_brightness(value)

    def set_volume(self, value):
        AndroidUtils.set_volume(value)

    def tog_wifi(self, widget):
        # Inverte estado desejado
        target_state = not self.is_wifi_on
        AndroidUtils.set_wifi_enabled(target_state)
        # Atualiza UI otimista (o loop de check corrigirá se falhar)
        self.is_wifi_on = target_state
        self.vibrate()

    def tog_bt(self, widget):
        target_state = not self.is_bt_on
        AndroidUtils.set_bluetooth_enabled(target_state)
        self.is_bt_on = target_state
        self.vibrate()

    def tog_airplane(self, widget):
        # Modo Avião é protegido. Abrimos o painel.
        self.vibrate()
        AndroidUtils.open_settings_panel(Settings.ACTION_AIRPLANE_MODE_SETTINGS)

    def tog_flash(self, widget):
        target_state = not self.is_flash_on
        AndroidUtils.toggle_torch(target_state)
        self.is_flash_on = target_state
        self.vibrate()

    def open_network_menu(self):
        """Abre o menu específico de Wi-Fi"""
        self.vibrate()
        WifiDialog().open()

    def open_android_settings(self):
        AndroidUtils.open_settings_panel(Settings.ACTION_SETTINGS)

if __name__ == '__main__':
    SophiaMobileApp().run()

# ==============================================================================
# 🤖 BUILDOZER.SPEC — SophiaOS / Mesa Mobile
# Alvos: Moto E7 Plus (Android 10/11) + Dispositivos Legados (Android 4.1+)
# Autor: Studio Hallel
# ATENÇÃO: Para Android 4.x use a seção [LEGADO] no final deste arquivo
# ==============================================================================

[app]

# --- IDENTIDADE ---
title = Sofia Mobile
package.name = sofiamobile
package.domain = org.studiohallel.sophia
# ⚠️ Corrigido: package.domain deve bater com o pkg usado no AdbWorker
# (era org.julio.sofia, o AdbWorker usa org.studiohallel.sophia)

# --- FONTES ---
source.dir = .
source.include_exts = py,png,jpg,jpeg,svg,kv,atlas,json,appicon,webicon,manifest,ttf,otf
# Adicionado: svg (ícones Colloid), ttf/otf (fontes), jpeg

source.include_patterns =
    assets/*,
    assets/**/*,
    mobile_icons/Colloid/**/*,
    mobile_icons/Colloid-Dark/**/*
# ⚠️ Inclui os ícones mas NÃO o colloid.zip

source.exclude_patterns =
    mobile_icons/*.zip,
    _fonte/*,
    **/__pycache__/*,
    **/*.pyc,
    **/*.pyo
# Zip e pasta _fonte ficam fora do APK — apenas arquivos fonte locais

# --- VERSÃO ---
version = 1.0

# --- REQUIREMENTS ---
# Ordem importa: dependências base primeiro
requirements =
    python3==3.11.6,
    kivy==2.3.0,
    kivymd==1.2.0,
    pillow==10.3.0,
    android,
    pyjnius,
    cython==0.29.33
# Notas:
# - kivymd versão explícita para evitar quebra de API
# - pyjnius explícito (estava implícito, pode falhar no build)
# - pillow 10.3.0 compatível com kivy 2.3.0
# - python3.11.6 é o mais estável com p4a atual

# --- ORIENTAÇÃO E DISPLAY ---
orientation = portrait
fullscreen = 1
android.wakelock = False

# --- PERMISSÕES ---
# Agrupadas por função para facilitar manutenção
android.permissions =
    # Armazenamento (ícones, apps, configurações)
    READ_EXTERNAL_STORAGE,
    WRITE_EXTERNAL_STORAGE,
    MANAGE_EXTERNAL_STORAGE,

    # Hardware
    CAMERA,
    FLASHLIGHT,
    VIBRATE,
    MODIFY_AUDIO_SETTINGS,
    RECORD_AUDIO,

    # Rede
    ACCESS_WIFI_STATE,
    CHANGE_WIFI_STATE,
    ACCESS_NETWORK_STATE,
    CHANGE_NETWORK_STATE,
    INTERNET,

    # Bluetooth (dual-stack: legado + BLE moderno)
    BLUETOOTH,
    BLUETOOTH_ADMIN,
    BLUETOOTH_CONNECT,
    BLUETOOTH_SCAN,

    # Localização (obrigatório para scan WiFi no Android 9+)
    ACCESS_FINE_LOCATION,
    ACCESS_COARSE_LOCATION,
    ACCESS_BACKGROUND_LOCATION,

    # Sistema / Kernel Parasita
    KILL_BACKGROUND_PROCESSES,
    QUERY_ALL_PACKAGES,
    GET_TASKS,
    PACKAGE_USAGE_STATS,
    WRITE_SETTINGS,
    FOREGROUND_SERVICE,
    RECEIVE_BOOT_COMPLETED,
    SYSTEM_ALERT_WINDOW,
    REQUEST_INSTALL_PACKAGES

# --- APIs ANDROID ---
# ✅ MOTO E7 PLUS (Android 10 = API 29)
android.api = 33
# Target 33 garante compatibilidade com Play Store e comportamento moderno

# ✅ LEGADOS (Android 4.1 = API 16, KitKat 4.4 = API 19)
# ⚠️ minapi 21 (seu valor anterior) EXCLUI Android 4.x completamente!
# API 16 = Android 4.1 Jelly Bean (mínimo seguro para Kivy)
android.minapi = 16

# --- NDK / SDK ---
android.ndk = 25b
android.sdk = 34
android.ndk_api = 16
# ndk_api deve bater com minapi para compilar libs nativas compatíveis

android.skip_update = False
android.accept_sdk_license = True

# --- ARQUITETURAS ---
# ✅ armeabi-v7a  → Android 4.x e Moto E7 Plus (compatibilidade)
# ✅ arm64-v8a    → Moto E7 Plus nativo (Snapdragon 460 é 64-bit)
# Buildozer gera um APK "fat" com as duas ABIs
android.archs = armeabi-v7a, arm64-v8a
# 💡 Para APKs separados (menor tamanho), comente a linha acima
# e use gradle splits — mas fat APK é mais simples para distribuição direta

# --- ENTRY POINT ---
android.entrypoint = org.kivy.android.PythonActivity
android.apptheme = "@android:style/Theme.NoTitleBar"

# --- FEATURES DECLARADAS ---
# Necessário para acesso a hardware específico
android.manifest.features =
    android.hardware.camera,
    android.hardware.camera.autofocus,
    android.hardware.wifi,
    android.hardware.bluetooth

# --- SERVIÇO FOREGROUND (Kernel Parasita persistente) ---
# Mantém o processo vivo mesmo com a tela desligada
android.foreground_service = True
# Nome do serviço que aparece na notificação persistente
android.foreground_service_type = dataSync

# --- META-DATA (importante para launcher behavior) ---
# Define como launcher padrão (essencial para o conceito parasita)
android.manifest.intent_filters =
    <intent-filter>
        <action android:name="android.intent.action.MAIN" />
        <category android:name="android.intent.category.LAUNCHER" />
        <category android:name="android.intent.category.HOME" />
        <category android:name="android.intent.category.DEFAULT" />
    </intent-filter>
# ⬆️ HOME + DEFAULT transforma o app em LAUNCHER PADRÃO
# O Android pergunta "qual app usar como home?" — usuário escolhe Sofia

# --- BACKUP ---
android.allow_backup = True
android.backup_rules = @xml/backup_rules

# --- ICONE E PRESPLASH ---
# Descomente e coloque os arquivos em assets/ quando tiver:
# icon.filename = %(source.dir)s/assets/icon.png
# presplash.filename = %(source.dir)s/assets/presplash.png
# presplash.lottie_animation = False

# --- GRADLE EXTRAS (compatibilidade legado) ---
# Aumenta heap do compilador para builds grandes
android.gradle_dependencies =
    androidx.core:core:1.9.0,
    androidx.appcompat:appcompat:1.6.1

# Configurações extras de compilação para suporte legado
android.add_gradle_repositories = google(), mavenCentral()

p4a.branch = develop
# 'develop' em vez de 'master' — tem melhor suporte a Python 3.11 e NDK 25

# ==============================================================================
# [buildozer]
# ==============================================================================

[buildozer]
log_level = 2
warn_on_root = 0
# warn_on_root = 0 para não travar em ambientes CI/Docker rodando como root

# ==============================================================================
# 📋 NOTAS DE BUILD
# ==============================================================================
#
# PROBLEMA CONHECIDO — Android 4.x + camera2:
#   main.py usa android.hardware.camera2.CameraManager (API 21+)
#   Em Android 4.x isso crasha. Solução: substituir por android.hardware.Camera
#   (a versão legada). Podemos fazer isso juntos.
#
# DOIS APKs vs FAT APK:
#   Fat APK (configuração atual): ~20-30MB maior mas funciona em tudo
#   APKs separados: armeabi-v7a para gaveta, arm64-v8a para Moto E7 Plus
#   Para gerar separados: android.archs = armeabi-v7a (build 1)
#                         android.archs = arm64-v8a   (build 2)
#
# MINAPI 16 vs MINAPI 21:
#   API 16 = Android 4.1+ ✅ (gaveta phones)
#   API 19 = Android 4.4+ ✅ (mais seguro, KitKat é o mais comum nos legados)
#   API 21 = Android 5.0+ ❌ (exclui todo Android 4.x)
#   Se quiser ser conservador sem perder muito: use minapi = 19
#
# PERMISSÕES NOVAS vs LEGADO:
#   BLUETOOTH_CONNECT / BLUETOOTH_SCAN só existem em API 31+
#   Em legados são ignoradas — o Android usa BLUETOOTH/BLUETOOTH_ADMIN
#   Declarar as duas famílias é a prática correta (dual-stack)
#
# ==============================================================================

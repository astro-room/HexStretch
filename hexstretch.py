import sys
import os
import getpass
import json
import math
import struct
import wave
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QWidget, QMainWindow, QSystemTrayIcon, QMenu, QDialog,
    QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QCheckBox, QPushButton,
    QFrame, QGraphicsDropShadowEffect, QStackedWidget, QButtonGroup
)
from PySide6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QParallelAnimationGroup, QVariantAnimation,
    QEasingCurve, QPoint, QPointF, QRectF, Signal
)
from PySide6.QtGui import (
    QIcon, QPixmap, QImage, QPainter, QColor, QFont, QFontDatabase, QPen, QBrush,
    QLinearGradient, QRadialGradient, QPolygonF, QPainterPath, QPalette
)

from PySide6.QtNetwork import QLocalServer, QLocalSocket

try:
    import winsound
except ImportError:
    winsound = None

try:
    import winreg
except ImportError:
    winreg = None

APP_NAME = "HexStretch"
DATA_DIR = Path.home() / ".hexstretch"
DATA_FILE = DATA_DIR / "state_v2.json"
CHIME_FILE = DATA_DIR / "hextech_chime.wav"
# Character cut-outs, card background and the Persian font — swap the files in assets/ to re-skin
ASSET_DIR = Path(__file__).resolve().parent / "assets"

EXERCISES = [
    {
        "id": "thoracic_ext",
        "char": "vi",
        "theme_color": "#FF2A6D",
        "accent_color": "#C89B3C",
        "duration_sec": 40,
        "title": {"en": "Thoracic Extension", "fa": "حرکت ضد قوز"},
        "dose": {"en": "10 reps • 2s hold", "fa": "۱۰ بار، هر بار ۲ ثانیه نگه دار"},
        "quote": {
            "en": "\"Drop the hunch, Cupcake. Shoulders back before I straighten 'em myself.\"",
            "fa": "«قوز نکن کاپ‌کیک! شونه‌ها عقب، قبل از اینکه خودم صافشون کنم.»",
        },
        "summary": {
            "en": "Hands behind your head, arch your upper back over the chair and open the elbows wide.",
            "fa": "دستاتو پشت سرت قفل کن، بالای کمرتو روی پشتی صندلی بده عقب و آرنج‌ها رو باز کن.",
        },
        "how_to": {
            "en": "1. Sit tall against the back of your chair.\n2. Clasp both hands behind your head.\n"
                  "3. Inhale and arch your upper/mid back over the backrest.\n"
                  "4. Squeeze your shoulder blades for 2 seconds, then return. (Counteracts thoracic kyphosis.)",
            "fa": "۱. صاف بشین و به پشتی صندلی تکیه بده.\n۲. دستاتو پشت سرت قفل کن.\n"
                  "۳. یه نفس عمیق بکش و بالای کمرتو روی لبه‌ی پشتی بده عقب.\n"
                  "۴. ۲ ثانیه کتف‌هاتو به هم فشار بده و برگرد. (این حرکت جلوی قوز پشت رو می‌گیره)",
        },
    },
    {
        "id": "chin_tucks",
        "char": "caitlyn",
        "theme_color": "#00D2FF",
        "accent_color": "#D4AF37",
        "duration_sec": 45,
        "title": {"en": "Chin Tucks", "fa": "چین تاک"},
        "dose": {"en": "10 reps • 3s hold", "fa": "۱۰ بار، هر بار ۳ ثانیه نگه دار"},
        "quote": {
            "en": "\"Precision starts with alignment. Eyes on the horizon, head straight back.\"",
            "fa": "«دقت از صاف بودن شروع می‌شه. چشم به افق، سر مستقیم عقب.»",
        },
        "summary": {
            "en": "Glide your head straight back (McKenzie retraction) to unload the neck discs.",
            "fa": "سرتو صاف ببر عقب (حرکت مک‌کنزی) تا فشار از روی دیسک‌های گردن برداشته بشه.",
        },
        "how_to": {
            "en": "1. Look straight ahead — don't tilt your chin up or down.\n"
                  "2. Pull your head straight back on a horizontal rail (make a double chin).\n"
                  "3. Hold 3 seconds at end-range until the base of your skull stretches.\n4. Repeat 10 times.",
            "fa": "۱. مستقیم روبه‌رو رو نگاه کن؛ چونه‌تو بالا یا پایین نبر.\n"
                  "۲. سرتو روی یه خط صاف ببر عقب، انگار داری غبغب درست می‌کنی.\n"
                  "۳. ۳ ثانیه نگه دار تا پشت گردنت کشیده بشه.\n۴. ۱۰ بار تکرار کن.",
        },
    },
    {
        "id": "hydration",
        "char": "jinx",
        "theme_color": "#05D5FF",
        "accent_color": "#FF007F",
        "duration_sec": 20,
        "title": {"en": "Hydration Check", "fa": "وقت آب خوردن"},
        "dose": {"en": "250 ml • one full glass", "fa": "یه لیوان آب (۲۵۰ سی‌سی)"},
        "quote": {
            "en": "\"Drink your water right now! Or is your brain running on Shimmer fumes?!\"",
            "fa": "«همین الان آبتو بخور! یا مغزت با بخار شیمر کار می‌کنه؟!»",
        },
        "summary": {
            "en": "Drink a full glass of water now to keep your spinal discs and focus sharp.",
            "fa": "همین الان یه لیوان آب بخور تا هم دیسک‌های کمرت سرحال بمونن هم تمرکزت.",
        },
        "how_to": {
            "en": "1. Grab your bottle or glass and drink ~250 ml of water.\n"
                  "2. Intervertebral discs rehydrate through movement and overall fluid balance.\n"
                  "3. Target 2.5 to 3.0 litres across the day.",
            "fa": "۱. لیوان یا بطری‌تو بردار و حدود ۲۵۰ سی‌سی آب بخور.\n"
                  "۲. دیسک‌های ستون فقرات با حرکت و آب کافی بدن تغذیه می‌شن.\n"
                  "۳. هدف روزانه: ۲٫۵ تا ۳ لیتر.",
        },
    },
    {
        "id": "eye_reset",
        "char": "ekko",
        "theme_color": "#00F59B",
        "accent_color": "#C89B3C",
        "duration_sec": 20,
        "title": {"en": "20-20-20 Eye Reset", "fa": "قانون ۲۰-۲۰-۲۰ چشم"},
        "dose": {"en": "20 sec • look 6 m away", "fa": "۲۰ ثانیه، به ۶ متر دورتر نگاه کن"},
        "quote": {
            "en": "\"Rewind your eyes for 20 seconds. Screen lock is a trap.\"",
            "fa": "«چشماتو ۲۰ ثانیه ریوایند کن. زل زدن به مانیتور یه تله‌ست.»",
        },
        "summary": {
            "en": "Look at something at least 6 m (20 ft) away and blink slowly 10 times.",
            "fa": "به یه چیزی که حداقل ۶ متر دورتره نگاه کن و ۱۰ بار آروم پلک بزن.",
        },
        "how_to": {
            "en": "1. Look away from the monitor toward an object 6+ metres away.\n"
                  "2. Blink slowly and completely 10 times to recoat the eye.\n"
                  "3. Let your focusing muscles fully relax.",
            "fa": "۱. چشمتو از مانیتور بگیر و به یه چیز دور (۶ متر یا بیشتر) نگاه کن.\n"
                  "۲. ۱۰ بار آروم و کامل پلک بزن تا چشمت خیس بشه.\n"
                  "۳. بذار عضلات چشمت کامل ریلکس بشن.",
        },
    },
    {
        "id": "upper_trap",
        "char": "viktor",
        "theme_color": "#FFB800",
        "accent_color": "#A855F7",
        "duration_sec": 40,
        "title": {"en": "Neck & Upper Trap Stretch", "fa": "کشش گردن و شونه"},
        "dose": {"en": "20 sec each side", "fa": "هر طرف ۲۰ ثانیه"},
        "quote": {
            "en": "\"Relieve structural tension in the cervical frame before it calcifies.\"",
            "fa": "«گرفتگی گردنت رو آزاد کن، قبل از اینکه خشک بشه.»",
        },
        "summary": {
            "en": "Anchor one hand under the chair and tilt your ear toward the opposite shoulder.",
            "fa": "یه دستتو زیر صندلی گیر بده و گوشتو آروم به سمت شونه‌ی مخالف خم کن.",
        },
        "how_to": {
            "en": "1. Sit on your right hand (or hold the chair seat) to anchor the right shoulder down.\n"
                  "2. Gently tilt your left ear toward your left shoulder.\n"
                  "3. Hold 20 seconds, then switch sides.",
            "fa": "۱. روی دست راستت بشین (یا لبه‌ی صندلی رو بگیر) تا شونه‌ی راستت پایین بمونه.\n"
                  "۲. آروم گوش چپتو به سمت شونه‌ی چپ خم کن.\n"
                  "۳. ۲۰ ثانیه نگه دار، بعد طرف دیگه.",
        },
    },
    {
        "id": "micro_walk",
        "char": "ambessa",
        "theme_color": "#EF4444",
        "accent_color": "#C89B3C",
        "duration_sec": 90,
        "title": {"en": "Walk & Hip Stretch", "fa": "قدم زدن و کشش لگن"},
        "dose": {"en": "90 sec walk + lunges", "fa": "۹۰ ثانیه قدم زدن + لانج"},
        "quote": {
            "en": "\"A commander does not rust in a chair. Stand, march, and open your stride.\"",
            "fa": "«فرمانده پشت میز زنگ نمی‌زنه. پاشو، قدم بزن، گام‌هاتو باز کن.»",
        },
        "summary": {
            "en": "Stand up, walk around the room, then do 2 hip-flexor lunges per leg.",
            "fa": "پاشو، یه دور تو اتاق قدم بزن و بعد برای هر پا ۲ تا لانج برو.",
        },
        "how_to": {
            "en": "1. Stand up from your desk now.\n"
                  "2. Walk around the room for 60 seconds to wake up the calf muscle pump.\n"
                  "3. Step into a half-lunge and push your hips forward for 15 seconds per side "
                  "to release the hip flexors (iliopsoas).",
            "fa": "۱. همین الان از پشت میز پاشو.\n"
                  "۲. ۶۰ ثانیه تو اتاق راه برو تا خون پاهات به جریان بیفته.\n"
                  "۳. برو تو حالت نیم‌لانج، لگنتو بده جلو و هر طرف ۱۵ ثانیه نگه دار تا عضلات جلوی لگن (سوآس) باز بشن.",
        },
    },
]

# How each cut-out sits in its card: (zoom relative to the character area width,
# horizontal shift as a fraction of that width, vertical shift as a fraction of card height)
CHAR_FIT = {
    "vi":      {"vertical": (1.00, 0.00, 0.00), "side": (1.10, 0.00, 0.00)},
    "caitlyn": {"vertical": (1.00, 0.02, 0.00), "side": (1.05, 0.00, 0.00)},
    "jinx":    {"vertical": (1.10, 0.00, 0.00), "side": (1.15, 0.00, 0.00)},
    "ekko":    {"vertical": (1.00, 0.00, 0.00), "side": (1.00, 0.00, 0.00)},
    "viktor":  {"vertical": (1.00, 0.00, 0.00), "side": (1.00, 0.00, 0.00)},
    "ambessa": {"vertical": (1.00, 0.00, 0.00), "side": (1.05, 0.00, 0.00)},
}

# Each dashboard card shows a different slice of the shared background art
BG_FOCI = [(0.15, 0.20), (0.55, 0.30), (0.90, 0.20), (0.10, 0.75), (0.50, 0.60), (0.90, 0.80)]

TR = {
    "en": {
        "window_title": "HexStretch",
        "subtitle": "Stretch reminders that live in your system tray. Click a card to try it.",
        "next": "⚡  Next stretch",
        "settings": "Settings",
        "back": "←  Back",
        "today": "{n} today",
        "start": "⚡ Start",
        "done": "✔ Done",
        "snooze": "Snooze 10m",
        "skip": "Skip",
        "guide": "Guide",
        "start_now": "⚡ Start now",
        "close": "Close",
        "mute": "Mute / unmute sound",
        "dismiss": "Dismiss (keeps running in the background)",
        "completed": "✔ Nice! ({n} today)",
        "snoozed": "🌙 See you in 10 minutes",
        "how_to": "How to do it",
        "s_reminders": "Pop-up reminders",
        "s_reminders_hint": "Turn off while gaming or focusing",
        "s_sound": "Sound",
        "s_sound_hint": "Soft chime when a reminder appears",
        "s_startup": "Start with Windows",
        "s_startup_hint": "Launch quietly in the tray at sign-in",
        "s_stretch": "Stretch reminder every",
        "s_water": "Water reminder every",
        "minutes": " min",
        "s_language": "Language",
        "quit": "✖  Quit HexStretch",
        "tray_open": "⚙  Open HexStretch",
        "tray_next": "⚡  Next stretch now",
        "tray_water": "💧  Water reminder now",
        "tray_notif_on": "🔔  Reminders: ON",
        "tray_notif_off": "🔕  Reminders: OFF",
        "tray_sound_on": "🔊  Sound: ON",
        "tray_sound_off": "🔇  Sound: muted",
        "tray_quit": "✖  Quit",
        "tray_tip_on": "HexStretch — active",
        "tray_tip_off": "HexStretch — paused",
    },
    "fa": {
        "window_title": "HexStretch",
        "subtitle": "یادآور حرکات کششی که کنار ساعت ویندوز (System Tray) می‌مونه. برای امتحان، روی هر کارت بزن.",
        "next": "⚡  حرکت بعدی",
        "settings": "تنظیمات",
        "back": "→  برگشت",
        "today": "امروز {n}",
        "start": "⚡ شروع",
        "done": "✔ تموم شد",
        "snooze": "۱۰ دقیقه دیگه",
        "skip": "رد کن",
        "guide": "راهنما",
        "start_now": "⚡ همین الان شروع کن",
        "close": "بستن",
        "mute": "صدا: قطع / وصل",
        "dismiss": "بستن (برنامه پشت صحنه روشن می‌مونه)",
        "completed": "✔ ایول! (امروز {n})",
        "snoozed": "🌙 ۱۰ دقیقه دیگه یادت می‌ندازم",
        "how_to": "چطوری انجامش بدم؟",
        "s_reminders": "پاپ‌آپ‌های یادآور",
        "s_reminders_hint": "موقع گیم یا کارهای فوکوسی خاموشش کن",
        "s_sound": "صدا",
        "s_sound_hint": "یه صدای آروم موقع باز شدن پاپ‌آپ",
        "s_startup": "اجرا با روشن شدن ویندوز",
        "s_startup_hint": "بی‌سروصدا کنار ساعت ویندوز باز می‌شه",
        "s_stretch": "یادآور حرکت کششی هر",
        "s_water": "یادآور آب هر",
        "minutes": " دقیقه",
        "s_language": "زبان",
        "quit": "✖  بستن کامل برنامه",
        "tray_open": "⚙  باز کردن HexStretch",
        "tray_next": "⚡  حرکت بعدی، همین الان",
        "tray_water": "💧  یادآور آب، همین الان",
        "tray_notif_on": "🔔  یادآورها: روشن",
        "tray_notif_off": "🔕  یادآورها: خاموش",
        "tray_sound_on": "🔊  صدا: روشن",
        "tray_sound_off": "🔇  صدا: قطع",
        "tray_quit": "✖  خروج",
        "tray_tip_on": "HexStretch — فعال",
        "tray_tip_off": "HexStretch — متوقف",
    },
}

MS_PER_MIN = 60 * 1000
SNOOZE_MINUTES = 10

FONT_FAMILY = {"en": "Segoe UI", "fa": "Vazirmatn"}
FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def digits(value, lang: str) -> str:
    return str(value).translate(FA_DIGITS) if lang == "fa" else str(value)


def tr(key: str, lang: str, **kw) -> str:
    text = TR.get(lang, TR["en"]).get(key, TR["en"].get(key, key))
    if kw:
        text = text.format(**{k: digits(v, lang) for k, v in kw.items()})
    return text


def load_fonts():
    families = set()
    for f in sorted(ASSET_DIR.glob("Vazirmatn-*.ttf")):
        fid = QFontDatabase.addApplicationFont(str(f))
        if fid >= 0:
            families.update(QFontDatabase.applicationFontFamilies(fid))
    if "Vazirmatn" not in families:
        FONT_FAMILY["fa"] = "Tahoma"


def base_qss(lang: str) -> str:
    fam = FONT_FAMILY.get(lang, "Segoe UI")
    return f"""
        * {{ font-family: "{fam}"; }}
        QToolTip {{ background-color: #0B1120; color: #F8FAFC; border: 1px solid #C89B3C; padding: 4px 8px; }}
        QLabel {{ background: transparent; color: #E2E8F0; }}
        QLabel#H1 {{ color: #C89B3C; font-size: 24px; font-weight: 800; letter-spacing: 3px; }}
        QLabel#Sub {{ color: #94A3B8; font-size: 12.5px; }}
        QLabel#TileTitle {{ color: #F8FAFC; font-size: 15px; font-weight: 800; }}
        QLabel#PopTitle {{ color: #F8FAFC; font-size: 18px; font-weight: 800; }}
        QLabel#Dose {{ font-size: 12.5px; font-weight: 700; }}
        QLabel#Pill {{
            background-color: rgba(9, 13, 22, 215); color: #C89B3C; border: 1px solid #334155;
            border-radius: 9px; padding: 1px 9px; font-size: 11px; font-weight: 700;
        }}
        QLabel#Timer {{ color: #F8FAFC; font-size: 17px; font-weight: 800; }}
        QLabel#Banner {{ font-size: 13px; font-weight: 700; padding: 6px 14px; border-radius: 8px; }}
        QFrame#GuideBox {{ background-color: rgba(9, 13, 22, 225); border: 1px solid #26334D; border-radius: 10px; }}
        QLabel#GuideHead {{ color: #C89B3C; font-size: 12px; font-weight: 800; }}
        QLabel#Quote {{ color: #94A3B8; font-size: 12px; }}
        QLabel#Summary {{ color: #F1F5F9; font-size: 12.5px; font-weight: 600; }}
        QLabel#Steps {{ color: #CBD5E1; font-size: 12px; }}
        QPushButton {{ font-size: 12.5px; }}
        QPushButton#IconBtn {{
            background-color: rgba(15, 23, 42, 215); color: #CBD5E1; border: 1px solid #334155;
            border-radius: 8px; font-size: 12px; font-weight: 800; padding: 0;
            min-width: 28px; max-width: 28px; min-height: 28px; max-height: 28px;
        }}
        QPushButton#IconBtn:hover {{ border-color: #C89B3C; color: #FDE047; background-color: #1E293B; }}
        QPushButton#IconBtn:disabled {{ color: #334155; border-color: #1E293B; }}
        QPushButton#Ghost {{
            background-color: rgba(15, 23, 42, 220); color: #E2E8F0; border: 1px solid #475569;
            border-radius: 8px; padding: 0 16px; min-height: 34px; font-weight: 600;
        }}
        QPushButton#Ghost:hover {{ border-color: #C89B3C; color: #FDE047; }}
        QPushButton#Gold {{
            background-color: #C89B3C; color: #090D16; border: none; border-radius: 9px;
            padding: 0 20px; min-height: 38px; font-size: 13.5px; font-weight: 800;
        }}
        QPushButton#Gold:hover {{ background-color: #FDE047; }}
        QPushButton#Danger {{
            background-color: rgba(30, 41, 59, 220); color: #F87171; border: 1px solid #7F1D1D;
            border-radius: 8px; padding: 0 16px; min-height: 34px; font-weight: 700;
        }}
        QPushButton#Danger:hover {{ background-color: #7F1D1D; color: #FFFFFF; }}
        QFrame#Panel {{ background-color: rgba(11, 17, 32, 232); border: 1px solid #26334D; border-radius: 16px; }}
        QLabel#PanelTitle {{ color: #C89B3C; font-size: 20px; font-weight: 800; }}
        QLabel#RowLabel {{ color: #F1F5F9; font-size: 13.5px; font-weight: 700; }}
        QLabel#RowHint {{ color: #64748B; font-size: 11.5px; }}
        QFrame#Divider {{ background-color: #1E293B; max-height: 1px; min-height: 1px; border: none; }}
        QLabel#StepValue {{
            background-color: #070A12; color: #05D5FF; border: 1px solid #C89B3C; border-radius: 6px;
            padding: 5px 10px; font-size: 13px; font-weight: 700;
        }}
        QPushButton#Seg {{
            background-color: #0F172A; color: #CBD5E1; border: 1px solid #334155;
            padding: 0 18px; min-height: 32px; font-size: 13px; font-weight: 700; border-radius: 8px;
        }}
        QPushButton#Seg:checked {{ background-color: #C89B3C; color: #090D16; border-color: #C89B3C; }}
    """


# ---------------------------------------------------------------------------
# SOUND & STARTUP HELPERS
# ---------------------------------------------------------------------------
def ensure_chime_wav():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if CHIME_FILE.exists():
        return str(CHIME_FILE)
    sample_rate = 44100
    duration = 0.45
    num_samples = int(sample_rate * duration)
    with wave.open(str(CHIME_FILE), "w") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for i in range(num_samples):
            t = i / sample_rate
            attack = min(1.0, t / 0.02)
            decay = math.exp(-6.0 * t)
            env = attack * decay
            val = (
                0.55 * math.sin(2 * math.pi * 587.33 * t) +
                0.35 * math.sin(2 * math.pi * 880.00 * t) +
                0.10 * math.sin(2 * math.pi * 1174.66 * t)
            )
            sample = int(val * env * 8000)
            wav_file.writeframesraw(struct.pack("<h", max(-32767, min(32767, sample))))
    return str(CHIME_FILE)


def play_soft_chime(muted=False):
    if muted:
        return
    wav_path = ensure_chime_wav()
    if winsound and os.path.exists(wav_path):
        winsound.PlaySound(wav_path, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)


def get_startup_command():
    exe = sys.executable
    if exe.lower().endswith("python.exe"):
        pythonw = exe[:-10] + "pythonw.exe"
        if os.path.exists(pythonw):
            exe = pythonw
    script_path = os.path.abspath(sys.argv[0])
    return f'"{exe}" "{script_path}" --minimized'


def is_startup_enabled():
    if not winreg:
        return False
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
        val, _ = winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return bool(val)
    except Exception:
        return False


def set_startup_enabled(enable: bool):
    if not winreg:
        return False
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
        if enable:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, get_startup_command())
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# ARTWORK HELPERS
# ---------------------------------------------------------------------------
_image_cache = {}
_flat_top = {}
_ALPHA_SOLID = bytes(0 if v <= 24 else 1 for v in range(256))


def _trim_cutout(img: QImage):
    """Crop transparent margins off a cut-out and report whether its top is cut flat
    (the photo's frame sliced through the head). Lets users drop in any transparent PNG."""
    img = img.convertToFormat(QImage.Format_ARGB32)
    w, h, bpl = img.width(), img.height(), img.bytesPerLine()
    data = bytes(img.constBits())
    top = bottom = None
    left, right = w, -1
    top_row = b""
    for y in range(h):
        row = data[y * bpl + 3: y * bpl + 4 * w: 4].translate(_ALPHA_SOLID)   # alpha byte of each pixel
        first = row.find(1)
        if first < 0:
            continue
        if top is None:
            top, top_row = y, row
        bottom = y
        left = min(left, first)
        right = max(right, row.rfind(1))
    if top is None:
        return img, False
    cropped = img.copy(left, top, right - left + 1, bottom - top + 1)
    flat = top_row.count(1) > 0.12 * cropped.width()
    return cropped, flat


def asset_image(name: str) -> QImage:
    if name not in _image_cache:
        path = ASSET_DIR / name
        img = QImage(str(path)) if path.exists() else QImage()
        if not img.isNull():
            if name.endswith(".png") and img.hasAlphaChannel():
                img, _flat_top[name] = _trim_cutout(img)
            img = img.convertToFormat(QImage.Format_ARGB32_Premultiplied)
        _image_cache[name] = img
    return _image_cache[name]


def is_flat_top(name: str) -> bool:
    """True when the head touches the photo's top edge: such a character sits flush with the
    card's top border instead of breaking out of it (a flat-topped head looks wrong outside)."""
    asset_image(name)
    return _flat_top.get(name, False)


def cover_pixmap(img: QImage, w: float, h: float, focus=(0.5, 0.5), zoom=1.0, dpr=1.0) -> QPixmap:
    """Scale an image to fill w x h (like CSS background-size: cover), cropping around `focus`."""
    W, H = max(1, round(w * dpr)), max(1, round(h * dpr))
    s = img.scaled(round(W * zoom), round(H * zoom), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    x = int((s.width() - W) * focus[0])
    y = int((s.height() - H) * focus[1])
    pm = QPixmap.fromImage(s.copy(x, y, W, H))
    pm.setDevicePixelRatio(dpr)
    return pm


def make_outline(src: QImage, color: QColor, radius: float):
    """Solid-colour silhouette of `src`, grown by `radius` px — drawn behind the cut-out it becomes its border."""
    pad = int(math.ceil(radius)) + 1
    out = QImage(src.width() + 2 * pad, src.height() + 2 * pad, QImage.Format_ARGB32_Premultiplied)
    out.fill(Qt.transparent)
    p = QPainter(out)
    for i in range(16):
        a = 2 * math.pi * i / 16
        p.drawImage(QPointF(pad + radius * math.cos(a), pad + radius * math.sin(a)), src)
    p.setCompositionMode(QPainter.CompositionMode_SourceIn)
    p.fillRect(out.rect(), color)
    p.end()
    return out, pad


# ---------------------------------------------------------------------------
# STATE MANAGER
# ---------------------------------------------------------------------------
class StateManager:
    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.data = {
            "notifications_enabled": True,
            "muted": False,
            "interval_minutes": 20,
            "water_interval_minutes": 60,
            "run_on_startup": is_startup_enabled(),
            "language": "fa",
            "last_date": datetime.now().strftime("%Y-%m-%d"),
            "counts_today": {},
            "queue_index": 0
        }
        self.load()

    @property
    def lang(self) -> str:
        return self.data.get("language", "fa") if self.data.get("language") in TR else "en"

    def load(self):
        if DATA_FILE.exists():
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    self.data.update(loaded)
            except Exception:
                pass
        self._sanitize()
        self._roll_day()
        self.data["run_on_startup"] = is_startup_enabled()
        self.save()

    def _sanitize(self):
        """A hand-edited or damaged state file must not crash the app or set absurd intervals."""
        d = self.data

        def clamp_int(key, lo, hi, default):
            try:
                v = int(d.get(key, default))
            except (TypeError, ValueError):
                v = default
            d[key] = max(lo, min(hi, v))

        clamp_int("interval_minutes", 1, 120, 20)
        clamp_int("water_interval_minutes", 15, 180, 60)
        clamp_int("queue_index", 0, 1000, 0)
        for key, default in (("notifications_enabled", True), ("muted", False)):
            if not isinstance(d.get(key), bool):
                d[key] = default
        if d.get("language") not in TR:
            d["language"] = "fa"
        if not isinstance(d.get("last_date"), str):
            d["last_date"] = ""
        counts = d.get("counts_today")
        known = {e["id"] for e in EXERCISES}
        d["counts_today"] = {
            k: v for k, v in counts.items()
            if k in known and isinstance(v, int) and not isinstance(v, bool) and 0 <= v < 10000
        } if isinstance(counts, dict) else {}

    def save(self):
        # Write to a temp file and swap it in, so a crash mid-write can't leave a broken file
        tmp = DATA_FILE.with_suffix(".tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            os.replace(tmp, DATA_FILE)
        except Exception:
            pass

    def _roll_day(self):
        today = datetime.now().strftime("%Y-%m-%d")
        if self.data.get("last_date") != today:
            self.data["last_date"] = today
            self.data["counts_today"] = {}
            return True
        return False

    def get_count(self, ex_id: str) -> int:
        if self._roll_day():
            self.save()
        return self.data["counts_today"].get(ex_id, 0)

    def increment_count(self, ex_id: str) -> int:
        c = self.get_count(ex_id) + 1
        self.data["counts_today"][ex_id] = c
        self.save()
        return c


# ---------------------------------------------------------------------------
# POP-OUT CARD — background art + a cut-out character that breaks through the top edge,
# with the card border continuing around the character's silhouette
# ---------------------------------------------------------------------------
class PopoutCard(QWidget):
    def __init__(self, mode="vertical", overflow=46, radius=18, parent=None):
        super().__init__(parent)
        self.mode = mode            # "vertical": character fills the card, text at the bottom
        self.overflow = overflow    # "side": character in `char_slot`, text beside it
        self.radius = radius
        self.theme = QColor("#C89B3C")
        self.accent = QColor("#C89B3C")
        self.char_name = None
        self.char_slot = None
        self.bg_focus = (0.5, 0.35)
        self.bg_zoom = 1.0
        self.lift = 0.0       # 0..1 hover animation
        self.progress = 0.0   # 0..1 countdown bar
        self._bg_key = None
        self._bg_pix = QPixmap()
        self._char_key = None
        self._char = None

    def set_exercise(self, ex: dict):
        self.theme = QColor(ex["theme_color"])
        self.accent = QColor(ex["accent_color"])
        self.char_name = ex["char"]
        self._char_key = None
        self.update()

    def set_progress(self, ratio: float):
        self.progress = max(0.0, min(1.0, ratio))
        self.update()

    def card_rect(self) -> QRectF:
        return QRectF(1.5, self.overflow + 1.5, self.width() - 3.0, self.height() - self.overflow - 3.0)

    def _char_area(self, card: QRectF) -> QRectF:
        if self.mode == "side" and self.char_slot is not None:
            g = self.char_slot.geometry()
            return QRectF(g.x(), 0, g.width(), card.bottom())
        return QRectF(card.left(), 0, card.width(), card.bottom())

    def _background(self, card: QRectF) -> QPixmap:
        img = asset_image("background.jpg")
        if img.isNull():
            return QPixmap()
        dpr = self.devicePixelRatioF()
        key = (round(card.width()), round(card.height()), dpr, self.bg_focus, self.bg_zoom)
        if key != self._bg_key:
            self._bg_pix = cover_pixmap(img, card.width(), card.height(), self.bg_focus, self.bg_zoom, dpr)
            self._bg_key = key
        return self._bg_pix

    def _character(self, card: QRectF):
        img = asset_image(f"{self.char_name}.png") if self.char_name else QImage()
        if img.isNull():
            return None
        flat = is_flat_top(f"{self.char_name}.png")
        area = self._char_area(card)
        zoom, dx, dy = CHAR_FIT.get(self.char_name, {}).get(self.mode, (1.0, 0.0, 0.0))
        if self.isRightToLeft():
            dx = -dx
        w = area.width() * zoom
        if flat:  # sits inside the card, so it must at least fill its height
            w = max(w, (card.height() + 2) * img.width() / img.height())
        h = w * img.height() / img.width()
        x = area.center().x() - w / 2 + dx * area.width()
        if flat:
            y = card.top() + 1.0 + dy * card.height()
        else:
            y = 8 + dy * card.height() - 6 * self.lift
        dpr = self.devicePixelRatioF()
        key = (round(w), round(h), dpr, self.theme.name())
        if key != self._char_key:
            scaled = img.scaled(max(1, round(w * dpr)), max(1, round(h * dpr)), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            outline, pad = make_outline(scaled, self.theme, 2.0 * dpr)
            scaled.setDevicePixelRatio(dpr)
            outline.setDevicePixelRatio(dpr)
            self._char = (scaled, outline, pad / dpr)
            self._char_key = key
        scaled, outline, pad = self._char
        return scaled, outline, pad, QPointF(x, y), area

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        card = self.card_rect()
        r = self.radius
        path = QPainterPath()
        path.addRoundedRect(card, r, r)
        inner = QPainterPath()
        inner.addRoundedRect(card.adjusted(1.2, 1.2, -1.2, -1.2), r - 1, r - 1)
        char = self._character(card)

        # 1. Background art, darkened, with a soft glow of the theme colour behind the character
        p.save()
        p.setClipPath(path)
        p.fillRect(card, QColor("#070A12"))
        bg = self._background(card)
        if not bg.isNull():
            p.drawPixmap(card.topLeft(), bg)
        p.fillRect(card, QColor(6, 8, 16, 150 if self.mode == "vertical" else 175))
        cx = char[4].center().x() if char else card.center().x()
        glow = QRadialGradient(cx, card.top() + card.height() * 0.30, max(card.width(), card.height()) * 0.55)
        g = QColor(self.theme)
        g.setAlpha(int(70 + 40 * self.lift))
        glow.setColorAt(0.0, g)
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.fillRect(card, glow)
        p.restore()

        # 2. Card border (theme colour along the top so it flows into the character outline)
        border = QLinearGradient(0, card.top(), 0, card.bottom())
        border.setColorAt(0.0, self.theme)
        border.setColorAt(0.55, self.accent)
        border.setColorAt(1.0, QColor(self.accent).darker(260))
        p.setPen(QPen(QBrush(border), 2.0 + 0.6 * self.lift))
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)

        # 3. Character: inside the card it is clipped by the card; above the top edge it breaks free,
        #    and its silhouette outline continues the border around it
        if char:
            scaled, outline, pad, pos, area = char
            above = QPainterPath()
            above.addRect(QRectF(card.left(), -20, card.width(), card.top() + 1.0 + 20))
            p.save()
            p.setClipPath(above)
            p.drawImage(pos - QPointF(pad, pad), outline)
            p.restore()
            p.save()
            p.setClipPath(inner.united(above))
            p.drawImage(pos, scaled)
            p.restore()

        # 4. Readability shade under the text + countdown bar
        p.save()
        p.setClipPath(inner)
        if self.mode == "vertical":
            shade = QLinearGradient(0, card.bottom(), 0, card.top() + card.height() * 0.38)
            shade.setColorAt(0.0, QColor(5, 7, 14, 250))
            shade.setColorAt(0.45, QColor(5, 7, 14, 200))
            shade.setColorAt(1.0, QColor(5, 7, 14, 0))
        else:
            area = char[4] if char else QRectF(card.left(), 0, 0, 0)
            rtl = self.isRightToLeft()
            edge = area.left() if rtl else area.right()
            sgn = -1 if rtl else 1
            shade = QLinearGradient(edge - sgn * 50, 0, edge + sgn * 40, 0)
            shade.setColorAt(0.0, QColor(5, 7, 14, 0))
            shade.setColorAt(1.0, QColor(5, 7, 14, 215))
        p.fillRect(card, shade)
        if self.progress > 0.0:
            bar_w = (card.width() - 2 * r) * self.progress
            x0 = card.right() - r - bar_w if self.isRightToLeft() else card.left() + r
            p.fillRect(QRectF(x0, card.bottom() - 5, bar_w, 3), self.theme)
        p.restore()


def make_icon_btn(text: str, slot) -> QPushButton:
    btn = QPushButton(text)
    btn.setObjectName("IconBtn")
    btn.setCursor(Qt.PointingHandCursor)
    btn.setFocusPolicy(Qt.NoFocus)
    btn.clicked.connect(slot)
    return btn


def theme_button_qss(theme_hex: str) -> str:
    return f"""
        QPushButton {{
            background-color: {theme_hex}; color: #090D16; border: none; border-radius: 8px;
            padding: 0 18px; min-height: 34px; font-size: 13px; font-weight: 800;
        }}
        QPushButton:hover {{ background-color: #FFFFFF; }}
    """


class GuideBox(QFrame):
    """The 'non-essential' text — quote, summary and step-by-step — shown only on demand."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("GuideBox")
        v = QVBoxLayout(self)
        v.setContentsMargins(12, 10, 12, 12)
        v.setSpacing(6)
        self.lbl_quote = QLabel()
        self.lbl_quote.setObjectName("Quote")
        self.lbl_summary = QLabel()
        self.lbl_summary.setObjectName("Summary")
        self.lbl_head = QLabel()
        self.lbl_head.setObjectName("GuideHead")
        self.lbl_steps = QLabel()
        self.lbl_steps.setObjectName("Steps")
        for lbl in (self.lbl_quote, self.lbl_summary, self.lbl_head, self.lbl_steps):
            lbl.setWordWrap(True)
            v.addWidget(lbl)

    def set_content(self, ex: dict, lang: str):
        self.lbl_quote.setText(ex["quote"][lang])
        f = self.lbl_quote.font()
        f.setItalic(lang == "en")
        self.lbl_quote.setFont(f)
        self.lbl_summary.setText(ex["summary"][lang])
        self.lbl_head.setText(tr("how_to", lang))
        self.lbl_steps.setText(ex["how_to"][lang])


# ---------------------------------------------------------------------------
# TOP-CENTER POP-UP
# ---------------------------------------------------------------------------
class ExercisePopup(QWidget):
    open_settings_requested = Signal()
    snooze_requested = Signal(object)
    state_updated = Signal()
    closed = Signal()

    POPUP_WIDTH = 600
    OVERFLOW = 48
    TOP_GAP = 6

    def __init__(self, state: StateManager):
        super().__init__()
        self.state = state
        self.current_exercise = EXERCISES[0]
        self.remaining_sec = 40
        self.total_sec = 40
        self._running = False
        self._hiding = False

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool |
            Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setFixedWidth(self.POPUP_WIDTH)

        self._build_ui()

        self.countdown_timer = QTimer(self)
        self.countdown_timer.timeout.connect(self._on_tick)

        # Slide a short distance + fade, so the window never has to sit above the screen edge
        self.anim_pos = QPropertyAnimation(self, b"pos", self)
        self.anim_fade = QPropertyAnimation(self, b"windowOpacity", self)
        self.anim = QParallelAnimationGroup(self)
        self.anim.addAnimation(self.anim_pos)
        self.anim.addAnimation(self.anim_fade)
        self.anim.finished.connect(self._on_anim_finished)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 0, 14, 22)

        self.card = PopoutCard("side", overflow=self.OVERFLOW, radius=18)
        self.card.setMinimumHeight(self.OVERFLOW + 150)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setOffset(0, 10)
        shadow.setColor(QColor(0, 0, 0, 220))
        self.card.setGraphicsEffect(shadow)
        root.addWidget(self.card)

        row = QHBoxLayout(self.card)
        row.setContentsMargins(16, self.OVERFLOW + 14, 16, 16)
        row.setSpacing(0)

        self.slot = QWidget(self.card)
        self.slot.setFixedWidth(180)
        self.slot.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.card.char_slot = self.slot
        row.addWidget(self.slot)

        col = QVBoxLayout()
        col.setSpacing(6)

        hdr = QHBoxLayout()
        hdr.setSpacing(6)
        self.lbl_title = QLabel()
        self.lbl_title.setObjectName("PopTitle")
        self.lbl_title.setWordWrap(True)
        hdr.addWidget(self.lbl_title, 1, Qt.AlignTop)
        self.btn_guide = make_icon_btn("?", self._toggle_guide)
        self.btn_mute = make_icon_btn("🔊", self._toggle_mute)
        self.btn_settings = make_icon_btn("⚙", self.open_settings_requested.emit)
        self.btn_close = make_icon_btn("✕", self._dismiss)
        for b in (self.btn_guide, self.btn_mute, self.btn_settings, self.btn_close):
            hdr.addWidget(b, 0, Qt.AlignTop)
        col.addLayout(hdr)

        meta = QHBoxLayout()
        self.lbl_dose = QLabel()
        self.lbl_dose.setObjectName("Dose")
        meta.addWidget(self.lbl_dose)
        meta.addStretch()
        self.lbl_today = QLabel()
        self.lbl_today.setObjectName("Pill")
        meta.addWidget(self.lbl_today)
        col.addLayout(meta)

        self.guide = GuideBox()
        self.guide.setVisible(False)
        col.addWidget(self.guide)

        col.addSpacing(4)
        act = QHBoxLayout()
        act.setSpacing(8)
        self.btn_primary = QPushButton()
        self.btn_primary.setCursor(Qt.PointingHandCursor)
        self.btn_primary.clicked.connect(self._on_primary)
        act.addWidget(self.btn_primary)
        self.btn_secondary = QPushButton()
        self.btn_secondary.setObjectName("Ghost")
        self.btn_secondary.setCursor(Qt.PointingHandCursor)
        self.btn_secondary.clicked.connect(self._on_secondary)
        act.addWidget(self.btn_secondary)
        self.lbl_banner = QLabel()
        self.lbl_banner.setObjectName("Banner")
        self.lbl_banner.setVisible(False)
        act.addWidget(self.lbl_banner)
        act.addStretch()
        self.lbl_timer = QLabel()
        self.lbl_timer.setObjectName("Timer")
        act.addWidget(self.lbl_timer)
        col.addLayout(act)
        col.addStretch()

        row.addLayout(col, 1)

    # --- language / content -------------------------------------------------
    def retranslate(self):
        lang = self.state.lang
        self.setStyleSheet(base_qss(lang))
        self.btn_guide.setToolTip(tr("guide", lang))
        self.btn_mute.setToolTip(tr("mute", lang))
        self.btn_settings.setToolTip(tr("settings", lang))
        self.btn_close.setToolTip(tr("dismiss", lang))
        self._fill_texts()
        if self.isVisible():
            self._fit_height()

    def _fill_texts(self):
        lang = self.state.lang
        ex = self.current_exercise
        self.lbl_title.setText(ex["title"][lang])
        self.lbl_dose.setText(ex["dose"][lang])
        self.lbl_today.setText(tr("today", lang, n=self.state.get_count(ex["id"])))
        self.guide.set_content(ex, lang)
        self.btn_primary.setText(tr("done" if self._running else "start", lang))
        self.btn_secondary.setText(tr("skip" if self._running else "snooze", lang))
        self._update_timer_text()

    def is_busy(self) -> bool:
        return self.isVisible() and not self._hiding

    def show_exercise(self, ex: dict):
        self.countdown_timer.stop()
        self._running = False
        if self._hiding:
            # A new pop-up arrived mid fade-out: finish closing the old one properly first
            self.anim.stop()
            self._hiding = False
            self.closed.emit()
        self.current_exercise = ex
        self.total_sec = ex["duration_sec"]
        self.remaining_sec = ex["duration_sec"]

        theme_hex = ex["theme_color"]
        self.card.set_exercise(ex)
        self.card.set_progress(0.0)
        self.lbl_dose.setStyleSheet(f"color: {theme_hex};")
        self.btn_primary.setStyleSheet(theme_button_qss(theme_hex))
        self.guide.setVisible(False)
        self.lbl_banner.setVisible(False)
        self.btn_primary.setVisible(True)
        self.btn_secondary.setVisible(True)
        self.lbl_timer.setVisible(True)
        self._fill_texts()
        self._sync_mute_btn()
        self._fit_height()
        self._slide_in()
        play_soft_chime(self.state.data.get("muted", False))

    # --- sizing: the top edge stays anchored, the window only grows downward ----
    def _target_pos(self) -> QPoint:
        screen = QApplication.primaryScreen().availableGeometry()
        return QPoint(screen.x() + (screen.width() - self.width()) // 2, screen.y() + self.TOP_GAP)

    def _fit_height(self):
        self._fit_height_now()
        # Word-wrapped labels only know their real height after a polish pass — measure again
        QTimer.singleShot(0, self._fit_height_now)

    def _fit_height_now(self):
        lay = self.layout()
        lay.invalidate()
        lay.activate()
        h = self.heightForWidth(self.width())
        if h <= 0:
            h = self.sizeHint().height()
        self.setFixedHeight(max(h, lay.totalMinimumSize().height()))
        if self.isVisible() and not self._hiding and self.anim.state() != QParallelAnimationGroup.Running:
            self.move(self._target_pos())

    def _toggle_guide(self):
        self.guide.setVisible(not self.guide.isVisible())
        self._fit_height()

    def _sync_mute_btn(self):
        self.btn_mute.setText("🔇" if self.state.data.get("muted", False) else "🔊")

    def _toggle_mute(self):
        self.state.data["muted"] = not self.state.data.get("muted", False)
        self.state.save()
        self._sync_mute_btn()
        self.state_updated.emit()

    # --- actions ---------------------------------------------------------------
    def _on_primary(self):
        if not self._running:
            self._running = True
            self.btn_primary.setText(tr("done", self.state.lang))
            self.btn_secondary.setText(tr("skip", self.state.lang))
            self.countdown_timer.start(1000)
        else:
            self._complete_exercise()

    def _on_secondary(self):
        self.countdown_timer.stop()
        if not self._running:
            self.snooze_requested.emit(self.current_exercise)
            self._show_banner_and_hide(tr("snoozed", self.state.lang), "#F59E0B")
        else:
            self._dismiss()

    def _on_tick(self):
        self.remaining_sec -= 1
        self.card.set_progress((self.total_sec - self.remaining_sec) / max(1, self.total_sec))
        if self.remaining_sec <= 0:
            self._complete_exercise()
        else:
            self._update_timer_text()

    def _update_timer_text(self):
        m, s = divmod(max(0, self.remaining_sec), 60)
        self.lbl_timer.setText(digits(f"{m:02d}:{s:02d}", self.state.lang))

    def _complete_exercise(self):
        self.countdown_timer.stop()
        self._running = False
        self.card.set_progress(1.0)
        new_count = self.state.increment_count(self.current_exercise["id"])
        self.lbl_today.setText(tr("today", self.state.lang, n=new_count))
        self.state_updated.emit()
        play_soft_chime(self.state.data.get("muted", False))
        self._show_banner_and_hide(tr("completed", self.state.lang, n=new_count), "#10B981")

    def _show_banner_and_hide(self, msg: str, color_hex: str):
        self.btn_primary.setVisible(False)
        self.btn_secondary.setVisible(False)
        self.lbl_timer.setVisible(False)
        self.lbl_banner.setText(msg)
        self.lbl_banner.setStyleSheet(
            f"background-color: rgba(9, 13, 22, 235); color: {color_hex}; border: 1px solid {color_hex};"
        )
        self.lbl_banner.setVisible(True)
        QTimer.singleShot(1400, self._dismiss)

    # --- animation ---------------------------------------------------------------
    def _slide_in(self):
        self._hiding = False
        end = self._target_pos()
        start = end - QPoint(0, 28)
        self.anim.stop()
        if not self.isVisible():
            self.setWindowOpacity(0.0)
            self.move(start)
            self.show()
        self.raise_()
        self.anim_pos.setDuration(380)
        self.anim_pos.setEasingCurve(QEasingCurve.OutCubic)
        self.anim_pos.setStartValue(self.pos())
        self.anim_pos.setEndValue(end)
        self.anim_fade.setDuration(300)
        self.anim_fade.setStartValue(self.windowOpacity())
        self.anim_fade.setEndValue(1.0)
        self.anim.start()

    def _dismiss(self):
        self.countdown_timer.stop()
        self._running = False
        if not self.isVisible() or self._hiding:
            return
        self._hiding = True
        self.anim.stop()
        self.anim_pos.setDuration(260)
        self.anim_pos.setEasingCurve(QEasingCurve.InCubic)
        self.anim_pos.setStartValue(self.pos())
        self.anim_pos.setEndValue(self.pos() - QPoint(0, 24))
        self.anim_fade.setDuration(240)
        self.anim_fade.setStartValue(self.windowOpacity())
        self.anim_fade.setEndValue(0.0)
        self.anim.start()

    def _on_anim_finished(self):
        if self._hiding:
            self.hide()
            self._hiding = False
            self.closed.emit()

    def hide_now(self):
        self.countdown_timer.stop()
        self._running = False
        self.anim.stop()
        was_visible = self.isVisible()
        self._hiding = False
        self.hide()
        if was_visible:
            self.closed.emit()


# ---------------------------------------------------------------------------
# GUIDE DIALOG (opened from the "?" on a dashboard card)
# ---------------------------------------------------------------------------
class GuideDialog(QDialog):
    start_requested = Signal(object)

    def __init__(self, ex: dict, lang: str, parent=None):
        super().__init__(parent)
        self.ex = ex
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(True)
        self.setStyleSheet(base_qss(lang))
        self.setLayoutDirection(Qt.RightToLeft if lang == "fa" else Qt.LeftToRight)
        self.setFixedWidth(620)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 0, 14, 22)
        card = PopoutCard("side", overflow=48, radius=18)
        card.set_exercise(ex)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setOffset(0, 10)
        shadow.setColor(QColor(0, 0, 0, 220))
        card.setGraphicsEffect(shadow)
        root.addWidget(card)

        row = QHBoxLayout(card)
        row.setContentsMargins(16, 48 + 14, 16, 16)
        row.setSpacing(0)
        slot = QWidget(card)
        slot.setFixedWidth(180)
        slot.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        card.char_slot = slot
        row.addWidget(slot)

        col = QVBoxLayout()
        col.setSpacing(8)
        hdr = QHBoxLayout()
        title = QLabel(ex["title"][lang])
        title.setObjectName("PopTitle")
        title.setWordWrap(True)
        hdr.addWidget(title, 1, Qt.AlignTop)
        hdr.addWidget(make_icon_btn("✕", self.reject), 0, Qt.AlignTop)
        col.addLayout(hdr)
        dose = QLabel(ex["dose"][lang])
        dose.setObjectName("Dose")
        dose.setStyleSheet(f"color: {ex['theme_color']};")
        col.addWidget(dose)
        box = GuideBox()
        box.set_content(ex, lang)
        col.addWidget(box)
        act = QHBoxLayout()
        btn_start = QPushButton(tr("start_now", lang))
        btn_start.setCursor(Qt.PointingHandCursor)
        btn_start.setStyleSheet(theme_button_qss(ex["theme_color"]))
        btn_start.clicked.connect(self._start)
        act.addWidget(btn_start)
        btn_close = QPushButton(tr("close", lang))
        btn_close.setObjectName("Ghost")
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.clicked.connect(self.reject)
        act.addWidget(btn_close)
        act.addStretch()
        col.addLayout(act)
        row.addLayout(col, 1)

        self._fit()

    def _fit(self):
        self.layout().invalidate()
        self.layout().activate()
        h = self.heightForWidth(self.width())
        self.setFixedHeight(h if h > 0 else self.sizeHint().height())
        parent = self.parentWidget()
        if parent is not None:
            pg = parent.frameGeometry()
            self.move(pg.center().x() - self.width() // 2, pg.center().y() - self.height() // 2)

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self._fit)

    def _start(self):
        self.start_requested.emit(self.ex)
        self.accept()


# ---------------------------------------------------------------------------
# DASHBOARD
# ---------------------------------------------------------------------------
class ExerciseTile(PopoutCard):
    clicked = Signal(object)
    guide_requested = Signal(object)

    def __init__(self, ex: dict, idx: int, parent=None):
        super().__init__("vertical", overflow=46, radius=18, parent=parent)
        self.ex = ex
        self.set_exercise(ex)
        self.bg_focus = BG_FOCI[idx % len(BG_FOCI)]
        self.bg_zoom = 1.5
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumSize(220, 300)

        v = QVBoxLayout(self)
        v.setContentsMargins(16, self.overflow + 16, 16, 14)
        v.setSpacing(3)
        v.addStretch(1)

        top = QHBoxLayout()
        self.lbl_title = QLabel()
        self.lbl_title.setObjectName("TileTitle")
        self.lbl_title.setWordWrap(True)
        top.addWidget(self.lbl_title, 1, Qt.AlignBottom)
        self.btn_guide = make_icon_btn("?", lambda: self.guide_requested.emit(self.ex))
        top.addWidget(self.btn_guide, 0, Qt.AlignBottom)
        v.addLayout(top)

        meta = QHBoxLayout()
        self.lbl_dose = QLabel()
        self.lbl_dose.setObjectName("Dose")
        self.lbl_dose.setStyleSheet(f"color: {ex['theme_color']};")
        meta.addWidget(self.lbl_dose)
        meta.addStretch()
        self.lbl_count = QLabel()
        self.lbl_count.setObjectName("Pill")
        meta.addWidget(self.lbl_count)
        v.addLayout(meta)

        self.hover_anim = QVariantAnimation(self)
        self.hover_anim.setDuration(180)
        self.hover_anim.setEasingCurve(QEasingCurve.OutCubic)
        self.hover_anim.valueChanged.connect(self._set_lift)

    def _set_lift(self, v):
        self.lift = float(v)
        self.update()

    def set_texts(self, lang: str, count: int):
        self.lbl_title.setText(self.ex["title"][lang])
        self.lbl_dose.setText(self.ex["dose"][lang])
        self.lbl_count.setText(tr("today", lang, n=count))
        self.btn_guide.setToolTip(tr("guide", lang))

    def _animate_lift(self, target: float):
        self.hover_anim.stop()
        self.hover_anim.setStartValue(self.lift)
        self.hover_anim.setEndValue(target)
        self.hover_anim.start()

    def enterEvent(self, event):
        self._animate_lift(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._animate_lift(0.0)
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.rect().contains(event.position().toPoint()):
            self.clicked.emit(self.ex)
        super().mouseReleaseEvent(event)


class Backdrop(QWidget):
    """Window background: the shared Arcane graffiti art, heavily dimmed."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._key = None
        self._pix = QPixmap()

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#070A12"))
        img = asset_image("background.jpg")
        if not img.isNull():
            dpr = self.devicePixelRatioF()
            key = (self.width(), self.height(), dpr)
            if key != self._key:
                self._pix = cover_pixmap(img, self.width(), self.height(), (0.5, 0.5), 1.0, dpr)
                self._key = key
            p.drawPixmap(0, 0, self._pix)
        p.fillRect(self.rect(), QColor(5, 7, 14, 215))
        vignette = QRadialGradient(self.width() / 2, self.height() / 2, max(self.width(), self.height()) * 0.75)
        vignette.setColorAt(0.0, QColor(0, 0, 0, 0))
        vignette.setColorAt(1.0, QColor(0, 0, 0, 170))
        p.fillRect(self.rect(), vignette)


class MinuteStepper(QWidget):
    """− [ 20 min ] + — a plain label between two buttons. (QSpinBox loses its text field
    after an RTL<->LTR switch when styled, so the value went invisible in English.)"""
    valueChanged = Signal(int)

    def __init__(self, minimum: int, maximum: int, step: int, parent=None):
        super().__init__(parent)
        self._min, self._max, self._step = minimum, maximum, step
        self._value = minimum
        self._lang = "en"
        hb = QHBoxLayout(self)
        hb.setContentsMargins(0, 0, 0, 0)
        hb.setSpacing(6)
        self.btn_down = make_icon_btn("−", lambda: self.setValue(self._value - self._step))
        self.btn_up = make_icon_btn("+", lambda: self.setValue(self._value + self._step))
        for b in (self.btn_down, self.btn_up):
            b.setAutoRepeat(True)          # hold to keep counting
            b.setAutoRepeatDelay(400)
            b.setAutoRepeatInterval(90)
        self.lbl = QLabel()
        self.lbl.setObjectName("StepValue")
        self.lbl.setAlignment(Qt.AlignCenter)
        self.lbl.setMinimumWidth(104)
        hb.addWidget(self.btn_down)
        hb.addWidget(self.lbl)
        hb.addWidget(self.btn_up)
        self._render()

    def value(self) -> int:
        return self._value

    def setValue(self, v: int):
        v = max(self._min, min(self._max, int(v)))
        if v != self._value:
            self._value = v
            self._render()
            if not self.signalsBlocked():
                self.valueChanged.emit(v)

    def set_lang(self, lang: str):
        self._lang = lang
        self._render()

    def _render(self):
        self.lbl.setText(digits(self._value, self._lang) + tr("minutes", self._lang))
        self.btn_down.setEnabled(self._value > self._min)
        self.btn_up.setEnabled(self._value < self._max)

    def wheelEvent(self, event):
        self.setValue(self._value + (self._step if event.angleDelta().y() > 0 else -self._step))
        event.accept()


class ToggleSwitch(QCheckBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(46, 26)

    def hitButton(self, pos):
        return self.rect().contains(pos)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        on = self.isChecked()
        p.setPen(QPen(QColor("#C89B3C") if on else QColor("#475569"), 1))
        p.setBrush(QColor("#C89B3C") if on else QColor("#1E293B"))
        p.drawRoundedRect(QRectF(0.5, 0.5, 45, 25), 12.5, 12.5)
        knob_on_far_side = on != self.isRightToLeft()
        x = 23 if knob_on_far_side else 3
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#090D16") if on else QColor("#94A3B8"))
        p.drawEllipse(QRectF(x, 3, 20, 20))


class ControlCenter(QMainWindow):
    play_requested = Signal(object)
    next_requested = Signal()
    settings_updated = Signal()
    language_changed = Signal()

    def __init__(self, state: StateManager):
        super().__init__()
        self.state = state
        self.setMinimumSize(800, 760)
        self.resize(960, 800)
        self.backdrop = Backdrop()
        self.setCentralWidget(self.backdrop)
        root = QVBoxLayout(self.backdrop)
        root.setContentsMargins(26, 20, 26, 22)
        self.stack = QStackedWidget()
        root.addWidget(self.stack)
        self.page_home = self._build_home()
        self.page_settings = self._build_settings()
        self.stack.addWidget(self.page_home)
        self.stack.addWidget(self.page_settings)
        self.retranslate()

    # --- home ------------------------------------------------------------------
    def _build_home(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)

        hdr = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(2)
        lbl_h1 = QLabel("HEXSTRETCH")
        lbl_h1.setObjectName("H1")
        self.lbl_sub = QLabel()
        self.lbl_sub.setObjectName("Sub")
        self.lbl_sub.setWordWrap(True)
        titles.addWidget(lbl_h1)
        titles.addWidget(self.lbl_sub)
        hdr.addLayout(titles, 1)
        self.btn_next = QPushButton()
        self.btn_next.setObjectName("Gold")
        self.btn_next.setCursor(Qt.PointingHandCursor)
        self.btn_next.clicked.connect(self.next_requested.emit)
        hdr.addWidget(self.btn_next, 0, Qt.AlignVCenter)
        self.btn_open_settings = make_icon_btn("⚙", self.show_settings)
        hdr.addWidget(self.btn_open_settings, 0, Qt.AlignVCenter)
        v.addLayout(hdr)

        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(8)
        self.tiles = []
        for idx, ex in enumerate(EXERCISES):
            tile = ExerciseTile(ex, idx)
            tile.clicked.connect(self.play_requested.emit)
            tile.guide_requested.connect(self._open_guide)
            r, c = divmod(idx, 3)
            grid.addWidget(tile, r, c)
            self.tiles.append(tile)
        v.addLayout(grid, 1)
        return page

    def _open_guide(self, ex: dict):
        dlg = GuideDialog(ex, self.state.lang, self)
        dlg.start_requested.connect(self.play_requested.emit)
        dlg.exec()

    # --- settings --------------------------------------------------------------
    def _build_settings(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(16)

        hdr = QHBoxLayout()
        self.btn_back = QPushButton()
        self.btn_back.setObjectName("Ghost")
        self.btn_back.setCursor(Qt.PointingHandCursor)
        self.btn_back.clicked.connect(self.show_home)
        hdr.addWidget(self.btn_back)
        hdr.addSpacing(10)
        self.lbl_settings_title = QLabel()
        self.lbl_settings_title.setObjectName("PanelTitle")
        hdr.addWidget(self.lbl_settings_title)
        hdr.addStretch()
        v.addLayout(hdr)

        center = QHBoxLayout()
        center.addStretch()
        panel = QFrame()
        panel.setObjectName("Panel")
        panel.setFixedWidth(600)
        center.addWidget(panel)
        center.addStretch()
        v.addLayout(center)
        v.addStretch()

        g = QGridLayout(panel)
        g.setContentsMargins(26, 22, 26, 22)
        g.setHorizontalSpacing(20)
        g.setVerticalSpacing(14)
        g.setColumnStretch(0, 1)
        self._setting_labels = {}
        row = 0

        def add_row(key, control, hint_key=None):
            nonlocal row
            box = QVBoxLayout()
            box.setSpacing(1)
            lbl = QLabel()
            lbl.setObjectName("RowLabel")
            box.addWidget(lbl)
            hint = None
            if hint_key:
                hint = QLabel()
                hint.setObjectName("RowHint")
                box.addWidget(hint)
            self._setting_labels[key] = (lbl, hint, hint_key)
            g.addLayout(box, row, 0)
            g.addWidget(control, row, 1, Qt.AlignVCenter | Qt.AlignRight)
            row += 1

        def add_divider():
            nonlocal row
            line = QFrame()
            line.setObjectName("Divider")
            g.addWidget(line, row, 0, 1, 2)
            row += 1

        self.sw_enabled = ToggleSwitch()
        self.sw_enabled.toggled.connect(self._save_from_ui)
        add_row("s_reminders", self.sw_enabled, "s_reminders_hint")
        self.sw_sound = ToggleSwitch()
        self.sw_sound.toggled.connect(self._save_from_ui)
        add_row("s_sound", self.sw_sound, "s_sound_hint")
        self.sw_startup = ToggleSwitch()
        self.sw_startup.toggled.connect(self._save_from_ui)
        add_row("s_startup", self.sw_startup, "s_startup_hint")
        add_divider()

        self.spin_stretch = MinuteStepper(1, 120, 1)
        self.spin_stretch.valueChanged.connect(self._save_from_ui)
        add_row("s_stretch", self.spin_stretch)
        self.spin_water = MinuteStepper(15, 180, 5)
        self.spin_water.valueChanged.connect(self._save_from_ui)
        add_row("s_water", self.spin_water)
        add_divider()

        lang_box = QWidget()
        lb = QHBoxLayout(lang_box)
        lb.setContentsMargins(0, 0, 0, 0)
        lb.setSpacing(6)
        self.lang_group = QButtonGroup(self)
        self.lang_group.setExclusive(True)
        self.lang_buttons = {}
        for code, label in (("fa", "فارسی"), ("en", "English")):
            b = QPushButton(label)
            b.setObjectName("Seg")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            if code == "fa":
                b.setFont(QFont(FONT_FAMILY["fa"]))
            self.lang_group.addButton(b)
            self.lang_buttons[code] = b
            b.clicked.connect(lambda _=False, c=code: self._set_language(c))
            lb.addWidget(b)
        add_row("s_language", lang_box)
        add_divider()

        self.btn_quit = QPushButton()
        self.btn_quit.setObjectName("Danger")
        self.btn_quit.setCursor(Qt.PointingHandCursor)
        self.btn_quit.clicked.connect(QApplication.instance().quit)
        g.addWidget(self.btn_quit, row, 0, 1, 2, Qt.AlignLeft)
        return page

    def show_settings(self):
        self.refresh_from_state()
        self.stack.setCurrentWidget(self.page_settings)

    def show_home(self):
        self.stack.setCurrentWidget(self.page_home)

    def _set_language(self, code: str):
        if code != self.state.lang:
            self.state.data["language"] = code
            self.state.save()
            self.language_changed.emit()

    # --- texts / state -----------------------------------------------------------
    def retranslate(self):
        lang = self.state.lang
        self.backdrop.setStyleSheet(base_qss(lang))
        self.setWindowTitle(tr("window_title", lang))
        self.lbl_sub.setText(tr("subtitle", lang))
        self.btn_next.setText(tr("next", lang))
        self.btn_open_settings.setToolTip(tr("settings", lang))
        self.btn_back.setText(tr("back", lang))
        self.lbl_settings_title.setText(tr("settings", lang))
        for key, (lbl, hint, hint_key) in self._setting_labels.items():
            lbl.setText(tr(key, lang))
            if hint is not None:
                hint.setText(tr(hint_key, lang))
        for spin in (self.spin_stretch, self.spin_water):
            spin.set_lang(lang)
        self.btn_quit.setText(tr("quit", lang))
        self.refresh_from_state()

    def refresh_from_state(self):
        lang = self.state.lang
        widgets = (self.sw_enabled, self.sw_sound, self.sw_startup, self.spin_stretch, self.spin_water)
        for w in widgets:
            w.blockSignals(True)
        self.sw_enabled.setChecked(self.state.data.get("notifications_enabled", True))
        self.sw_sound.setChecked(not self.state.data.get("muted", False))
        self.sw_startup.setChecked(is_startup_enabled())
        self.spin_stretch.setValue(int(self.state.data.get("interval_minutes", 20)))
        self.spin_water.setValue(int(self.state.data.get("water_interval_minutes", 60)))
        for w in widgets:
            w.blockSignals(False)
            w.update()
        self.lang_buttons[lang].setChecked(True)
        for tile in self.tiles:
            tile.set_texts(lang, self.state.get_count(tile.ex["id"]))

    def _save_from_ui(self):
        self.state.data["notifications_enabled"] = self.sw_enabled.isChecked()
        self.state.data["muted"] = not self.sw_sound.isChecked()
        self.state.data["interval_minutes"] = self.spin_stretch.value()
        self.state.data["water_interval_minutes"] = self.spin_water.value()
        if self.sw_startup.isChecked() != is_startup_enabled():
            set_startup_enabled(self.sw_startup.isChecked())
        self.state.data["run_on_startup"] = is_startup_enabled()
        self.state.save()
        self.settings_updated.emit()

    def closeEvent(self, event):
        # Hide to tray instead of quitting
        event.ignore()
        self.hide()


# ---------------------------------------------------------------------------
# APPLICATION ORCHESTRATOR & SYSTEM TRAY
# ---------------------------------------------------------------------------
def create_hextech_icon(active=True) -> QIcon:
    pix = QPixmap(64, 64)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setPen(QPen(QColor("#C89B3C"), 4))
    p.setBrush(QColor("#070A12"))
    p.drawRoundedRect(6, 6, 52, 52, 14, 14)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#05D5FF") if active else QColor("#64748B"))
    poly = QPolygonF([QPointF(32, 12), QPointF(50, 32), QPointF(32, 52), QPointF(14, 32)])
    p.drawPolygon(poly)
    p.end()
    return QIcon(pix)


class HexStretchApp:
    def __init__(self, app: QApplication):
        self.app = app
        self._apply_dark_fusion_palette()
        load_fonts()

        self.state = StateManager()
        if is_startup_enabled():
            set_startup_enabled(True)   # point an older version's auto-start entry at this script
        self._apply_language_globals()
        self.popup = ExercisePopup(self.state)
        self.dashboard = ControlCenter(self.state)
        self.popup.retranslate()

        self.popup.open_settings_requested.connect(self.show_settings)
        self.popup.snooze_requested.connect(self.schedule_snooze)
        self.popup.state_updated.connect(self.on_state_updated)
        self.popup.closed.connect(self._on_popup_closed)

        self.dashboard.play_requested.connect(self.show_now)
        self.dashboard.next_requested.connect(lambda: self.trigger_next_stretch(force=True))
        self.dashboard.settings_updated.connect(self.on_state_updated)
        self.dashboard.language_changed.connect(self.on_language_changed)

        self.posture_exercises = [e for e in EXERCISES if e["id"] != "hydration"]
        self.water_exercise = next(e for e in EXERCISES if e["id"] == "hydration")
        self.pending = []   # reminders that fired while another pop-up was on screen
        self.snoozed_exercise = None
        self._intervals = (None, None)

        # Each countdown is one-shot and only re-arms when its pop-up is closed, so the
        # interval is "N minutes after you finished the last one" and reminders never pile up.
        self.stretch_timer = QTimer()
        self.stretch_timer.setSingleShot(True)
        self.stretch_timer.setTimerType(Qt.PreciseTimer)
        self.stretch_timer.timeout.connect(self.trigger_next_stretch)
        self.water_timer = QTimer()
        self.water_timer.setSingleShot(True)
        self.water_timer.setTimerType(Qt.PreciseTimer)
        self.water_timer.timeout.connect(self.trigger_water)
        self.snooze_timer = QTimer()
        self.snooze_timer.setSingleShot(True)
        self.snooze_timer.setTimerType(Qt.PreciseTimer)
        self.snooze_timer.timeout.connect(self._on_snooze_over)

        self._setup_tray()
        self.apply_timers()

        if "--minimized" not in sys.argv:
            self.show_dashboard()

    def _apply_dark_fusion_palette(self):
        self.app.setStyle("Fusion")
        pal = QPalette()
        pal.setColor(QPalette.Window, QColor("#070A12"))
        pal.setColor(QPalette.WindowText, QColor("#F8FAFC"))
        pal.setColor(QPalette.Base, QColor("#0D1322"))
        pal.setColor(QPalette.AlternateBase, QColor("#1E293B"))
        pal.setColor(QPalette.ToolTipBase, QColor("#090D16"))
        pal.setColor(QPalette.ToolTipText, QColor("#F8FAFC"))
        pal.setColor(QPalette.Text, QColor("#F8FAFC"))
        pal.setColor(QPalette.Button, QColor("#1E293B"))
        pal.setColor(QPalette.ButtonText, QColor("#F8FAFC"))
        pal.setColor(QPalette.Highlight, QColor("#C89B3C"))
        pal.setColor(QPalette.HighlightedText, QColor("#070A12"))
        self.app.setPalette(pal)

    def _apply_language_globals(self):
        lang = self.state.lang
        self.app.setLayoutDirection(Qt.RightToLeft if lang == "fa" else Qt.LeftToRight)
        self.app.setFont(QFont(FONT_FAMILY[lang], 10))

    def on_language_changed(self):
        self._apply_language_globals()
        self.dashboard.retranslate()
        self.popup.retranslate()
        self._retranslate_tray()

    def _setup_tray(self):
        self.tray = QSystemTrayIcon(self.app)
        self.menu = QMenu()
        self.act_open = self.menu.addAction("")
        self.act_open.triggered.connect(self.show_dashboard)
        self.menu.addSeparator()
        self.act_next = self.menu.addAction("")
        self.act_next.triggered.connect(lambda: self.trigger_next_stretch(force=True))
        self.act_water = self.menu.addAction("")
        self.act_water.triggered.connect(lambda: self.trigger_water(force=True))
        self.menu.addSeparator()
        self.act_notif = self.menu.addAction("")
        self.act_notif.triggered.connect(self.toggle_notifications)
        self.act_mute = self.menu.addAction("")
        self.act_mute.triggered.connect(self.toggle_mute)
        self.menu.addSeparator()
        self.act_quit = self.menu.addAction("")
        self.act_quit.triggered.connect(self.app.quit)

        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(lambda r: self.show_dashboard() if r != QSystemTrayIcon.Context else None)
        self._retranslate_tray()
        self.tray.show()

    def _retranslate_tray(self):
        lang = self.state.lang
        self.menu.setStyleSheet(f"""
            QMenu {{
                background-color: #070A12; color: #F8FAFC; border: 1px solid #C89B3C;
                font-family: "{FONT_FAMILY[lang]}"; font-size: 12.5px; padding: 6px;
            }}
            QMenu::item {{ padding: 6px 22px 6px 12px; border-radius: 5px; }}
            QMenu::item:selected {{ background-color: #1E293B; color: #05D5FF; }}
        """)
        self.act_open.setText(tr("tray_open", lang))
        self.act_next.setText(tr("tray_next", lang))
        self.act_water.setText(tr("tray_water", lang))
        self.act_quit.setText(tr("tray_quit", lang))
        self.refresh_tray()

    def show_dashboard(self):
        self.dashboard.refresh_from_state()
        self.dashboard.showNormal()
        self.dashboard.raise_()
        self.dashboard.activateWindow()

    def show_settings(self):
        self.show_dashboard()
        self.dashboard.show_settings()

    def on_state_updated(self):
        self.apply_timers()
        self.dashboard.refresh_from_state()
        self.popup._sync_mute_btn()
        self.refresh_tray()
        if not self.state.data.get("notifications_enabled", True):
            self.snooze_timer.stop()
            self.snoozed_exercise = None
            self.pending.clear()

    def _interval_ms(self, kind: str) -> int:
        key = "water_interval_minutes" if kind == "water" else "interval_minutes"
        default = 60 if kind == "water" else 20
        return int(self.state.data.get(key, default)) * MS_PER_MIN

    def _arm(self, kind: str):
        """Start this kind's countdown from zero (full interval from now)."""
        timer = self.water_timer if kind == "water" else self.stretch_timer
        timer.start(self._interval_ms(kind))

    def apply_timers(self):
        # Only touch a countdown when its interval actually changed — toggling mute or
        # finishing an exercise must not move the next reminder. A countdown that is
        # paused because its pop-up is on screen picks up the new value when it closes.
        s_min = int(self.state.data.get("interval_minutes", 20))
        w_min = int(self.state.data.get("water_interval_minutes", 60))
        first = self._intervals == (None, None)
        if first or (s_min != self._intervals[0] and self.stretch_timer.isActive()):
            self._arm("stretch")
        if first or (w_min != self._intervals[1] and self.water_timer.isActive()):
            self._arm("water")
        self._intervals = (s_min, w_min)

    def refresh_tray(self):
        lang = self.state.lang
        en = self.state.data.get("notifications_enabled", True)
        muted = self.state.data.get("muted", False)
        self.tray.setIcon(create_hextech_icon(en))
        self.tray.setToolTip(tr("tray_tip_on" if en else "tray_tip_off", lang))
        self.act_notif.setText(tr("tray_notif_on" if en else "tray_notif_off", lang))
        self.act_mute.setText(tr("tray_sound_off" if muted else "tray_sound_on", lang))

    def toggle_notifications(self):
        self.state.data["notifications_enabled"] = not self.state.data.get("notifications_enabled", True)
        self.state.save()
        if not self.state.data["notifications_enabled"]:
            self.popup.hide_now()
        self.on_state_updated()
        # Off or on, both countdowns restart from zero so nothing fires right after re-enabling
        self._arm("stretch")
        self._arm("water")

    def toggle_mute(self):
        self.state.data["muted"] = not self.state.data.get("muted", False)
        self.state.save()
        self.on_state_updated()

    # --- reminders -----------------------------------------------------------------
    def _notifications_on(self) -> bool:
        return self.state.data.get("notifications_enabled", True)

    def show_now(self, ex: dict):
        """Manual pop-up (card click, tray, "next" button): replaces whatever is on screen."""
        if self.popup.is_busy():
            self._arm(self._kind(self.popup.current_exercise))   # the replaced one never "closes"
        self.popup.show_exercise(ex)

    @staticmethod
    def _kind(ex: dict) -> str:
        return "water" if ex["id"] == "hydration" else "stretch"

    def request_popup(self, ex: dict):
        """Timer-driven reminders wait their turn instead of replacing an exercise in progress."""
        if self.popup.is_busy():
            kind = self._kind(ex)
            if kind == self._kind(self.popup.current_exercise):
                return   # same kind already on screen; its countdown re-arms when it closes
            if all(self._kind(q) != kind for q in self.pending):
                self.pending.append(ex)
        else:
            self.popup.show_exercise(ex)

    def _on_popup_closed(self):
        closed = self.popup.current_exercise
        snoozed = self.snoozed_exercise is not None and self.snoozed_exercise["id"] == closed["id"]
        if not snoozed:
            self._arm(self._kind(closed))   # next one comes a full interval after this one closed
        if self.pending:
            ex = self.pending.pop(0)
            QTimer.singleShot(1500, lambda: self._show_pending(ex))

    def _show_pending(self, ex: dict):
        if self._notifications_on():
            self.request_popup(ex)
        else:
            self._arm(self._kind(ex))

    def schedule_snooze(self, ex: dict):
        self.snoozed_exercise = ex
        (self.water_timer if self._kind(ex) == "water" else self.stretch_timer).stop()
        self.snooze_timer.start(SNOOZE_MINUTES * MS_PER_MIN)

    def _on_snooze_over(self):
        ex, self.snoozed_exercise = self.snoozed_exercise, None
        if ex is None:
            return
        if self._notifications_on():
            self.request_popup(ex)
        else:
            self._arm(self._kind(ex))

    def _next_posture_exercise(self) -> dict:
        idx = self.state.data.get("queue_index", 0) % len(self.posture_exercises)
        self.state.data["queue_index"] = (idx + 1) % len(self.posture_exercises)
        self.state.save()
        return self.posture_exercises[idx]

    def trigger_next_stretch(self, force=False):
        if force:
            self.show_now(self._next_posture_exercise())
        elif not self._notifications_on():
            self._arm("stretch")
        else:
            self.request_popup(self._next_posture_exercise())

    def trigger_water(self, force=False):
        if force:
            self.show_now(self.water_exercise)
        elif not self._notifications_on():
            self._arm("water")
        else:
            self.request_popup(self.water_exercise)


INSTANCE_KEY = f"HexStretch-{getpass.getuser()}"


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # Only one copy may run: two copies means two sets of timers and reminders far too often.
    # A second launch just asks the running copy to show its window, then exits.
    probe = QLocalSocket()
    probe.connectToServer(INSTANCE_KEY)
    if probe.waitForConnected(500):
        if "--minimized" not in sys.argv:
            probe.write(b"show")
            probe.flush()
            probe.waitForBytesWritten(500)
        probe.disconnectFromServer()
        return 0

    QLocalServer.removeServer(INSTANCE_KEY)   # clean up after a crashed copy
    server = QLocalServer()
    server.setSocketOptions(QLocalServer.UserAccessOption)   # only this Windows user can talk to it
    server.listen(INSTANCE_KEY)
    controller = HexStretchApp(app)

    def on_second_launch():
        conn = server.nextPendingConnection()
        if conn is None:
            return
        conn.waitForReadyRead(300)
        if conn.readAll().data() == b"show":
            controller.show_dashboard()
        conn.disconnectFromServer()

    server.newConnection.connect(on_second_launch)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

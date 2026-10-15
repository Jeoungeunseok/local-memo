import sys
import os
import sqlite3
import random
from datetime import date, datetime
import ctypes
from ctypes import wintypes
try:
    from PyQt6.QtWidgets import (
        QApplication,
        QMainWindow,
        QTextEdit,
        QVBoxLayout,
        QHBoxLayout,
        QWidget,
        QDateEdit,
        QTimeEdit,
        QPushButton,
        QToolButton,
        QMenu,
        QGraphicsDropShadowEffect,
        QSystemTrayIcon,
    )
    from PyQt6.QtCore import QDate, QTime, Qt, QPoint, QTimer, QThread, pyqtSignal
    from PyQt6.QtGui import (
        QColor,
        QFont,
        QAction,
        QIcon,
        QPixmap,
        QPainter,
        QBrush,
        QPen,
        QKeySequence,
        QShortcut,
        QCursor,
    )
except Exception:
    from PySide6.QtWidgets import (
        QApplication,
        QMainWindow,
        QTextEdit,
        QVBoxLayout,
        QHBoxLayout,
        QWidget,
        QDateEdit,
        QTimeEdit,
        QPushButton,
        QToolButton,
        QMenu,
        QGraphicsDropShadowEffect,
        QSystemTrayIcon,
    )
    from PySide6.QtCore import QDate, QTime, Qt, QPoint, QTimer, QThread, Signal as pyqtSignal
    from PySide6.QtGui import (
        QColor,
        QFont,
        QAction,
        QIcon,
        QPixmap,
        QPainter,
        QBrush,
        QPen,
        QKeySequence,
        QShortcut,
        QCursor,
    )

try:
    import winsound
except ImportError:
    winsound = None

# DB 경로 설정 (exe로 단일 패키징 시 AppData 폴더에 안전하게 영구 보존)
if getattr(sys, 'frozen', False):
    app_data_dir = os.path.join(os.getenv("APPDATA", os.path.expanduser("~")), "StickyCalendar")
    os.makedirs(app_data_dir, exist_ok=True)
    DB_PATH = os.path.join(app_data_dir, "sticky_notes.db")
else:
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sticky_notes.db")

# 파스텔 톤 테마 정의 (배경색, 헤더색, 테두리색, 텍스트색)
PASTEL_THEMES = {
    "yellow": {"bg": "#FEF9E7", "header": "#FDEBD0", "border": "#FAD7A0", "text": "#333333"},
    "blue": {"bg": "#EBF5FB", "header": "#D4E6F1", "border": "#A9CCE3", "text": "#333333"},
    "green": {"bg": "#EAFAF1", "header": "#D5F5E3", "border": "#A9DFBF", "text": "#333333"},
    "orange": {"bg": "#FBEEE6", "header": "#F6DDCC", "border": "#EDBB99", "text": "#333333"},
    "purple": {"bg": "#F4ECF7", "header": "#E8DAEF", "border": "#D2B4DE", "text": "#333333"},
}

def create_tray_icon_pixmap():
    """트레이용 귀여운 포스트잇 픽스맵 아이콘 생성"""
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # 포스트잇 본체 (노랑)
    painter.setBrush(QBrush(QColor("#FDEBD0")))
    painter.setPen(QPen(QColor("#FAD7A0"), 1.5))
    painter.drawRoundedRect(3, 4, 26, 24, 4, 4)

    # 핀(Pin) 포인트 (빨강)
    painter.setBrush(QBrush(QColor("#EF4444")))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(13, 1, 6, 6)

    # 포스트잇 라인
    painter.setPen(QPen(QColor("#D97706"), 1.5))
    painter.drawLine(8, 12, 22, 12)
    painter.drawLine(8, 17, 24, 17)
    painter.drawLine(8, 22, 18, 22)

    painter.end()
    return pixmap

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS sticky_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_date TEXT,
            target_time TEXT DEFAULT '',
            content TEXT,
            color TEXT,
            is_pinned INTEGER,
            is_alarm_enabled INTEGER DEFAULT 0,
            pos_x INTEGER,
            pos_y INTEGER,
            width INTEGER,
            height INTEGER
        )
        """
    )
    conn.commit()

    # 기존 DB에 컬럼이 없을 경우 마이그레이션
    cursor.execute("PRAGMA table_info(sticky_notes)")
    cols = [col[1] for col in cursor.fetchall()]
    if "target_time" not in cols:
        cursor.execute("ALTER TABLE sticky_notes ADD COLUMN target_time TEXT DEFAULT ''")
    if "is_alarm_enabled" not in cols:
        cursor.execute("ALTER TABLE sticky_notes ADD COLUMN is_alarm_enabled INTEGER DEFAULT 0")
    conn.commit()
    conn.close()

active_windows = []

class GlobalHotkeyThread(QThread):
    """Windows OS 전역 단축키 수신 스레드 (ctypes 기반)"""
    new_note_signal = pyqtSignal()
    toggle_all_signal = pyqtSignal()

    def run(self):
        if sys.platform != "win32":
            return
        try:
            user32 = ctypes.windll.user32
            MOD_ALT = 0x0001
            MOD_CONTROL = 0x0002
            VK_N = 0x4E  # N key
            VK_M = 0x4D  # M key
            HOTKEY_ID_NEW = 101
            HOTKEY_ID_TOGGLE = 102

            # Alt + N (새 메모 생성), Alt + M (모든 메모 숨기기/보이기)
            user32.RegisterHotKey(None, HOTKEY_ID_NEW, MOD_ALT, VK_N)
            user32.RegisterHotKey(None, HOTKEY_ID_TOGGLE, MOD_ALT, VK_M)

            msg = wintypes.MSG()
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
                if msg.message == 0x0312:  # WM_HOTKEY
                    if msg.wParam == HOTKEY_ID_NEW:
                        self.new_note_signal.emit()
                    elif msg.wParam == HOTKEY_ID_TOGGLE:
                        self.toggle_all_signal.emit()
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
        except Exception as e:
            print("Hotkey thread notice:", e)


class StickyNoteWindow(QMainWindow):
    def __init__(self, note_id=None, target_date=None, target_time="", content="", color="yellow", is_pinned=0, is_alarm_enabled=0, x=150, y=150, w=380, h=300):
        super().__init__()
        self.note_id = note_id
        self.current_color = color if color in PASTEL_THEMES else "yellow"
        self.is_pinned = bool(is_pinned)
        self.is_alarm_enabled = bool(is_alarm_enabled)
        self.old_pos = None

        # 프레임리스 창 및 윈도우 기본 속성
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.SubWindow)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMinimumWidth(350)
        self.setMinimumHeight(240)
        self.setGeometry(x, y, max(360, w), h)

        if self.is_pinned:
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)

        # 메인 컨테이너 위젯 및 레이아웃
        self.container = QWidget(self)
        self.setCentralWidget(self.container)
        main_layout = QVBoxLayout(self.container)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(4)

        # 상단 타이틀 바 레이아웃
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(2, 2, 2, 2)
        header_layout.setSpacing(2)

        # 날짜 선택기
        self.date_picker = QDateEdit()
        self.date_picker.setCalendarPopup(True)
        self.date_picker.setDisplayFormat("yyyy-MM-dd")
        if target_date:
            self.date_picker.setDate(QDate.fromString(target_date, "yyyy-MM-dd"))
        else:
            self.date_picker.setDate(QDate.currentDate())
        self.date_picker.dateChanged.connect(self.auto_save)
        header_layout.addWidget(self.date_picker)

        # 시간 선택기 (알람 시간)
        self.time_picker = QTimeEdit()
        self.time_picker.setDisplayFormat("HH:mm")
        if target_time:
            self.time_picker.setTime(QTime.fromString(target_time, "HH:mm"))
        else:
            self.time_picker.setTime(QTime.currentTime())
        self.time_picker.timeChanged.connect(self.auto_save)
        header_layout.addWidget(self.time_picker)

        # 알람 켜기/끄기 토글 버튼 (🔔 / 🔕)
        self.alarm_btn = QPushButton("🔔" if self.is_alarm_enabled else "🔕")
        self.alarm_btn.setFixedSize(24, 24)
        self.alarm_btn.setToolTip("알람 켜기/끄기 (지정 시간에 소리 및 토스트 알림)")
        self.alarm_btn.clicked.connect(self.toggle_alarm)
        header_layout.addWidget(self.alarm_btn)

        # 항상 위 핀 버튼
        self.pin_btn = QPushButton("📌" if self.is_pinned else "📍")
        self.pin_btn.setFixedSize(24, 24)
        self.pin_btn.setToolTip("항상 위에 고정 (Ctrl+P)")
        self.pin_btn.clicked.connect(self.toggle_pin)
        header_layout.addWidget(self.pin_btn)

        # 색상 변경 메뉴 버튼
        self.color_btn = QToolButton()
        self.color_btn.setText("🎨")
        self.color_btn.setFixedSize(24, 24)
        self.color_menu = QMenu(self)
        for theme_name in PASTEL_THEMES.keys():
            action = QAction(theme_name.capitalize(), self)
            action.triggered.connect(lambda checked, t=theme_name: self.change_color(t))
            self.color_menu.addAction(action)
        self.color_btn.setMenu(self.color_menu)
        self.color_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        header_layout.addWidget(self.color_btn)

        # 투두 체크박스 추가 버튼
        todo_btn = QPushButton("☑️")
        todo_btn.setFixedSize(24, 24)
        todo_btn.setToolTip("체크박스 투두 추가 (Ctrl+T)")
        todo_btn.clicked.connect(self.add_todo_item)
        header_layout.addWidget(todo_btn)

        # 새 메모 추가 버튼
        new_btn = QPushButton("➕")
        new_btn.setFixedSize(24, 24)
        new_btn.setToolTip("새 일정 메모 (Ctrl+N)")
        new_btn.clicked.connect(self.create_new_window)
        header_layout.addWidget(new_btn)

        # 트레이로 숨기기 (최소화) 버튼
        hide_btn = QPushButton("➖")
        hide_btn.setFixedSize(24, 24)
        hide_btn.setToolTip("트레이로 숨기기 (Esc / Ctrl+H)")
        hide_btn.clicked.connect(self.hide_to_tray)
        header_layout.addWidget(hide_btn)

        # 삭제 버튼
        del_btn = QPushButton("✕")
        del_btn.setFixedSize(24, 24)
        del_btn.setToolTip("삭제 (Ctrl+D)")
        del_btn.clicked.connect(self.delete_note)
        header_layout.addWidget(del_btn)

        main_layout.addLayout(header_layout)

        # 메모 본문 입력창
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(content)
        self.text_edit.setFont(QFont("Malgun Gothic", 10))
        self.text_edit.textChanged.connect(self.auto_save)
        main_layout.addWidget(self.text_edit)

        # 그림자 효과 적용
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(2, 3)
        self.container.setGraphicsEffect(shadow)

        # 인앱 단축키 등록
        self.setup_shortcuts()

        self.apply_style()

        if self.note_id is None:
            self.save_initial()

    def setup_shortcuts(self):
        """창 내부 단축키 바인딩"""
        QShortcut(QKeySequence("Ctrl+N"), self, self.create_new_window)
        QShortcut(QKeySequence("Ctrl+P"), self, self.toggle_pin)
        QShortcut(QKeySequence("Ctrl+T"), self, self.add_todo_item)
        QShortcut(QKeySequence("Ctrl+S"), self, self.auto_save)
        QShortcut(QKeySequence("Ctrl+D"), self, self.delete_note)
        QShortcut(QKeySequence("Ctrl+H"), self, self.hide_to_tray)
        QShortcut(QKeySequence("Escape"), self, self.hide_to_tray)

    def apply_style(self):
        theme = PASTEL_THEMES[self.current_color]
        alarm_style = "background-color: #FDE68A; border: 1.5px solid #F59E0B;" if self.is_alarm_enabled else ""
        style = f"""
            QWidget#centralWidget {{
                background-color: {theme['bg']};
                border: 1px solid {theme['border']};
                border-radius: 8px;
            }}
            QDateEdit, QTimeEdit {{
                background-color: {theme['header']};
                border: 1px solid {theme['border']};
                border-radius: 4px;
                padding: 2px 4px;
                font-weight: bold;
                font-size: 11px;
                color: {theme['text']};
            }}
            QPushButton, QToolButton {{
                background-color: {theme['header']};
                border: 1px solid {theme['border']};
                border-radius: 4px;
                font-size: 11px;
                color: {theme['text']};
            }}
            QPushButton#alarmBtn {{
                {alarm_style}
            }}
            QPushButton:hover, QToolButton:hover {{
                background-color: {theme['border']};
            }}
            QTextEdit {{
                background-color: transparent;
                border: none;
                color: {theme['text']};
                line-height: 1.4;
            }}
        """
        self.alarm_btn.setObjectName("alarmBtn")
        self.container.setObjectName("centralWidget")
        self.container.setStyleSheet(style)

    # 창 드래그 이동 처리
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.old_pos is not None:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.pos() + delta)
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.old_pos = None
        self.auto_save()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.auto_save()

    def toggle_pin(self):
        self.is_pinned = not self.is_pinned
        self.pin_btn.setText("📌" if self.is_pinned else "📍")
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, self.is_pinned)
        self.show()
        self.auto_save()

    def toggle_alarm(self):
        self.is_alarm_enabled = not self.is_alarm_enabled
        self.alarm_btn.setText("🔔" if self.is_alarm_enabled else "🔕")
        self.apply_style()
        self.auto_save()

        target_dt = f"{self.date_picker.date().toString('yyyy-MM-dd')} {self.time_picker.time().toString('HH:mm')}"
        if self.is_alarm_enabled:
            if hasattr(QApplication.instance(), "tray_manager"):
                QApplication.instance().tray_manager.notify("알람 설정 완료", f"{target_dt}에 소리 및 알림이 울립니다.")

    def change_color(self, new_color):
        self.current_color = new_color
        self.apply_style()
        self.auto_save()

    def add_todo_item(self):
        cursor = self.text_edit.textCursor()
        cursor.insertText("\n[ ] ")
        self.text_edit.setTextCursor(cursor)
        self.text_edit.setFocus()
        self.auto_save()

    def hide_to_tray(self):
        self.hide()
        if hasattr(QApplication.instance(), "tray_manager"):
            QApplication.instance().tray_manager.notify("메모 숨김", "메모가 트레이로 최소화되었습니다. (Alt+M 또는 트레이 클릭 시 복원)")

    def save_initial(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        current_date = self.date_picker.date().toString("yyyy-MM-dd")
        current_time = self.time_picker.time().toString("HH:mm")
        current_text = self.text_edit.toPlainText()
        geo = self.geometry()

        cursor.execute(
            """
            INSERT INTO sticky_notes (target_date, target_time, content, color, is_pinned, is_alarm_enabled, pos_x, pos_y, width, height)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                current_date,
                current_time,
                current_text,
                self.current_color,
                1 if self.is_pinned else 0,
                1 if self.is_alarm_enabled else 0,
                geo.x(),
                geo.y(),
                geo.width(),
                geo.height(),
            ),
        )
        self.note_id = cursor.lastrowid
        conn.commit()
        conn.close()

    def auto_save(self):
        if self.note_id is None:
            return
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        current_date = self.date_picker.date().toString("yyyy-MM-dd")
        current_time = self.time_picker.time().toString("HH:mm")
        current_text = self.text_edit.toPlainText()
        geo = self.geometry()

        cursor.execute(
            """
            UPDATE sticky_notes
            SET target_date = ?, target_time = ?, content = ?, color = ?, is_pinned = ?, is_alarm_enabled = ?, pos_x = ?, pos_y = ?, width = ?, height = ?
            WHERE id = ?
            """,
            (
                current_date,
                current_time,
                current_text,
                self.current_color,
                1 if self.is_pinned else 0,
                1 if self.is_alarm_enabled else 0,
                geo.x(),
                geo.y(),
                geo.width(),
                geo.height(),
                self.note_id,
            ),
        )
        conn.commit()
        conn.close()

    def delete_note(self):
        if self.note_id is not None:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sticky_notes WHERE id = ?", (self.note_id,))
            conn.commit()
            conn.close()
        if self in active_windows:
            active_windows.remove(self)
        self.close()

    def create_new_window(self):
        geo = self.geometry()
        color_choices = list(PASTEL_THEMES.keys())
        random_color = random.choice(color_choices)
        new_window = StickyNoteWindow(
            note_id=None,
            target_date=date.today().isoformat(),
            target_time=datetime.now().strftime("%H:%M"),
            content="",
            color=random_color,
            is_pinned=0,
            is_alarm_enabled=0,
            x=geo.x() + 35,
            y=geo.y() + 35,
            w=geo.width(),
            h=geo.height(),
        )
        active_windows.append(new_window)
        new_window.show()


class StickyTrayManager:
    """시스템 트레이 아이콘 및 메뉴 & 알람 스케줄러 & 글로벌 단축키 관리자"""
    def __init__(self, app):
        self.app = app
        self.tray_icon = QSystemTrayIcon(app)
        self.triggered_alarms = set()
        
        # 트레이 아이콘 설정
        icon = QIcon(create_tray_icon_pixmap())
        self.tray_icon.setIcon(icon)
        self.tray_icon.setToolTip("스티커 메모 캘린더 (단축키: Alt+N 새 메모, Alt+M 전체 숨김/표시)")

        # 트레이 컨텍스트 메뉴 생성
        self.menu = QMenu()
        
        action_new = QAction("➕ 새 메모 만들기 (Alt+N)", self.menu)
        action_new.triggered.connect(self.create_new_note)
        self.menu.addAction(action_new)

        self.action_toggle = QAction("👁️ 모든 메모 보이기/숨기기 (Alt+M)", self.menu)
        self.action_toggle.triggered.connect(self.toggle_all_notes)
        self.menu.addAction(self.action_toggle)

        action_align = QAction("🗂️ 화면에 바둑판식 정렬", self.menu)
        action_align.triggered.connect(self.align_notes)
        self.menu.addAction(action_align)

        self.menu.addSeparator()

        action_quit = QAction("🚪 프로그램 완전 종료", self.menu)
        action_quit.triggered.connect(self.exit_app)
        self.menu.addAction(action_quit)

        self.tray_icon.setContextMenu(self.menu)

        # 클릭 / 더블클릭 이벤트 연결 (보이기/숨기기 토글)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

        # 1초마다 알람 트리거 검사 타이머
        self.alarm_timer = QTimer()
        self.alarm_timer.timeout.connect(self.check_alarms)
        self.alarm_timer.start(1000)

        # 글로벌 핫키 수신 백그라운드 스레드 시작
        self.hotkey_thread = GlobalHotkeyThread()
        self.hotkey_thread.new_note_signal.connect(self.create_note_at_cursor)
        self.hotkey_thread.toggle_all_signal.connect(self.toggle_all_notes)
        self.hotkey_thread.start()

    def create_note_at_cursor(self):
        """OS 전역 단축키(Alt+N) 입력 시 마우스 커서 위치에 새 메모 즉시 생성"""
        cursor_pos = QCursor.pos()
        x = max(30, cursor_pos.x() - 150)
        y = max(30, cursor_pos.y() - 50)
        
        color_choices = list(PASTEL_THEMES.keys())
        random_color = random.choice(color_choices)
        w = StickyNoteWindow(
            note_id=None,
            target_date=date.today().isoformat(),
            target_time=datetime.now().strftime("%H:%M"),
            content="",
            color=random_color,
            is_pinned=0,
            is_alarm_enabled=0,
            x=x,
            y=y,
            w=380,
            h=300,
        )
        active_windows.append(w)
        w.show()
        w.raise_()
        w.activateWindow()
        self.notify("새 메모 생성 (Alt+N)", "마우스 커서 위치에 새 포스트잇이 생성되었습니다.")

    def check_alarms(self):
        """설정된 날짜 및 시간에 알람 사운드 및 팝업 토스트 트리거"""
        now = datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        current_time = now.strftime("%H:%M")

        for w in list(active_windows):
            if not w.is_alarm_enabled:
                continue

            note_date = w.date_picker.date().toString("yyyy-MM-dd")
            note_time = w.time_picker.time().toString("HH:mm")

            alarm_key = (w.note_id, current_date, current_time)

            if note_date == current_date and note_time == current_time:
                if alarm_key not in self.triggered_alarms:
                    self.triggered_alarms.add(alarm_key)
                    self.trigger_alarm(w, current_time)

    def trigger_alarm(self, window, time_str):
        """알람 사운드 재생, 창 전면 표시, 시스템 토스트 알림"""
        # 1. 알람 사운드 재생
        if winsound:
            try:
                winsound.Beep(988, 200)   # B5
                winsound.Beep(1319, 400)  # E6
            except Exception:
                QApplication.beep()
        else:
            QApplication.beep()

        # 2. 창 활성화 및 전면 표시
        window.show()
        window.raise_()
        window.activateWindow()

        # 3. 토스트 알림 발송
        content_preview = window.text_edit.toPlainText().strip()
        first_line = content_preview.split('\n')[0][:50] if content_preview else "일정 메모 알람입니다."
        self.notify(f"⏰ [일정 알람] {time_str}", first_line)

    def on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.toggle_all_notes()

    def toggle_all_notes(self):
        """모든 메모 보이기/숨기기 토글 (Alt+M)"""
        if not active_windows:
            self.create_new_note()
            return

        any_visible = any(w.isVisible() for w in active_windows)
        if any_visible:
            for w in active_windows:
                w.hide()
        else:
            for w in active_windows:
                w.show()
                w.raise_()
                w.activateWindow()

    def create_new_note(self):
        """트레이 메뉴에서 새 메모 생성"""
        color_choices = list(PASTEL_THEMES.keys())
        random_color = random.choice(color_choices)
        w = StickyNoteWindow(
            note_id=None,
            target_date=date.today().isoformat(),
            target_time=datetime.now().strftime("%H:%M"),
            content="",
            color=random_color,
            is_pinned=0,
            is_alarm_enabled=0,
            x=200 + random.randint(0, 100),
            y=150 + random.randint(0, 100),
            w=340,
            h=300,
        )
        active_windows.append(w)
        w.show()
        w.raise_()
        w.activateWindow()

    def align_notes(self):
        """화면에 활성 메모들을 바둑판 형태로 자동 정렬"""
        visible_windows = [w for w in active_windows if w.isVisible()]
        if not visible_windows:
            for w in active_windows:
                w.show()
            visible_windows = active_windows

        start_x, start_y = 50, 50
        gap = 20
        col_w, row_h = 350, 310
        max_cols = 4

        for idx, w in enumerate(visible_windows):
            col = idx % max_cols
            row = idx // max_cols
            new_x = start_x + col * (col_w + gap)
            new_y = start_y + row * (row_h + gap)
            w.move(new_x, new_y)
            w.auto_save()

    def notify(self, title, message):
        """풍선 도움말 토스트 알림"""
        self.tray_icon.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 4000)

    def exit_app(self):
        """프로그램 완전 종료 및 핫키 해제"""
        try:
            if sys.platform == "win32":
                user32 = ctypes.windll.user32
                user32.UnregisterHotKey(None, 101)
                user32.UnregisterHotKey(None, 102)
        except Exception:
            pass
        self.tray_icon.hide()
        self.app.quit()


def main():
    init_db()
    app = QApplication(sys.argv)
    
    # 애플리케이션 아이콘 설정
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # 마지막 창이 닫혀도 시스템 트레이에서 계속 실행 유지
    app.setQuitOnLastWindowClosed(False)

    # 시스템 트레이 관리자 활성화
    tray_manager = StickyTrayManager(app)
    app.tray_manager = tray_manager

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, target_date, target_time, content, color, is_pinned, is_alarm_enabled, pos_x, pos_y, width, height
        FROM sticky_notes
        """
    )
    rows = cursor.fetchall()
    conn.close()

    if rows:
        for row in rows:
            w = StickyNoteWindow(
                note_id=row[0],
                target_date=row[1],
                target_time=row[2] or "",
                content=row[3],
                color=row[4],
                is_pinned=row[5],
                is_alarm_enabled=row[6] or 0,
                x=row[7],
                y=row[8],
                w=max(360, row[9]),
                h=row[10],
            )
            active_windows.append(w)
            w.show()
    else:
        # 최초 실행 시 기본 메모 하나 생성
        initial_note = StickyNoteWindow(
            note_id=None,
            target_date=date.today().isoformat(),
            target_time=datetime.now().strftime("%H:%M"),
            content="[ ] 오늘 할 일 1\n[ ] 오늘 할 일 2\n[ ] 상단 🔔 버튼으로 알람 켜기\n[ ] 어디서든 Alt+N으로 새 메모 생성",
            color="yellow",
            is_pinned=0,
            is_alarm_enabled=0,
            x=200,
            y=200,
            w=380,
            h=300,
        )
        active_windows.append(initial_note)
        initial_note.show()

    # 트레이 실행 안내 알림
    tray_manager.notify("스티커 메모 캘린더 시작", "글로벌 단축키 활성화됨:\n- Alt+N: 마우스 위치에 새 메모\n- Alt+M: 전체 숨김/표시")

    sys.exit(app.exec())

if __name__ == "__main__":
    main()

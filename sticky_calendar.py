import sys
import os
import sqlite3
import random
import re
from datetime import date, datetime, timedelta
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
        QStackedWidget,
        QScrollArea,
        QCheckBox,
        QLineEdit,
        QLabel,
        QCalendarWidget,
        QDialog,
        QListWidget,
        QListWidgetItem,
        QFrame,
        QMessageBox,
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
        QTextCharFormat,
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
        QStackedWidget,
        QScrollArea,
        QCheckBox,
        QLineEdit,
        QLabel,
        QCalendarWidget,
        QDialog,
        QListWidget,
        QListWidgetItem,
        QFrame,
        QMessageBox,
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
        QTextCharFormat,
    )

try:
    import winsound
except ImportError:
    winsound = None

try:
    import winreg
except ImportError:
    winreg = None

# DB 경로 설정 (exe 패키징 및 로컬 실행 간 데이터 완벽 보존 및 동기화)
def get_db_path():
    app_data_dir = os.path.join(os.getenv("APPDATA", os.path.expanduser("~")), "StickyCalendar")
    os.makedirs(app_data_dir, exist_ok=True)
    appdata_db = os.path.join(app_data_dir, "sticky_notes.db")
    local_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sticky_notes.db")

    # 로컬 DB가 존재하고 AppData DB가 비어있거나 없으면 자동 마이그레이션
    if os.path.exists(local_db):
        if not os.path.exists(appdata_db) or (os.path.getsize(appdata_db) < 1000 and os.path.getsize(local_db) > 1000):
            try:
                import shutil
                shutil.copy2(local_db, appdata_db)
            except Exception:
                pass

    if getattr(sys, 'frozen', False):
        return appdata_db
    else:
        return appdata_db if os.path.exists(appdata_db) else local_db

DB_PATH = get_db_path()

# Windows 부팅 시 자동 시작(Auto-start) 레지스트리 관리
def get_app_command():
    """현재 실행 중인 실행 파일 또는 스크립트 실행 명령어 반환"""
    if getattr(sys, 'frozen', False):
        return f'"{os.path.abspath(sys.executable)}"'
    else:
        python_exe = os.path.abspath(sys.executable)
        script = os.path.abspath(__file__)
        return f'"{python_exe}" "{script}"'

def is_autostart_enabled() -> bool:
    """윈도우 부팅 시 자동 실행 등록 여부 확인"""
    if sys.platform != "win32" or not winreg:
        return False
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_READ
        )
        val, _ = winreg.QueryValueEx(key, "StickyCalendar")
        winreg.CloseKey(key)
        return bool(val)
    except FileNotFoundError:
        return False
    except Exception:
        return False

def set_autostart(enable: bool) -> bool:
    """윈도우 부팅 시 자동 실행 등록 또는 해제 (경로 변경 시 자동 갱신)"""
    if sys.platform != "win32" or not winreg:
        return False
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE
        )
        if enable:
            cmd = get_app_command()
            winreg.SetValueEx(key, "StickyCalendar", 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(key, "StickyCalendar")
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"Autostart configuration error: {e}")
        return False

# 파스텔 톤 테마 정의 (배경색, 헤더색, 테두리색, 악센트색, 텍스트색) - 노션/애플 감성 모던 팔레트
PASTEL_THEMES = {
    "yellow": {"bg": "#FFFDF0", "header": "#FEF3C7", "border": "#FDE68A", "accent": "#D97706", "text": "#1F2937"},
    "blue": {"bg": "#F0F9FF", "header": "#E0F2FE", "border": "#BAE6FD", "accent": "#0284C7", "text": "#1F2937"},
    "green": {"bg": "#F0FDF4", "header": "#DCFCE7", "border": "#BBF7D0", "accent": "#16A34A", "text": "#1F2937"},
    "orange": {"bg": "#FFF7ED", "header": "#FFEDD5", "border": "#FED7AA", "accent": "#EA580C", "text": "#1F2937"},
    "purple": {"bg": "#FAF5FF", "header": "#F3E8FF", "border": "#E9D5FF", "accent": "#9333EA", "text": "#1F2937"},
}

def create_tray_icon_pixmap(is_alert=False):
    """트레이용 귀여운 포스트잇 픽스맵 아이콘 생성 (알람 시 빨간색/금색 알람 버전 지원)"""
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    if is_alert:
        # 반짝이는 경고 배경 (강렬한 주황/빨강)
        painter.setBrush(QBrush(QColor("#EF4444")))
        painter.setPen(QPen(QColor("#DC2626"), 1.5))
        painter.drawRoundedRect(2, 2, 28, 28, 6, 6)

        # 밝은 황금색 벨 아이콘 모양 그리기
        painter.setBrush(QBrush(QColor("#FDE047")))
        painter.setPen(QPen(QColor("#CA8A04"), 1))
        painter.drawEllipse(11, 7, 10, 10)
        painter.drawChord(7, 12, 18, 12, 0, 180 * 16)
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        painter.drawEllipse(14, 22, 4, 4)
    else:
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

def get_advance_time(date_str, time_str, minutes=10):
    """지정 날짜 및 시간의 N분 전 날짜/시간(HH:mm) 계산 (자정 경계 자동 처리)"""
    try:
        dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        adv = dt - timedelta(minutes=minutes)
        return adv.strftime("%Y-%m-%d"), adv.strftime("%H:%M")
    except Exception:
        return None, None

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS sticky_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_date TEXT,
            target_time TEXT,
            content TEXT,
            color TEXT,
            is_pinned INTEGER DEFAULT 0,
            is_alarm_enabled INTEGER DEFAULT 0,
            pos_x INTEGER,
            pos_y INTEGER,
            width INTEGER,
            height INTEGER
        )
        """
    )
    cursor.execute("PRAGMA table_info(sticky_notes)")
    columns = [col[1] for col in cursor.fetchall()]
    if "target_time" not in columns:
        cursor.execute("ALTER TABLE sticky_notes ADD COLUMN target_time TEXT DEFAULT '09:00'")
    if "is_alarm_enabled" not in columns:
        cursor.execute("ALTER TABLE sticky_notes ADD COLUMN is_alarm_enabled INTEGER DEFAULT 0")
    if "is_visible" not in columns:
        cursor.execute("ALTER TABLE sticky_notes ADD COLUMN is_visible INTEGER DEFAULT 1")
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


class TodoItemWidget(QWidget):
    """인터랙티브 체크박스 할 일 항목 위젯 (체크, 취소선, 개별 시간 지정, 텍스트 수정, 개별 삭제 지원)"""
    changed_signal = pyqtSignal()
    delete_signal = pyqtSignal(object)
    create_next_signal = pyqtSignal(object)

    def __init__(self, checked=False, time_str=None, text="", text_color="#333333", parent=None):
        super().__init__(parent)
        self.text_color = text_color
        self.has_time = bool(time_str)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)

        # 1. 완료 체크박스
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(checked)
        self.checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        self.checkbox.stateChanged.connect(self.on_check_changed)
        layout.addWidget(self.checkbox)

        # 2. 개별 시간 토글 버튼 (⏰)
        self.time_btn = QPushButton("⏰")
        self.time_btn.setFixedSize(24, 24)
        self.time_btn.setToolTip("이 할 일의 개별 알람 시간 지정 / 해제 (클릭)")
        self.time_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.time_btn.clicked.connect(self.toggle_time)
        layout.addWidget(self.time_btn)

        # 3. 개별 시간 편집기 (QTimeEdit)
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setFixedSize(64, 24)
        self.time_edit.setStyleSheet("QTimeEdit { background: rgba(255, 255, 255, 0.85); border: 1px solid rgba(0, 0, 0, 0.12); border-radius: 4px; padding: 1px 3px; font-size: 11px; font-weight: 600; color: #1E293B; }")
        self.time_edit.setToolTip("할 일 시작 및 알람 시간")
        if time_str:
            t = QTime.fromString(time_str, "HH:mm")
            if t.isValid():
                self.time_edit.setTime(t)
            else:
                self.time_edit.setTime(QTime.currentTime())
        else:
            self.time_edit.setTime(QTime.currentTime())
        self.time_edit.timeChanged.connect(lambda: self.changed_signal.emit())
        self.time_edit.setVisible(self.has_time)
        layout.addWidget(self.time_edit)

        # 4. 할 일 내용 입력 (QLineEdit)
        self.line_edit = QLineEdit(text)
        self.line_edit.setPlaceholderText("할 일 내용 입력...")
        self.line_edit.setFont(QFont("Malgun Gothic", 10))
        self.line_edit.textChanged.connect(self.on_text_changed)
        self.line_edit.returnPressed.connect(lambda: self.create_next_signal.emit(self))
        self.line_edit.installEventFilter(self)
        layout.addWidget(self.line_edit, stretch=1)

        # 5. 개별 삭제 버튼 (✕)
        self.del_btn = QPushButton("✕")
        self.del_btn.setFixedSize(22, 22)
        self.del_btn.setToolTip("이 할 일 삭제")
        self.del_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 4px;
                color: #94A3B8;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #FEE2E2;
                color: #EF4444;
            }
        """)
        self.del_btn.clicked.connect(lambda: self.delete_signal.emit(self))
        layout.addWidget(self.del_btn)

        self.update_time_btn_style()
        self.update_style(checked)

    def toggle_time(self):
        self.has_time = not self.has_time
        self.time_edit.setVisible(self.has_time)
        self.update_time_btn_style()
        self.changed_signal.emit()

    def update_time_btn_style(self):
        if self.has_time:
            self.time_btn.setStyleSheet("""
                QPushButton {
                    background: #6366F1;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    font-size: 12px;
                }
            """)
        else:
            self.time_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(0, 0, 0, 0.04);
                    color: #94A3B8;
                    border: 1px solid rgba(0, 0, 0, 0.06);
                    border-radius: 6px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background: rgba(99, 102, 241, 0.15);
                    color: #4F46E5;
                }
            """)

    def on_text_changed(self):
        # 텍스트에 "14:00 미팅" 또는 "[14:00] 미팅" 형태가 입력되면 자동으로 시간 인식
        txt = self.line_edit.text()
        m = re.match(r'^\[?(\d{1,2}:\d{2})\]?\s+(.*)$', txt)
        if m:
            t_str = m.group(1)
            rest_txt = m.group(2)
            t = QTime.fromString(t_str, "HH:mm")
            if t.isValid():
                self.time_edit.setTime(t)
                self.has_time = True
                self.time_edit.setVisible(True)
                self.update_time_btn_style()
                self.line_edit.blockSignals(True)
                self.line_edit.setText(rest_txt)
                self.line_edit.blockSignals(False)
        self.changed_signal.emit()

    def on_check_changed(self, state):
        is_checked = (state == Qt.CheckState.Checked.value or state == 2)
        self.update_style(is_checked)
        self.changed_signal.emit()

    def update_style(self, checked):
        font = self.line_edit.font()
        font.setStrikeOut(checked)
        self.line_edit.setFont(font)
        if checked:
            self.line_edit.setStyleSheet("QLineEdit { background: transparent; border: none; font-size: 13px; color: #94a3b8; text-decoration: line-through; }")
        else:
            self.line_edit.setStyleSheet(f"QLineEdit {{ background: transparent; border: none; font-size: 13px; color: {self.text_color}; }}")

    def set_text_color(self, color):
        self.text_color = color
        self.update_style(self.checkbox.isChecked())

    def eventFilter(self, obj, event):
        if obj == self.line_edit and event.type() == event.Type.KeyPress:
            if event.key() == Qt.Key.Key_Backspace and self.line_edit.text() == "":
                self.delete_signal.emit(self)
                return True
        return super().eventFilter(obj, event)

    def is_checked(self):
        return self.checkbox.isChecked()

    def get_time(self):
        if self.has_time:
            return self.time_edit.time().toString("HH:mm")
        return None

    def get_text(self):
        return self.line_edit.text().strip()

    def get_serialized_line(self):
        check_str = "[x]" if self.checkbox.isChecked() else "[ ]"
        txt = self.line_edit.text().strip()
        if self.has_time:
            time_str = self.time_edit.time().toString("HH:mm")
            return f"{check_str} [{time_str}] {txt}"
        else:
            return f"{check_str} {txt}"


class CalendarWindow(QMainWindow):
    """월간 달력 뷰 및 날짜별 메모 모아보기 (비모달 독립 윈도우 - 모던 노션/애플 캘린더 감성)"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📅 캘린더 뷰 - 월간 일정 및 메모")
        self.resize(560, 640)
        self.setMinimumSize(500, 560)
        self._highlighted_dates = set()

        container = QWidget(self)
        container.setObjectName("calContainer")
        self.setCentralWidget(container)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # 상단 타이틀 바
        title_layout = QHBoxLayout()
        title_label = QLabel("📅  월간 캘린더 & 일정 모아보기")
        title_label.setFont(QFont("Malgun Gothic", 13, QFont.Weight.Bold))
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setObjectName("closeHeaderBtn")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.close)
        title_layout.addWidget(close_btn)
        layout.addLayout(title_layout)

        # QCalendarWidget (모던 스타일 적용)
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.calendar.selectionChanged.connect(self.on_date_selected)
        layout.addWidget(self.calendar)

        # 요약 레이블
        self.summary_label = QLabel("📌 날짜를 클릭하면 해당 일자의 메모 및 할 일이 표시됩니다:")
        self.summary_label.setFont(QFont("Malgun Gothic", 10, QFont.Weight.Bold))
        layout.addWidget(self.summary_label)

        # 메모 리스트
        self.notes_list = QListWidget()
        self.notes_list.itemDoubleClicked.connect(self.on_item_double_clicked)
        layout.addWidget(self.notes_list)

        # 하단 액션 버튼
        btn_layout = QHBoxLayout()
        self.new_note_btn = QPushButton("➕  선택한 날짜에 새 메모 만들기")
        self.new_note_btn.setObjectName("primaryBtn")
        self.new_note_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.new_note_btn.clicked.connect(self.create_note_for_selected_date)
        btn_layout.addWidget(self.new_note_btn)

        close_bottom_btn = QPushButton("닫기")
        close_bottom_btn.setObjectName("secondaryBtn")
        close_bottom_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_bottom_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_bottom_btn)
        layout.addLayout(btn_layout)

        self.apply_theme()
        self.highlight_calendar_dates()
        self.on_date_selected()

    def select_date(self, date_str):
        qdate = QDate.fromString(date_str, "yyyy-MM-dd")
        if qdate.isValid():
            self.calendar.setSelectedDate(qdate)
            self.on_date_selected()

    def apply_theme(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #F8FAFC;
            }
            QWidget#calContainer {
                background-color: #F8FAFC;
            }
            QLabel {
                color: #1E293B;
                font-family: 'Malgun Gothic', 'Pretendard', sans-serif;
            }
            /* QCalendarWidget Modern Design */
            QCalendarWidget {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
            }
            QCalendarWidget QWidget#qt_calendar_navigationbar {
                background-color: #FFFFFF;
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
                border-bottom: 1px solid #E2E8F0;
                min-height: 48px;
            }
            QCalendarWidget QToolButton {
                color: #0F172A;
                font-family: 'Malgun Gothic', 'Pretendard', sans-serif;
                font-size: 13px;
                font-weight: 700;
                background-color: transparent;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                margin: 2px 4px;
            }
            QCalendarWidget QToolButton:hover {
                background-color: #F1F5F9;
                color: #4F46E5;
            }
            QCalendarWidget QToolButton#qt_calendar_prevmonth {
                font-size: 14px;
                font-weight: bold;
            }
            QCalendarWidget QToolButton#qt_calendar_nextmonth {
                font-size: 14px;
                font-weight: bold;
            }
            QCalendarWidget QTableView {
                background-color: #FFFFFF;
                selection-background-color: #4F46E5;
                selection-color: #FFFFFF;
                gridline-color: #F8FAFC;
                border: none;
                font-size: 13px;
                outline: 0;
            }
            QCalendarWidget QTableView::item {
                border-radius: 6px;
                padding: 4px;
            }
            QCalendarWidget QTableView::item:hover {
                background-color: #EEF2FF;
            }
            QCalendarWidget QTableView::item:selected {
                background-color: #4F46E5;
                color: #FFFFFF;
                font-weight: bold;
            }
            QCalendarWidget QHeaderView::section {
                background-color: #F8FAFC;
                color: #64748B;
                font-weight: 600;
                font-size: 12px;
                padding: 6px 0;
                border: none;
                border-bottom: 1px solid #E2E8F0;
            }
            /* QListWidget Modern Cards */
            QListWidget {
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
                padding: 8px;
                font-size: 13px;
                color: #1E293B;
            }
            QListWidget::item {
                padding: 8px 12px;
                margin-bottom: 4px;
                border-radius: 8px;
                border-bottom: 1px solid #F8FAFC;
            }
            QListWidget::item:hover {
                background: #F8FAFC;
            }
            QListWidget::item:selected {
                background: #EEF2FF;
                color: #312E81;
                border: 1px solid #C7D2FE;
            }
            /* Buttons */
            QPushButton#primaryBtn {
                background-color: #4F46E5;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton#primaryBtn:hover {
                background-color: #4338CA;
            }
            QPushButton#secondaryBtn {
                background-color: #FFFFFF;
                color: #475569;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                padding: 10px 18px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton#secondaryBtn:hover {
                background-color: #F1F5F9;
                color: #0F172A;
            }
            QPushButton#closeHeaderBtn {
                background-color: transparent;
                color: #94A3B8;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton#closeHeaderBtn:hover {
                background-color: #FEE2E2;
                color: #EF4444;
            }
        """)

    def highlight_calendar_dates(self):
        """메모가 있는 날짜들을 캘린더에 세련된 보라/인디고 배지로 하이라이트 (이전 포맷 초기화로 파란색 잔상 버그 완벽 방지)"""
        empty_fmt = QTextCharFormat()
        if hasattr(self, "_highlighted_dates"):
            for old_qdate in self._highlighted_dates:
                self.calendar.setDateTextFormat(old_qdate, empty_fmt)
        self._highlighted_dates = set()

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT target_date FROM sticky_notes WHERE target_date IS NOT NULL AND target_date != ''")
        rows = cursor.fetchall()
        conn.close()

        fmt = QTextCharFormat()
        fmt.setFontWeight(QFont.Weight.Bold)
        fmt.setForeground(QColor("#4F46E5"))
        fmt.setBackground(QColor("#EEF2FF"))

        for (target_date_str,) in rows:
            qdate = QDate.fromString(target_date_str, "yyyy-MM-dd")
            if qdate.isValid():
                self.calendar.setDateTextFormat(qdate, fmt)
                self._highlighted_dates.add(qdate)

    def on_date_selected(self):
        sel_date = self.calendar.selectedDate().toString("yyyy-MM-dd")
        self.notes_list.clear()

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, content, color, target_time, is_pinned, is_alarm_enabled FROM sticky_notes WHERE target_date = ?",
            (sel_date,)
        )
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            self.summary_label.setText(f"📅  {sel_date} 일정 & 할 일 (0개)")
            item = QListWidgetItem("등록된 메모나 할 일이 없습니다. 아래 버튼으로 새 메모를 만들어보세요!")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            item.setForeground(QColor("#94A3B8"))
            self.notes_list.addItem(item)
            return

        total_items_count = 0
        theme_names = {
            "yellow": "🟡 노랑",
            "blue": "🔵 파랑",
            "green": "🟢 초록",
            "orange": "🟠 주황",
            "purple": "🟣 보라",
        }

        for row in rows:
            note_id, content, color, target_time, is_pinned, is_alarm = row
            lines = [l.strip() for l in content.split('\n') if l.strip()]

            pin_str = "📌 " if is_pinned else ""
            alarm_str = "🔔 " if is_alarm else ""
            time_str = f"⏰ {target_time}  " if target_time else ""
            c_label = theme_names.get(color, f"📝 {color.capitalize()}")

            # 메모 헤더 카드 아이템
            header_item = QListWidgetItem(f"{c_label} 메모  {time_str}{pin_str}{alarm_str}")
            header_item.setFont(QFont("Malgun Gothic", 10, QFont.Weight.Bold))
            header_item.setData(Qt.ItemDataRole.UserRole, note_id)
            header_item.setBackground(QColor("#F1F5F9"))
            header_item.setForeground(QColor("#0F172A"))
            self.notes_list.addItem(header_item)

            if not lines:
                sub_item = QListWidgetItem("      (내용 없음 - 더블클릭하여 열기)")
                sub_item.setData(Qt.ItemDataRole.UserRole, note_id)
                sub_item.setForeground(QColor("#94A3B8"))
                self.notes_list.addItem(sub_item)
                total_items_count += 1
            else:
                for line in lines:
                    total_items_count += 1
                    m = re.match(r'^\[([ xX])\]\s*(?:\[(\d{1,2}:\d{2})\]\s*|(\d{1,2}:\d{2})\s+)?(.*)$', line)
                    if m:
                        is_checked = (m.group(1).lower() == 'x')
                        item_time = m.group(2) or m.group(3)
                        item_txt = m.group(4)

                        status_str = "☑️" if is_checked else "⬜"
                        t_str = f"[{item_time}] " if item_time else ""
                        check_label = f"     {status_str}  {t_str}{item_txt}"
                        if is_checked:
                            check_label += "  ✓ 완료"

                        sub_item = QListWidgetItem(check_label)
                        sub_item.setData(Qt.ItemDataRole.UserRole, note_id)
                        if is_checked:
                            sub_item.setForeground(QColor("#94A3B8"))
                        else:
                            sub_item.setForeground(QColor("#1E293B"))
                        self.notes_list.addItem(sub_item)
                    else:
                        sub_item = QListWidgetItem(f"     •  {line}")
                        sub_item.setData(Qt.ItemDataRole.UserRole, note_id)
                        sub_item.setForeground(QColor("#334155"))
                        self.notes_list.addItem(sub_item)

        self.summary_label.setText(f"📅  {sel_date} 일정 & 할 일 ({len(rows)}개 메모, 총 {total_items_count}개 항목)  •  더블클릭 시 열기")

    def on_item_double_clicked(self, item):
        note_id = item.data(Qt.ItemDataRole.UserRole)
        if not note_id:
            return

        # 1. 이미 active_windows에 존재하는 경우: 전면 표시 & 포커스
        for w in active_windows:
            if w.note_id == note_id:
                w.show()
                w.raise_()
                w.activateWindow()
                conn = sqlite3.connect(DB_PATH)
                conn.execute("UPDATE sticky_notes SET is_visible = 1 WHERE id = ?", (note_id,))
                conn.commit()
                conn.close()
                return

        # 2. 닫혀 있어서 active_windows에 없는 경우: DB에서 안전하게 불러와서 창 복원!
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, target_date, target_time, content, color, is_pinned, is_alarm_enabled, pos_x, pos_y, width, height FROM sticky_notes WHERE id = ?",
            (note_id,)
        )
        row = cursor.fetchone()
        if row:
            cursor.execute("UPDATE sticky_notes SET is_visible = 1 WHERE id = ?", (note_id,))
            conn.commit()
        conn.close()

        if row:
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
                w=max(460, row[9]),
                h=max(300, row[10]),
            )
            active_windows.append(w)
            w.show()
            w.raise_()
            w.activateWindow()
            w.activateWindow()

    def create_note_for_selected_date(self):
        sel_date = self.calendar.selectedDate().toString("yyyy-MM-dd")
        if hasattr(QApplication.instance(), "tray_manager"):
            w = QApplication.instance().tray_manager.create_new_note(target_date=sel_date)
            self.highlight_calendar_dates()
            self.on_date_selected()


class StickyNoteWindow(QMainWindow):
    def __init__(self, note_id=None, target_date=None, target_time="", content="", color="yellow", is_pinned=0, is_alarm_enabled=0, x=150, y=150, w=480, h=330):
        super().__init__()
        self.note_id = note_id
        self.current_color = color if color in PASTEL_THEMES else "yellow"
        self.is_pinned = bool(is_pinned)
        self.is_alarm_enabled = bool(is_alarm_enabled)
        self.old_pos = None

        # 내용에 [ ] 또는 [x] 패턴이 있으면 자동으로 체크리스트 모드로 시작
        self.is_todo_mode = bool(re.search(r'\[( |x)\]', content, re.IGNORECASE))
        self.todo_items = []

        # 프레임리스 창 및 윈도우 기본 속성
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMinimumWidth(460)
        self.setMinimumHeight(260)
        self.setGeometry(x, y, max(460, w), max(300, h))

        if self.is_pinned:
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)

        # 메인 컨테이너 위젯 및 레이아웃
        self.container = QWidget(self)
        self.setCentralWidget(self.container)
        main_layout = QVBoxLayout(self.container)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(6)

        # 상단 타이틀 바 레이아웃 (충분한 호흡과 여백 확보)
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(4, 2, 4, 4)
        header_layout.setSpacing(4)

        # 1. 날짜 선택기 (잘림 방지 최적화 너비)
        self.date_picker = QDateEdit()
        self.date_picker.setCalendarPopup(True)
        self.date_picker.setDisplayFormat("yyyy-MM-dd")
        self.date_picker.setMinimumWidth(125)
        self.date_picker.setFixedHeight(28)
        if target_date:
            self.date_picker.setDate(QDate.fromString(target_date, "yyyy-MM-dd"))
        else:
            self.date_picker.setDate(QDate.currentDate())
        self.date_picker.dateChanged.connect(self.auto_save)
        header_layout.addWidget(self.date_picker)

        # 2. 시간 선택기 (알람 시간)
        self.time_picker = QTimeEdit()
        self.time_picker.setDisplayFormat("HH:mm")
        self.time_picker.setMinimumWidth(72)
        self.time_picker.setFixedHeight(28)
        if target_time:
            self.time_picker.setTime(QTime.fromString(target_time, "HH:mm"))
        else:
            self.time_picker.setTime(QTime.currentTime())
        self.time_picker.timeChanged.connect(self.auto_save)
        header_layout.addWidget(self.time_picker)

        header_layout.addSpacing(6)
        header_layout.addStretch()

        # 3. 캘린더 뷰 팝업 버튼 (📅)
        self.cal_btn = QPushButton("📅")
        self.cal_btn.setFixedSize(26, 26)
        self.cal_btn.setToolTip("월간 캘린더 & 일정 모아보기")
        self.cal_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cal_btn.clicked.connect(self.open_calendar_view)
        header_layout.addWidget(self.cal_btn)

        # 4. 알람 켜기/끄기 토글 버튼 (🔔 / 🔕)
        self.alarm_btn = QPushButton("🔔" if self.is_alarm_enabled else "🔕")
        self.alarm_btn.setFixedSize(26, 26)
        self.alarm_btn.setToolTip("알람 켜기/끄기 (지정 시간에 소리 및 토스트 알림)")
        self.alarm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.alarm_btn.clicked.connect(self.toggle_alarm)
        header_layout.addWidget(self.alarm_btn)

        # 5. 모드 전환 버튼 (체크리스트 ☑️ / 일반 텍스트 📝)
        self.mode_btn = QPushButton("📝" if self.is_todo_mode else "☑️")
        self.mode_btn.setFixedSize(26, 26)
        self.mode_btn.setToolTip("체크리스트/텍스트 모드 전환 (Ctrl+T)")
        self.mode_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mode_btn.clicked.connect(self.toggle_mode)
        header_layout.addWidget(self.mode_btn)

        # 6. 항상 위 핀 버튼
        self.pin_btn = QPushButton("📌" if self.is_pinned else "📍")
        self.pin_btn.setFixedSize(26, 26)
        self.pin_btn.setToolTip("항상 위에 고정 (Ctrl+P)")
        self.pin_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pin_btn.clicked.connect(self.toggle_pin)
        header_layout.addWidget(self.pin_btn)

        # 7. 색상 변경 메뉴 버튼
        self.color_btn = QToolButton()
        self.color_btn.setText("🎨")
        self.color_btn.setFixedSize(26, 26)
        self.color_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.color_menu = QMenu(self)
        for theme_name in PASTEL_THEMES.keys():
            action = QAction(theme_name.capitalize(), self)
            action.triggered.connect(lambda checked, t=theme_name: self.change_color(t))
            self.color_menu.addAction(action)
        self.color_btn.setMenu(self.color_menu)
        self.color_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        header_layout.addWidget(self.color_btn)

        # 8. 새 메모 추가 버튼
        new_btn = QPushButton("➕")
        new_btn.setFixedSize(26, 26)
        new_btn.setToolTip("새 일정 메모 (Ctrl+N)")
        new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        new_btn.clicked.connect(self.create_new_window)
        header_layout.addWidget(new_btn)

        # 9. 트레이로 숨기기 (최소화) 버튼
        hide_btn = QPushButton("➖")
        hide_btn.setFixedSize(26, 26)
        hide_btn.setToolTip("트레이로 최소화 (Ctrl+H)")
        hide_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        hide_btn.clicked.connect(self.hide_to_tray)
        header_layout.addWidget(hide_btn)

        # 10. 메모 완전 삭제 버튼 (🗑️)
        del_btn = QPushButton("🗑️")
        del_btn.setObjectName("delBtn")
        del_btn.setFixedSize(26, 26)
        del_btn.setToolTip("메모 완전 삭제 (캘린더에서도 완전히 삭제, Ctrl+D)")
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.clicked.connect(self.confirm_delete_note)
        header_layout.addWidget(del_btn)

        # 11. 창 닫기 버튼 (✕ - 닫아도 캘린더와 DB에 안전하게 보존됨)
        close_btn = QPushButton("✕")
        close_btn.setObjectName("closeBtn")
        close_btn.setFixedSize(26, 26)
        close_btn.setToolTip("창 닫기 (캘린더와 DB에 안전하게 영구 보존됨, Esc)")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.close_note)
        header_layout.addWidget(close_btn)

        main_layout.addLayout(header_layout)

        # 본문 스택 위젯 (0: 일반 텍스트 에디터, 1: 인터랙티브 체크리스트)
        self.stacked_body = QStackedWidget()

        # Page 0: 일반 텍스트 에디터
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(content)
        self.text_edit.setFont(QFont("Malgun Gothic", 10))
        self.text_edit.textChanged.connect(self.auto_save)
        self.stacked_body.addWidget(self.text_edit)

        # Page 1: 체크박스 투두 뷰
        self.todo_scroll = QScrollArea()
        self.todo_scroll.setWidgetResizable(True)
        self.todo_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.todo_scroll_content = QWidget()
        self.todo_main_layout = QVBoxLayout(self.todo_scroll_content)
        self.todo_main_layout.setContentsMargins(2, 2, 2, 2)
        self.todo_main_layout.setSpacing(4)

        # 실제 항목들이 들어갈 레이아웃
        self.todo_list_container = QWidget()
        self.todo_list_layout = QVBoxLayout(self.todo_list_container)
        self.todo_list_layout.setContentsMargins(0, 0, 0, 0)
        self.todo_list_layout.setSpacing(2)
        self.todo_main_layout.addWidget(self.todo_list_container)

        # 투두 추가 인풋 & 완료 정리 툴바
        self.todo_toolbar_layout = QVBoxLayout()
        self.todo_toolbar_layout.setContentsMargins(0, 4, 0, 0)
        self.todo_toolbar_layout.setSpacing(4)

        self.add_todo_input = QLineEdit()
        self.add_todo_input.setObjectName("addTodoInput")
        self.add_todo_input.setFixedHeight(34)
        self.add_todo_input.setPlaceholderText("+ 새 할 일 추가 (입력 후 Enter)...")
        self.add_todo_input.setFont(QFont("Malgun Gothic", 10))
        self.add_todo_input.returnPressed.connect(self.on_add_input_enter)
        self.todo_toolbar_layout.addWidget(self.add_todo_input)

        self.clear_completed_btn = QPushButton("🧹 완료 항목 정리")
        self.clear_completed_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_completed_btn.clicked.connect(self.clear_completed_todos)
        self.todo_toolbar_layout.addWidget(self.clear_completed_btn)

        self.todo_main_layout.addLayout(self.todo_toolbar_layout)
        self.todo_main_layout.addStretch()

        self.todo_scroll.setWidget(self.todo_scroll_content)
        self.stacked_body.addWidget(self.todo_scroll)

        main_layout.addWidget(self.stacked_body)

        # 초기 모드 설정
        if self.is_todo_mode:
            self.populate_todo_view(content)
            self.stacked_body.setCurrentIndex(1)
        else:
            self.stacked_body.setCurrentIndex(0)

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

    def open_calendar_view(self):
        """월간 캘린더 창 띄우기 (비모달)"""
        target_dt = self.date_picker.date().toString("yyyy-MM-dd")
        if hasattr(QApplication.instance(), "tray_manager"):
            QApplication.instance().tray_manager.open_calendar_dialog(target_date=target_dt)
        else:
            if not hasattr(self, "_cal_win") or self._cal_win is None:
                self._cal_win = CalendarWindow()
            self._cal_win.select_date(target_dt)
            self._cal_win.show()
            self._cal_win.raise_()
            self._cal_win.activateWindow()

    def toggle_mode(self):
        """일반 텍스트 모드 <-> 인터랙티브 체크박스 모드 상호 전환"""
        theme = PASTEL_THEMES[self.current_color]
        if self.is_todo_mode:
            # 텍스트 모드로 전환
            content = self.get_current_content()
            self.text_edit.setPlainText(content)
            self.stacked_body.setCurrentIndex(0)
            self.is_todo_mode = False
            self.mode_btn.setText("☑️")
            self.mode_btn.setToolTip("체크리스트 모드로 전환 (Ctrl+T)")
        else:
            # 체크리스트 모드로 전환
            content = self.text_edit.toPlainText()
            self.populate_todo_view(content)
            self.stacked_body.setCurrentIndex(1)
            self.is_todo_mode = True
            self.mode_btn.setText("📝")
            self.mode_btn.setToolTip("일반 텍스트 모드로 전환 (Ctrl+T)")
        self.auto_save()

    def populate_todo_view(self, content):
        """문자열에서 [ ] 와 [x] 및 [HH:mm] 파싱하여 체크박스 항목 위젯들 생성"""
        theme = PASTEL_THEMES[self.current_color]
        # 기존 아이템 제거
        for item in list(self.todo_items):
            self.todo_list_layout.removeWidget(item)
            item.deleteLater()
        self.todo_items.clear()

        lines = [l.strip() for l in content.split('\n') if l.strip()]
        for line in lines:
            m = re.match(r'^\[([ xX])\]\s*(?:\[(\d{1,2}:\d{2})\]\s*|(\d{1,2}:\d{2})\s+)?(.*)$', line)
            if m:
                checked = (m.group(1).lower() == 'x')
                time_str = m.group(2) or m.group(3)
                txt = m.group(4)
            else:
                m2 = re.match(r'^(?:\[(\d{1,2}:\d{2})\]\s*|(\d{1,2}:\d{2})\s+)(.*)$', line)
                if m2:
                    checked = False
                    time_str = m2.group(1) or m2.group(2)
                    txt = m2.group(3)
                else:
                    checked = False
                    time_str = None
                    txt = line
            self.add_todo_item_widget(checked, time_str, txt)

        if not self.todo_items:
            # 빈 경우 기본 한 줄 추가
            self.add_todo_item_widget(False, None, "")

        self.update_todo_footer()

    def add_todo_item_widget(self, checked=False, time_str=None, text=""):
        theme = PASTEL_THEMES[self.current_color]
        item = TodoItemWidget(checked, time_str, text, text_color=theme['text'])
        item.changed_signal.connect(self.on_todo_changed)
        item.delete_signal.connect(self.remove_todo_item_widget)
        item.create_next_signal.connect(self.create_next_todo_item)
        self.todo_items.append(item)
        self.todo_list_layout.addWidget(item)
        return item

    def on_add_input_enter(self):
        txt = self.add_todo_input.text().strip()
        if txt:
            m = re.match(r'^\[?(\d{1,2}:\d{2})\]?\s+(.*)$', txt)
            if m:
                time_str = m.group(1)
                item_txt = m.group(2)
            else:
                time_str = None
                item_txt = txt
            item = self.add_todo_item_widget(False, time_str, item_txt)
            self.add_todo_input.clear()
            self.update_todo_footer()
            self.auto_save()

    def create_next_todo_item(self, current_item):
        """Enter 키 입력 시 바로 아래에 새 할 일 추가 및 포커스 이동"""
        idx = self.todo_items.index(current_item) if current_item in self.todo_items else len(self.todo_items)
        new_item = self.add_todo_item_widget(False, None, "")
        # 순서 재정렬
        self.todo_items.remove(new_item)
        self.todo_items.insert(idx + 1, new_item)
        self.todo_list_layout.insertWidget(idx + 1, new_item)
        new_item.line_edit.setFocus()
        self.update_todo_footer()
        self.auto_save()

    def remove_todo_item_widget(self, item):
        if item in self.todo_items:
            idx = self.todo_items.index(item)
            self.todo_items.remove(item)
            self.todo_list_layout.removeWidget(item)
            item.deleteLater()
            self.update_todo_footer()
            self.auto_save()
            # 이전 아이템으로 포커스
            if self.todo_items:
                target_idx = max(0, idx - 1)
                self.todo_items[target_idx].line_edit.setFocus()

    def clear_completed_todos(self):
        """체크된 완료 항목들 일괄 삭제"""
        for item in list(self.todo_items):
            if item.is_checked():
                self.todo_items.remove(item)
                self.todo_list_layout.removeWidget(item)
                item.deleteLater()
        self.update_todo_footer()
        self.auto_save()

    def on_todo_changed(self):
        self.update_todo_footer()
        self.auto_save()

    def update_todo_footer(self):
        completed_count = sum(1 for item in self.todo_items if item.is_checked())
        if completed_count > 0:
            self.clear_completed_btn.setText(f"🧹 완료 항목 정리 ({completed_count}개)")
            self.clear_completed_btn.show()
        else:
            self.clear_completed_btn.hide()

    def get_current_content(self):
        """현재 모드에 맞춰 최신 텍스트 내용 반환"""
        if self.is_todo_mode:
            lines = []
            for item in self.todo_items:
                line_str = item.get_serialized_line()
                if item.get_text() or item.has_time:
                    lines.append(line_str)
            return "\n".join(lines)
        else:
            return self.text_edit.toPlainText()

    def setup_shortcuts(self):
        """창 내부 단축키 바인딩"""
        QShortcut(QKeySequence("Ctrl+N"), self, self.create_new_window)
        QShortcut(QKeySequence("Ctrl+P"), self, self.toggle_pin)
        QShortcut(QKeySequence("Ctrl+T"), self, self.toggle_mode)
        QShortcut(QKeySequence("Ctrl+S"), self, self.auto_save)
        QShortcut(QKeySequence("Ctrl+D"), self, self.confirm_delete_note)
        QShortcut(QKeySequence("Ctrl+W"), self, self.close_note)
        QShortcut(QKeySequence("Ctrl+H"), self, self.hide_to_tray)
        QShortcut(QKeySequence("Escape"), self, self.close_note)

    def apply_style(self):
        theme = PASTEL_THEMES[self.current_color]
        alarm_style = "background-color: #FEF3C7; border: 1.5px solid #F59E0B; border-radius: 6px;" if self.is_alarm_enabled else ""
        style = f"""
            QWidget#centralWidget {{
                background-color: {theme['bg']};
                border: 1.5px solid {theme['border']};
                border-radius: 14px;
            }}
            QDateEdit, QTimeEdit {{
                background-color: rgba(255, 255, 255, 0.75);
                border: 1px solid {theme['border']};
                border-radius: 6px;
                padding: 2px 6px;
                font-weight: 600;
                font-size: 12px;
                color: {theme['text']};
            }}
            QDateEdit:hover, QTimeEdit:hover {{
                background-color: rgba(255, 255, 255, 0.95);
                border-color: {theme['accent']};
            }}
            QDateEdit:focus, QTimeEdit:focus {{
                background-color: #FFFFFF;
                border: 1.5px solid {theme['accent']};
            }}
            QDateEdit::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 18px;
                border-left: none;
            }}
            QPushButton, QToolButton {{
                background-color: transparent;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                color: {theme['text']};
                padding: 2px;
            }}
            QPushButton:hover, QToolButton:hover {{
                background-color: rgba(0, 0, 0, 0.08);
            }}
            QPushButton:pressed, QToolButton:pressed {{
                background-color: rgba(0, 0, 0, 0.16);
            }}
            QPushButton#alarmBtn {{
                {alarm_style}
            }}
            QPushButton#closeBtn:hover {{
                background-color: #EF4444;
                color: #FFFFFF;
                font-weight: bold;
            }}
            QPushButton#delBtn:hover {{
                background-color: rgba(239, 68, 68, 0.15);
                color: #DC2626;
            }}
            QTextEdit {{
                background-color: transparent;
                border: none;
                color: {theme['text']};
                font-size: 13px;
                line-height: 1.5;
                padding: 6px;
            }}
            QScrollArea {{
                background-color: transparent;
                border: none;
            }}
            QLineEdit#addTodoInput {{
                background-color: rgba(255, 255, 255, 0.65);
                border: 1px dashed {theme['border']};
                border-radius: 8px;
                padding: 6px 10px;
                font-size: 12px;
                color: {theme['text']};
            }}
            QLineEdit#addTodoInput:hover {{
                background-color: rgba(255, 255, 255, 0.85);
            }}
            QLineEdit#addTodoInput:focus {{
                background-color: #FFFFFF;
                border: 1.5px solid {theme['accent']};
            }}
            QPushButton#clearCompletedBtn {{
                background: rgba(0, 0, 0, 0.04);
                border: 1px solid rgba(0, 0, 0, 0.08);
                border-radius: 6px;
                font-size: 11px;
                color: #64748B;
                padding: 4px 8px;
                font-weight: 500;
            }}
            QPushButton#clearCompletedBtn:hover {{
                background: rgba(239, 68, 68, 0.15);
                color: #EF4444;
                border-color: #EF4444;
            }}
        """
        self.alarm_btn.setObjectName("alarmBtn")
        self.clear_completed_btn.setObjectName("clearCompletedBtn")
        self.container.setObjectName("centralWidget")
        self.container.setStyleSheet(style)

        for item in self.todo_items:
            item.set_text_color(theme['text'])

    def flash_alert(self):
        """알람 발생 시 상단 벨 아이콘을 빨간색 경고등으로 반짝여 시각적 피드백 제공"""
        self.flash_step = 0
        if not hasattr(self, "_flash_timer"):
            self._flash_timer = QTimer(self)
            self._flash_timer.timeout.connect(self._on_flash_tick)
        self._flash_timer.start(350)

    def _on_flash_tick(self):
        self.flash_step += 1
        if self.flash_step % 2 == 1:
            self.alarm_btn.setText("🚨")
            self.alarm_btn.setStyleSheet("background: #ef4444; color: white; border-radius: 4px; font-weight: bold; font-size: 13px;")
        else:
            self.alarm_btn.setText("🔔")
            self.alarm_btn.setStyleSheet("background: #f59e0b; color: white; border-radius: 4px; font-weight: bold; font-size: 13px;")

        if self.flash_step >= 12:  # 약 4초간 반짝인 후 복구
            self._flash_timer.stop()
            self.alarm_btn.setText("🔔" if self.is_alarm_enabled else "🔕")
            self.apply_style()

    def mousePressEvent(self, event):
        if hasattr(QApplication.instance(), "tray_manager"):
            QApplication.instance().tray_manager.stop_tray_blink()
        if hasattr(self, "_flash_timer") and self._flash_timer.isActive():
            self._flash_timer.stop()
            self.alarm_btn.setText("🔔" if self.is_alarm_enabled else "🔕")
            self.apply_style()
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

    def hide_to_tray(self):
        self.hide()
        if hasattr(QApplication.instance(), "tray_manager"):
            QApplication.instance().tray_manager.notify("메모 숨김", "메모가 트레이로 최소화되었습니다. (Alt+M 또는 트레이 클릭 시 복원)")

    def save_initial(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        current_date = self.date_picker.date().toString("yyyy-MM-dd")
        current_time = self.time_picker.time().toString("HH:mm")
        current_text = self.get_current_content()
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
        current_text = self.get_current_content()
        geo = self.geometry()

        cursor.execute(
            """
            UPDATE sticky_notes
            SET target_date = ?, target_time = ?, content = ?, color = ?, is_pinned = ?, is_alarm_enabled = ?, pos_x = ?, pos_y = ?, width = ?, height = ?, is_visible = ?
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
                1 if self.isVisible() else 0,
                self.note_id,
            ),
        )
        conn.commit()
        conn.close()
        if hasattr(QApplication.instance(), "tray_manager"):
            QApplication.instance().tray_manager.refresh_calendar()

    def close_note(self):
        """창만 닫기: DB와 캘린더에는 100% 안전하게 영구 저장되어 유지됨"""
        self.auto_save()
        if self.note_id is not None:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("UPDATE sticky_notes SET is_visible = 0 WHERE id = ?", (self.note_id,))
            conn.commit()
            conn.close()
        self.hide()
        if hasattr(QApplication.instance(), "tray_manager"):
            QApplication.instance().tray_manager.refresh_calendar()
            QApplication.instance().tray_manager.notify("메모 창 닫힘", "메모가 닫혔습니다. 캘린더(📅) 또는 트레이 메뉴에서 언제든 다시 열 수 있습니다.")

    def confirm_delete_note(self):
        """확인 대화상자 후 DB와 캘린더에서 완전히 영구 삭제"""
        reply = QMessageBox.question(
            self,
            "메모 완전 삭제",
            "이 메모를 완전히 삭제하시겠습니까?\n\n삭제 시 캘린더에서도 완전히 지워집니다.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.delete_note_permanently()

    def delete_note_permanently(self):
        """DB와 캘린더에서 영구 삭제"""
        if self.note_id is not None:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sticky_notes WHERE id = ?", (self.note_id,))
            conn.commit()
            conn.close()
        if self in active_windows:
            active_windows.remove(self)
        self.close()
        if hasattr(QApplication.instance(), "tray_manager"):
            QApplication.instance().tray_manager.refresh_calendar()
            QApplication.instance().tray_manager.notify("메모 완전 삭제", "메모가 데이터베이스와 캘린더에서 완전히 삭제되었습니다.")

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
            w=max(480, geo.width()),
            h=max(330, geo.height()),
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
        self.normal_icon = QIcon(create_tray_icon_pixmap(is_alert=False))
        self.alert_icon = QIcon(create_tray_icon_pixmap(is_alert=True))
        self.tray_icon.setIcon(self.normal_icon)
        self.tray_icon.setToolTip("스티커 메모 캘린더 (단축키: Alt+N 새 메모, Alt+M 전체 숨김/표시)")

        # 트레이 아이콘 반짝임 타이머
        self.is_blinking = False
        self.blink_count = 0
        self.blink_timer = QTimer()
        self.blink_timer.timeout.connect(self._on_tray_blink_tick)

        # 트레이 컨텍스트 메뉴 생성
        self.menu = QMenu()
        
        action_new = QAction("➕ 새 메모 만들기 (Alt+N)", self.menu)
        action_new.triggered.connect(lambda: self.create_new_note())
        self.menu.addAction(action_new)

        action_cal = QAction("📅 캘린더 뷰 열기", self.menu)
        action_cal.triggered.connect(self.open_calendar_dialog)
        self.menu.addAction(action_cal)

        self.action_toggle = QAction("👁️ 모든 메모 보이기/숨기기 (Alt+M)", self.menu)
        self.action_toggle.triggered.connect(self.toggle_all_notes)
        self.menu.addAction(self.action_toggle)

        action_align = QAction("🗂️ 화면에 바둑판식 정렬", self.menu)
        action_align.triggered.connect(self.align_notes)
        self.menu.addAction(action_align)

        self.menu.addSeparator()

        self.action_autostart = QAction("🚀 윈도우 시작 시 자동 실행", self.menu)
        self.action_autostart.setCheckable(True)
        self.action_autostart.setChecked(is_autostart_enabled())
        self.action_autostart.triggered.connect(self.toggle_autostart)
        self.menu.addAction(self.action_autostart)

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

    def open_calendar_dialog(self, target_date=None):
        if not hasattr(self, "calendar_window") or self.calendar_window is None:
            self.calendar_window = CalendarWindow()
        if target_date:
            self.calendar_window.select_date(target_date)
        self.calendar_window.show()
        self.calendar_window.raise_()
        self.calendar_window.activateWindow()

    def refresh_calendar(self):
        if hasattr(self, "calendar_window") and self.calendar_window and self.calendar_window.isVisible():
            self.calendar_window.highlight_calendar_dates()
            self.calendar_window.on_date_selected()

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
            w=480,
            h=330,
        )
        active_windows.append(w)
        w.show()
        w.raise_()
        w.activateWindow()
        self.notify("새 메모 생성 (Alt+N)", "마우스 커서 위치에 새 포스트잇이 생성되었습니다.")

    def start_tray_blink(self):
        """알람 발생 시 작업 표시줄 트레이 아이콘을 반짝임"""
        self.is_blinking = True
        self.blink_count = 0
        self.blink_timer.start(400)

    def stop_tray_blink(self):
        """트레이 아이콘 반짝임 정지 및 정상 복구"""
        if self.is_blinking:
            self.is_blinking = False
            self.blink_timer.stop()
            self.tray_icon.setIcon(self.normal_icon)

    def _on_tray_blink_tick(self):
        self.blink_count += 1
        if self.blink_count % 2 == 1:
            self.tray_icon.setIcon(self.alert_icon)
        else:
            self.tray_icon.setIcon(self.normal_icon)

        if self.blink_count >= 30:  # 약 12초 후 자동 종료
            self.stop_tray_blink()

    def check_alarms(self):
        """설정된 날짜 및 시간에 알람 사운드 및 팝업 토스트 트리거 (10분 전 사전 알림 + 정시 알림)"""
        now = datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        current_time = now.strftime("%H:%M")

        for w in list(active_windows):
            if not w.is_alarm_enabled:
                continue

            note_date = w.date_picker.date().toString("yyyy-MM-dd")

            # 1. 헤더 기본 알람 시간 체크
            header_time = w.time_picker.time().toString("HH:mm")
            # 10분 전 사전 알림
            adv_date_h, adv_time_h = get_advance_time(note_date, header_time, 10)
            alarm_key_h_adv = (w.note_id, adv_date_h, header_time, "header", "adv10")
            if current_date == adv_date_h and current_time == adv_time_h:
                if alarm_key_h_adv not in self.triggered_alarms:
                    self.triggered_alarms.add(alarm_key_h_adv)
                    content_preview = w.get_current_content().strip()
                    first_line = content_preview.split('\n')[0][:40] if content_preview else "일정 메모"
                    self.trigger_alarm(
                        w,
                        f"{header_time} (10분 전)",
                        f"⏳ [10분 전 사전 알림] {header_time} '{first_line}' 10분 전입니다!",
                        is_advance=True
                    )

            # 정시 알림
            alarm_key_h_ontime = (w.note_id, note_date, header_time, "header", "ontime")
            if current_date == note_date and current_time == header_time:
                if alarm_key_h_ontime not in self.triggered_alarms:
                    self.triggered_alarms.add(alarm_key_h_ontime)
                    content_preview = w.get_current_content().strip()
                    first_line = content_preview.split('\n')[0][:40] if content_preview else "일정 메모"
                    self.trigger_alarm(
                        w,
                        header_time,
                        f"🔔 [지금 시작!] {header_time} '{first_line}' 시간입니다!",
                        is_advance=False
                    )

            # 2. 개별 할 일 항목 시간 체크 (체크리스트 및 텍스트 모드 공통)
            content = w.get_current_content()
            lines = [l.strip() for l in content.split('\n') if l.strip()]
            for line in lines:
                m = re.match(r'^\[([ xX])\]\s*(?:\[(\d{1,2}:\d{2})\]\s*|(\d{1,2}:\d{2})\s+)?(.*)$', line)
                if m:
                    is_checked = (m.group(1).lower() == 'x')
                    item_time = m.group(2) or m.group(3)
                    item_txt = m.group(4)
                    if is_checked or not item_time:
                        continue
                else:
                    m2 = re.match(r'^(?:\[(\d{1,2}:\d{2})\]\s*|(\d{1,2}:\d{2})\s+)(.*)$', line)
                    if m2:
                        item_time = m2.group(1) or m2.group(2)
                        item_txt = m2.group(3)
                    else:
                        continue

                # 10분 전 사전 알림
                adv_d, adv_t = get_advance_time(note_date, item_time, 10)
                item_key_adv = (w.note_id, adv_d, item_time, item_txt, "adv10")
                if current_date == adv_d and current_time == adv_t:
                    if item_key_adv not in self.triggered_alarms:
                        self.triggered_alarms.add(item_key_adv)
                        self.trigger_alarm(
                            w,
                            f"{item_time} (10분 전)",
                            f"⏳ [10분 전 사전 알림] {item_time} '{item_txt}' 10분 전입니다!",
                            is_advance=True
                        )

                # 정시 알림
                item_key_ontime = (w.note_id, note_date, item_time, item_txt, "ontime")
                if current_date == note_date and current_time == item_time:
                    if item_key_ontime not in self.triggered_alarms:
                        self.triggered_alarms.add(item_key_ontime)
                        self.trigger_alarm(
                            w,
                            item_time,
                            f"🔔 [지금 시작!] {item_time} '{item_txt}' 시간입니다!",
                            is_advance=False
                        )

    def trigger_alarm(self, window, time_str, message="일정 메모 알람입니다.", is_advance=False):
        """알람 사운드 재생, 창 전면 표시, 트레이/메모 아이콘 반짝임, 시스템 토스트 알림"""
        # 1. 알람 사운드 재생
        if winsound:
            try:
                if is_advance:
                    # 10분 전 사전 알림: 맑고 부드러운 사전 차임벨 (도 - 솔)
                    winsound.Beep(523, 200)   # C5
                    winsound.Beep(784, 350)   # G5
                else:
                    # 정시 알림: 주목도 높은 알람 비프 (시 - 높은미)
                    winsound.Beep(988, 200)   # B5
                    winsound.Beep(1319, 450)  # E6
            except Exception:
                QApplication.beep()
        else:
            QApplication.beep()

        # 2. 창 활성화 및 전면 표시
        window.show()
        window.raise_()
        window.activateWindow()

        # 3. 창 내부 벨 아이콘 반짝임 & 윈도우 작업 표시줄 알림
        window.flash_alert()
        QApplication.alert(window, 5000)

        # 4. 시스템 트레이 아이콘 반짝임 시작
        self.start_tray_blink()

        # 5. 토스트 알림 발송
        self.notify(f"⏰ [일정 알람] {time_str}", message)

    def on_tray_activated(self, reason):
        self.stop_tray_blink()
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

    def create_new_note(self, target_date=None):
        """새 메모 생성"""
        color_choices = list(PASTEL_THEMES.keys())
        random_color = random.choice(color_choices)
        w = StickyNoteWindow(
            note_id=None,
            target_date=target_date or date.today().isoformat(),
            target_time=datetime.now().strftime("%H:%M"),
            content="",
            color=random_color,
            is_pinned=0,
            is_alarm_enabled=0,
            x=200 + random.randint(0, 100),
            y=150 + random.randint(0, 100),
            w=480,
            h=330,
        )
        active_windows.append(w)
        w.show()
        w.raise_()
        w.activateWindow()
        return w

    def align_notes(self):
        """화면에 활성 메모들을 바둑판 형태로 자동 정렬"""
        visible_windows = [w for w in active_windows if w.isVisible()]
        if not visible_windows:
            for w in active_windows:
                w.show()
            visible_windows = active_windows

        start_x, start_y = 50, 50
        gap = 20
        col_w, row_h = 490, 340
        max_cols = 4

        for idx, w in enumerate(visible_windows):
            col = idx % max_cols
            row = idx // max_cols
            new_x = start_x + col * (col_w + gap)
            new_y = start_y + row * (row_h + gap)
            w.move(new_x, new_y)
            w.auto_save()

    def toggle_autostart(self, checked):
        """윈도우 시작 시 자동 실행 등록/해제 토글 핸들러"""
        success = set_autostart(checked)
        if success:
            if checked:
                self.notify("자동 실행 활성화", "🚀 이제 컴퓨터 부팅 시 스티커 메모가 자동으로 켜집니다!")
            else:
                self.notify("자동 실행 해제", "윈도우 시작 시 자동 실행이 해제되었습니다.")
        else:
            self.action_autostart.setChecked(not checked)
            self.notify("설정 실패", "윈도우 시작 프로그램 설정 중 오류가 발생했습니다.")

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

    # 윈도우 시작 시 자동 실행 기본 등록 및 경로 동기화
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT)")
        cur.execute("SELECT value FROM app_settings WHERE key = 'autostart_initialized'")
        row = cur.fetchone()
        if not row:
            set_autostart(True)
            cur.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES ('autostart_initialized', '1')")
            conn.commit()
        else:
            if is_autostart_enabled():
                set_autostart(True)
        conn.close()
    except Exception as e:
        print("Autostart init notice:", e)

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
        SELECT id, target_date, target_time, content, color, is_pinned, is_alarm_enabled, pos_x, pos_y, width, height, COALESCE(is_visible, 1)
        FROM sticky_notes
        """
    )
    rows = cursor.fetchall()
    conn.close()

    opened_any = False
    if rows:
        for row in rows:
            is_visible = row[11]
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
                w=max(460, row[9]),
                h=max(300, row[10]),
            )
            active_windows.append(w)
            if is_visible:
                w.show()
                opened_any = True
            else:
                w.hide()

        # 만약 저장된 메모들은 있는데 전부 닫혀 있는 상태라면, 가장 최근 메모를 열어두어 편리하게 사용하도록 지원
        if not opened_any and active_windows:
            active_windows[-1].show()
            active_windows[-1].raise_()
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
            w=480,
            h=330,
        )
        active_windows.append(initial_note)
        initial_note.show()

    # 트레이 실행 안내 알림
    tray_manager.notify("스티커 메모 캘린더 시작", "글로벌 단축키 활성화됨:\n- Alt+N: 마우스 위치에 새 메모\n- Alt+M: 전체 숨김/표시")

    sys.exit(app.exec())

if __name__ == "__main__":
    main()

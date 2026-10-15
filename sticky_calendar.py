import sys
import sqlite3
import random
from datetime import date
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QTextEdit,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QDateEdit,
    QPushButton,
    QToolButton,
    QMenu,
    QGraphicsDropShadowEffect,
)
from PyQt6.QtCore import QDate, Qt, QPoint
from PyQt6.QtGui import QColor, QFont, QAction

DB_PATH = "sticky_notes.db"

# 파스텔 톤 테마 정의 (배경색, 헤더색, 테두리색, 텍스트색)
PASTEL_THEMES = {
    "yellow": {"bg": "#FEF9E7", "header": "#FDEBD0", "border": "#FAD7A0", "text": "#333333"},
    "blue": {"bg": "#EBF5FB", "header": "#D4E6F1", "border": "#A9CCE3", "text": "#333333"},
    "green": {"bg": "#EAFAF1", "header": "#D5F5E3", "border": "#A9DFBF", "text": "#333333"},
    "orange": {"bg": "#FBEEE6", "header": "#F6DDCC", "border": "#EDBB99", "text": "#333333"},
    "purple": {"bg": "#F4ECF7", "header": "#E8DAEF", "border": "#D2B4DE", "text": "#333333"},
}

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS sticky_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_date TEXT,
            content TEXT,
            color TEXT,
            is_pinned INTEGER,
            pos_x INTEGER,
            pos_y INTEGER,
            width INTEGER,
            height INTEGER
        )
        """
    )
    conn.commit()
    conn.close()

class StickyNoteWindow(QMainWindow):
    def __init__(self, note_id=None, target_date=None, content="", color="yellow", is_pinned=0, x=150, y=150, w=320, h=300):
        super().__init__()
        self.note_id = note_id
        self.current_color = color if color in PASTEL_THEMES else "yellow"
        self.is_pinned = bool(is_pinned)
        self.old_pos = None

        # 프레임리스 창 및 윈도우 기본 속성
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.SubWindow)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setGeometry(x, y, w, h)

        if self.is_pinned:
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)

        # 메인 컨테이너 위젯 및 레이아웃
        self.container = QWidget(self)
        self.setCentralWidget(self.container)
        main_layout = QVBoxLayout(self.container)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(6)

        # 상단 타이틀 바 레이아웃
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(4, 2, 4, 2)
        header_layout.setSpacing(4)

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

        # 항상 위 핀 버튼
        self.pin_btn = QPushButton("📌" if self.is_pinned else "📍")
        self.pin_btn.setFixedSize(28, 26)
        self.pin_btn.setToolTip("항상 위에 고정")
        self.pin_btn.clicked.connect(self.toggle_pin)
        header_layout.addWidget(self.pin_btn)

        # 색상 변경 메뉴 버튼
        self.color_btn = QToolButton()
        self.color_btn.setText("🎨")
        self.color_btn.setFixedSize(28, 26)
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
        todo_btn.setFixedSize(28, 26)
        todo_btn.setToolTip("체크박스 투두 추가")
        todo_btn.clicked.connect(self.add_todo_item)
        header_layout.addWidget(todo_btn)

        # 새 메모 추가 버튼
        new_btn = QPushButton("➕")
        new_btn.setFixedSize(28, 26)
        new_btn.setToolTip("새 일정 메모")
        new_btn.clicked.connect(self.create_new_window)
        header_layout.addWidget(new_btn)

        # 삭제 버튼
        del_btn = QPushButton("✕")
        del_btn.setFixedSize(28, 26)
        del_btn.setToolTip("삭제")
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

        self.apply_style()

        if self.note_id is None:
            self.save_initial()

    def apply_style(self):
        theme = PASTEL_THEMES[self.current_color]
        style = f"""
            QWidget#centralWidget {{
                background-color: {theme['bg']};
                border: 1px solid {theme['border']};
                border-radius: 8px;
            }}
            QDateEdit {{
                background-color: {theme['header']};
                border: 1px solid {theme['border']};
                border-radius: 4px;
                padding: 2px 6px;
                font-weight: bold;
                color: {theme['text']};
            }}
            QPushButton, QToolButton {{
                background-color: {theme['header']};
                border: 1px solid {theme['border']};
                border-radius: 4px;
                font-size: 11px;
                color: {theme['text']};
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

    def save_initial(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        current_date = self.date_picker.date().toString("yyyy-MM-dd")
        current_text = self.text_edit.toPlainText()
        geo = self.geometry()

        cursor.execute(
            """
            INSERT INTO sticky_notes (target_date, content, color, is_pinned, pos_x, pos_y, width, height)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                current_date,
                current_text,
                self.current_color,
                1 if self.is_pinned else 0,
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
        current_text = self.text_edit.toPlainText()
        geo = self.geometry()

        cursor.execute(
            """
            UPDATE sticky_notes
            SET target_date = ?, content = ?, color = ?, is_pinned = ?, pos_x = ?, pos_y = ?, width = ?, height = ?
            WHERE id = ?
            """,
            (
                current_date,
                current_text,
                self.current_color,
                1 if self.is_pinned else 0,
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
            content="",
            color=random_color,
            is_pinned=0,
            x=geo.x() + 35,
            y=geo.y() + 35,
            w=geo.width(),
            h=geo.height(),
        )
        active_windows.append(new_window)
        new_window.show()

active_windows = []

def main():
    init_db()
    app = QApplication(sys.argv)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, target_date, content, color, is_pinned, pos_x, pos_y, width, height
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
                content=row[2],
                color=row[3],
                is_pinned=row[4],
                x=row[5],
                y=row[6],
                w=row[7],
                h=row[8],
            )
            active_windows.append(w)
            w.show()
    else:
        # 최초 실행 시 기본 메모 하나 생성
        initial_note = StickyNoteWindow(
            note_id=None,
            target_date=date.today().isoformat(),
            content="[ ] 오늘 할 일 1\n[ ] 오늘 할 일 2",
            color="yellow",
            is_pinned=0,
            x=200,
            y=200,
            w=320,
            h=300,
        )
        active_windows.append(initial_note)
        initial_note.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()

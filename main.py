from PySide6.QtWidgets import (
    QApplication, QWidget, QTextEdit, QPushButton, QVBoxLayout, QLabel,
    QHBoxLayout, QListWidget, QListWidgetItem, QComboBox, QInputDialog, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal
import sys, json, os
from chatgpt_api import load_api_key
from tts import speak_text
from record import save_to_history, transcribe_audio, load_history

class ChatWorker(QThread):
    result_signal = Signal(str)
    error_signal = Signal(str)

    def __init__(self, question, role_prompt, api_key):
        super().__init__()
        self.question = question
        self.role_prompt = role_prompt
        self.api_key = api_key

    def run(self):
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            messages = []
            if self.role_prompt:
                messages.append({"role": "system", "content": self.role_prompt})
            messages.append({"role": "user", "content": self.question})
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.7
            )
            save_to_history(self.question, response.choices[0].message.content)
            self.result_signal.emit(response.choices[0].message.content)
        except Exception as e:
            self.error_signal.emit(str(e))

class ChatGPTApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ChatGPT 家庭助手 v7")
        self.resize(920, 580)
        self.load_roles()
        self.api_key = self.ensure_api_key()
        self.init_ui()
        self.load_history_list()

    def ensure_api_key(self):
        key = load_api_key()
        if not key or not key.startswith("sk-"):
            while True:
                key, ok = QInputDialog.getText(self, "OpenAI Key 设置", "请输入你的 OpenAI API Key：")
                if ok and key.startswith("sk-"):
                    with open("config.json", "w", encoding="utf-8") as f:
                        json.dump({"api_key": key}, f, indent=2)
                    return key
                elif not ok:
                    QMessageBox.warning(self, "错误", "你未输入有效 Key，程序将退出。")
                    sys.exit(1)
        return key

    def load_roles(self):
        with open("roles.json", "r", encoding="utf-8") as f:
            self.roles = json.load(f)

    def init_ui(self):
        self.role_selector = QComboBox()
        self.role_selector.addItems(self.roles.keys())

        self.theme_button = QPushButton("切换主题")
        self.theme_button.clicked.connect(self.toggle_theme)
        self.current_theme = "light"
        self.load_theme()

        theme_bar = QHBoxLayout()
        theme_bar.addWidget(QLabel("角色选择："))
        theme_bar.addWidget(self.role_selector)
        theme_bar.addStretch()
        theme_bar.addWidget(self.theme_button)

        self.input_box = QTextEdit()
        self.input_box.setPlaceholderText("请输入你的问题...")

        self.answer_box = QTextEdit()
        self.answer_box.setReadOnly(True)

        self.status_label = QLabel("状态：等待中")

        self.send_button = QPushButton("发送")
        self.send_button.clicked.connect(self.handle_send)

        self.clear_button = QPushButton("清空")
        self.clear_button.clicked.connect(self.handle_clear)

        self.voice_button = QPushButton("🔊 朗读")
        self.voice_button.clicked.connect(self.handle_speak)

        self.record_button = QPushButton("🎙️ 语音输入")
        self.record_button.clicked.connect(self.handle_voice_input)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.send_button)
        button_layout.addWidget(self.clear_button)
        button_layout.addWidget(self.voice_button)
        button_layout.addWidget(self.record_button)

        left_layout = QVBoxLayout()
        left_layout.addLayout(theme_bar)
        left_layout.addWidget(self.input_box)
        left_layout.addWidget(self.answer_box)
        left_layout.addLayout(button_layout)
        left_layout.addWidget(self.status_label)

        self.history_list = QListWidget()
        self.history_list.itemClicked.connect(self.load_selected_history)

        main_layout = QHBoxLayout()
        main_layout.addLayout(left_layout, 3)
        main_layout.addWidget(self.history_list, 1)

        self.setLayout(main_layout)

    def load_theme(self):
        qss_file = f"themes/{self.current_theme}.qss"
        if os.path.exists(qss_file):
            with open(qss_file, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())

    def toggle_theme(self):
        self.current_theme = "dark" if self.current_theme == "light" else "light"
        self.load_theme()

    def handle_send(self):
        question = self.input_box.toPlainText().strip()
        if not question:
            self.status_label.setText("状态：请输入问题")
            return
        self.status_label.setText("状态：发送中...")
        self.send_button.setEnabled(False)
        role_name = self.role_selector.currentText()
        role_prompt = self.roles[role_name]
        self.worker = ChatWorker(question, role_prompt, self.api_key)
        self.worker.result_signal.connect(self.display_answer)
        self.worker.error_signal.connect(self.display_error)
        self.worker.start()

    def handle_clear(self):
        self.input_box.clear()
        self.answer_box.clear()
        self.status_label.setText("状态：等待中")

    def handle_speak(self):
        text = self.answer_box.toPlainText()
        if text:
            speak_text(text)

    def handle_voice_input(self):
        self.status_label.setText("状态：录音中，请说话...")
        text = transcribe_audio()
        self.input_box.setPlainText(text)
        self.status_label.setText("状态：语音识别完成")

    def display_answer(self, answer):
        self.answer_box.setPlainText(answer)
        self.status_label.setText("状态：完成")
        self.send_button.setEnabled(True)
        self.load_history_list()

    def display_error(self, error):
        self.answer_box.setPlainText("出错了：" + error)
        self.status_label.setText("状态：出错")
        self.send_button.setEnabled(True)

    def load_history_list(self):
        self.history_list.clear()
        self.histories = load_history()
        for item in self.histories:
            display_text = f"[{item['time']}] {item['question'][:20]}..."
            self.history_list.addItem(QListWidgetItem(display_text))

    def load_selected_history(self, item):
        index = self.history_list.currentRow()
        selected = self.histories[index]
        self.input_box.setPlainText(selected['question'])
        self.answer_box.setPlainText(selected['answer'])

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ChatGPTApp()
    window.show()
    sys.exit(app.exec())
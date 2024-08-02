import os
import sys
import threading
import time
import keyboard
import psutil
import win32gui
import win32process
from PIL import ImageGrab
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog, QHBoxLayout, \
    QMessageBox, QLineEdit
import cv2
import numpy as np
import pyaudio
import wave
import ffmpeg


class ScreenshotApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('截图和录屏工具')
        self.setGeometry(100, 100, 500, 400)

        # 设置布局
        main_layout = QVBoxLayout()

        # 说明标签
        description_label = QLabel('先选择目录，在打开截图窗口，按 F2 获取目标窗口的句柄')
        main_layout.addWidget(description_label)

        # 窗口句柄显示
        self.handle_label = QLabel('窗口句柄: 无')
        main_layout.addWidget(self.handle_label)

        # 进程名称显示
        self.process_name_label = QLabel('进程名称: 无')
        main_layout.addWidget(self.process_name_label)

        # 选择目录
        self.dir_label = QLabel('选择的目录: 无')
        main_layout.addWidget(self.dir_label)

        # 截图状态显示
        self.status_label = QLabel('状态: 未开始截图')
        main_layout.addWidget(self.status_label)

        # 截图间隔输入
        interval_layout = QHBoxLayout()
        interval_label = QLabel('截图间隔(秒): ')
        interval_layout.addWidget(interval_label)
        self.interval_input = QLineEdit()
        interval_layout.addWidget(self.interval_input)
        main_layout.addLayout(interval_layout)

        # 按钮布局
        button_layout = QHBoxLayout()

        self.select_dir_button = QPushButton('选择目录')
        self.select_dir_button.clicked.connect(self.select_directory)
        button_layout.addWidget(self.select_dir_button)

        self.start_button = QPushButton('开始截图')
        self.start_button.clicked.connect(self.toggle_screenshot)
        button_layout.addWidget(self.start_button)

        self.start_recording_button = QPushButton('开始录屏')
        self.start_recording_button.clicked.connect(self.toggle_recording)
        button_layout.addWidget(self.start_recording_button)

        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)
        self.screenshot_dir = ""
        self.hwnd = None
        self.screenshot_thread = None
        self.is_screenshot_running = False
        self.is_recording_running = False
        self.screenshot_count = 0
        self.recording_count = 0
        self.recording_images = []

        # 注册热键获取窗口句柄
        keyboard.add_hotkey('F2', self.get_window_handle)

    def get_window_handle(self):
        if not self.screenshot_dir:
            QMessageBox.warning(self, '错误', '请先选择目录，否则默认获取')
            return

        try:
            self.hwnd = win32gui.GetForegroundWindow()
            if self.hwnd:
                self.handle_label.setText(f'窗口句柄: {self.hwnd}')
                try:
                    _, pid = win32process.GetWindowThreadProcessId(self.hwnd)
                    process = psutil.Process(pid)
                    self.process_name_label.setText(f'进程名称: {process.name()}')
                except psutil.NoSuchProcess:
                    self.process_name_label.setText('进程名称: 未知 (进程不存在)')
                except Exception as e:
                    self.process_name_label.setText(f'进程名称: 未知 (错误: {e})')
        except Exception as e:
            QMessageBox.critical(self, '错误', f'获取窗口句柄时出错: {e}')
            self.hwnd = None

    def select_directory(self):
        self.screenshot_dir = QFileDialog.getExistingDirectory(self, '选择目录')
        if self.screenshot_dir:
            self.dir_label.setText(f'选择的目录: {self.screenshot_dir}')

    def toggle_screenshot(self):
        if not self.screenshot_dir:
            QMessageBox.warning(self, '错误', '请先选择截图存放目录')
            return
        if not self.hwnd:
            QMessageBox.warning(self, '错误', '请先按 F2 获取目标窗口的句柄')
            return
        if self.is_screenshot_running:
            self.stop_screenshot()
        else:
            self.start_screenshot()

    def start_screenshot(self):
        if self.hwnd and self.screenshot_dir:
            try:
                interval = int(self.interval_input.text())
                if interval <= 0:
                    QMessageBox.warning(self, '错误', '请输入大于0的整数作为间隔')
                    return
            except ValueError:
                QMessageBox.warning(self, '错误', '请输入有效的整数作为间隔')
                return

            self.is_screenshot_running = True
            self.screenshot_count = 0
            self.start_button.setText('暂停截图')
            self.status_label.setText('状态: 截图进行中')
            self.screenshot_thread = threading.Thread(target=self.take_screenshots, args=(interval,))
            self.screenshot_thread.start()

    def stop_screenshot(self):
        self.is_screenshot_running = False
        self.start_button.setText('开始截图')
        self.status_label.setText('状态: 已暂停截图')

    def take_screenshots(self, interval):
        while self.is_screenshot_running:
            try:
                left, top, right, bottom = win32gui.GetWindowRect(self.hwnd)
                bbox = (left, top, right, bottom)
                img = ImageGrab.grab(bbox)
                timestamp = time.strftime("%Y%m%d-%H%M%S")
                img.save(os.path.join(self.screenshot_dir, f'screenshot_{timestamp}.png'))
                self.screenshot_count += 1
                self.status_label.setText(f'状态: 截图进行中 - 第 {self.screenshot_count} 张')
                time.sleep(interval)
            except Exception as e:
                print(f"Error: {e}")
                break

    def toggle_recording(self):
        if not self.screenshot_dir:
            QMessageBox.warning(self, '错误', '请先选择视频存放目录')
            return
        if not self.hwnd:
            QMessageBox.warning(self, '错误', '请先按 F2 获取目标窗口的句柄')
            return
        if self.is_recording_running:
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self):
        if self.hwnd and self.screenshot_dir:
            self.is_recording_running = True
            self.recording_images = []
            self.recording_count = 0
            self.start_recording_button.setText('结束录屏')
            self.status_label.setText('状态: 录屏进行中')
            self.recording_thread = threading.Thread(target=self.record_screen)
            self.recording_thread.start()
            self.audio_thread = threading.Thread(target=self.record_audio, args=("output_audio.wav", 30))
            self.audio_thread.start()

    def stop_recording(self):
        self.is_recording_running = False
        self.start_recording_button.setText('开始录屏')
        self.status_label.setText('状态: 已暂停录屏')
        self.save_recording()

    def record_screen(self):
        while self.is_recording_running:
            try:
                left, top, right, bottom = win32gui.GetWindowRect(self.hwnd)
                bbox = (left, top, right, bottom)
                img = ImageGrab.grab(bbox)
                img_np = np.array(img)
                img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
                self.recording_images.append(img_bgr)
                self.recording_count += 1
                self.status_label.setText(f'状态: 录屏进行中 - 第 {self.recording_count} 帧')
                time.sleep(1 / 30)  # 每秒录制30帧
            except Exception as e:
                print(f"Error: {e}")
                break

    def save_recording(self):
        if self.recording_images:
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            video_path = os.path.join(self.screenshot_dir, f'recording_{timestamp}.mp4')
            height, width, layers = self.recording_images[0].shape
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            video = cv2.VideoWriter(video_path, fourcc, 30, (width, height))

            for img in self.recording_images:
                video.write(img)
            video.release()

            # 等待音频录制完成
            self.audio_thread.join()

            # 合并视频和音频
            audio_path = os.path.join(self.screenshot_dir, "output_audio.wav")
            output_final_path = os.path.join(self.screenshot_dir, f'final_{timestamp}.mp4')
            self.merge_audio_video(video_path, audio_path, output_final_path)

            QMessageBox.information(self, '录屏完成', f'录屏已保存到: {output_final_path}')
            self.recording_images = []

    def record_audio(self, output_filename, duration, sample_rate=44100, channels=2):
        p = pyaudio.PyAudio()

        stream = p.open(format=pyaudio.paInt16,
                        channels=channels,
                        rate=sample_rate,
                        input=True,
                        frames_per_buffer=1024)

        frames = []

        print("Recording audio...")

        for _ in range(0, int(sample_rate / 1024 * duration)):
            if not self.is_recording_running:
                break
            data = stream.read(1024)
            frames.append(data)

        print("Finished recording audio.")

        stream.stop_stream()
        stream.close()
        p.terminate()

        wf = wave.open(output_filename, 'wb')
        wf.setnchannels(channels)
        wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
        wf.setframerate(sample_rate)
        wf.writeframes(b''.join(frames))
        wf.close()

    def merge_audio_video(self, video_filename, audio_filename, output_filename):
        input_video = ffmpeg.input(video_filename)
        input_audio = ffmpeg.input(audio_filename)
        ffmpeg.concat(input_video, input_audio, v=1, a=1).output(output_filename).run()


if __name__ == '__main__':
    if getattr(sys, 'frozen', False):
        application_path = sys._MEIPASS
    else:
        application_path = os.path.dirname(os.path.abspath(__file__))

    icon_path = os.path.join(application_path, './image/icron2.png')
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(icon_path))
    ex = ScreenshotApp()
    ex.show()
    sys.exit(app.exec())
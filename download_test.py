import sys
import psycopg2
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QSizePolicy, QMessageBox
from PyQt5.QtWidgets import QInputDialog
from PyQt5.QtWidgets import QHBoxLayout
import requests
import xml.etree.ElementTree as ET
from psycopg2.extras import execute_values

class ApiDataRetriever:
    def __init__(self, api_input, service_key_input, param_labels, param_inputs, preview_table):
        self.api_input = api_input
        self.service_key_input = service_key_input
        self.param_labels = param_labels
        self.param_inputs = param_inputs
        self.preview_table = preview_table

    def call_api(self):
        api_url = self.api_input.text()
        service_key = self.service_key_input.text()

        if not service_key:
            QMessageBox.critical(None, '에러', '서비스 키를 입력하세요.')
            return None
        
        params = {'serviceKey': service_key}

        for i, param_input in enumerate(self.param_inputs):
            param_name = self.param_labels[i].text().replace(':', '').strip()
            if param_name:
                params[param_name] = param_input.text()

        try:
            response = requests.get(api_url, params=params)
            response.raise_for_status()
            return response.text

        except requests.exceptions.RequestException as e:
            QMessageBox.critical(None, '에러', f"다운로드 중 오류 발생: {e}")
            return None

    def data_preview(self): # datatype이 xml일 때만 실행됨...... 이것도 해결
        api_data = self.call_api()
        root = ET.fromstring(api_data)

        # 열 이름 및 값 추출
        columns = ["baseDate", "baseTime", "category", "fcstDate", "fcstTime", "fcstValue", "nx", "ny"]
        data = []

        for item in root.find(".//items"):
            row = [item.find(col).text for col in columns]
            data.append(row)

        # Set up the table
        self.preview_table.setColumnCount(len(columns))
        self.preview_table.setHorizontalHeaderLabels(columns)
        self.preview_table.setRowCount(len(data))

        for row_idx, row_data in enumerate(data):
            for col_idx, col_data in enumerate(row_data):
                item = QTableWidgetItem(col_data)
                self.preview_table.setItem(row_idx, col_idx, item)
        
class DataDownloader(QWidget):
    def __init__(self):
        super().__init__()

        self.init_ui()

        # 저장된 API URL값과 서비스키값을 불러옴
        self.load_saved_values()

    def init_ui(self):
        self.setWindowTitle('API 다운로더')

        self.api_label = QLabel('API URL:')
        self.api_input = QLineEdit(self)

        self.service_key_label = QLabel('서비스 키:')
        self.service_key_input = QLineEdit(self)

        self.param_labels = []
        self.param_inputs = []

        self.add_default_parameters()

        self.add_param_button = QPushButton('+', self)
        self.add_param_button.clicked.connect(self.add_parameter)

        self.remove_param_button = QPushButton('-', self)
        self.remove_param_button.clicked.connect(self.remove_parameter)
        
        self.call_button = QPushButton('호출', self)
        self.call_button.clicked.connect(self.data_preview)

        self.preview_label = QLabel('미리보기:')
        self.preview_table = QTableWidget(self)
        self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.preview_table.verticalHeader().setVisible(False)

        self.download_button = QPushButton('다운로드')
        self.download_button.clicked.connect(self.download_data)

        # 수직 박스 레이아웃
        v_layout = QVBoxLayout()
        v_layout.addWidget(self.api_label)
        v_layout.addWidget(self.api_input)
        v_layout.addWidget(self.service_key_label)
        v_layout.addWidget(self.service_key_input)

        # 파라미터 레이블 및 입력 필드를 수직 박스 레이아웃에 추가
        for i in range(len(self.param_labels)):
            v_layout.addWidget(self.param_labels[i])
            v_layout.addWidget(self.param_inputs[i])

        # 파라미터 추가 및 제거 버튼을 수평 박스 레이아웃에 추가
        h_button_layout1 = QHBoxLayout()
        h_button_layout1.addWidget(self.add_param_button)
        h_button_layout1.addWidget(self.remove_param_button)
        v_layout.addLayout(h_button_layout1)

        v_layout.addWidget(self.call_button)
        
        v_layout.addWidget(self.preview_label)
        v_layout.addWidget(self.preview_table)

        v_layout.addWidget(self.download_button)

        self.setLayout(v_layout)

    def add_default_parameters(self):
        default_params = ['pageNo', 'numOfRows', 'dataType', 'base_date', 'base_time', 'nx', 'ny']
        for param_name in default_params:
            param_label = QLabel(f'{param_name}:')
            param_input = QLineEdit(self)
            self.param_labels.append(param_label)
            self.param_inputs.append(param_input)

    def add_parameter(self): # 파라미터 입력 칸이 호출 버튼 아래에 추가됨.. 수정 필요
        param_name, ok = QInputDialog.getText(self, '파라미터 추가', '파라미터명:')
        if ok and param_name:
            param_label = QLabel(f'{param_name}:')
            param_input = QLineEdit(self)
            self.param_labels.append(param_label)
            self.param_inputs.append(param_input)
            v_layout = self.layout()
            
            v_layout.insertWidget(v_layout.indexOf(self.call_button), param_label)
            v_layout.insertWidget(v_layout.indexOf(self.call_button), param_input)

    def remove_parameter(self):
        if self.param_labels:
            param_label = self.param_labels.pop()
            param_input = self.param_inputs.pop()
            param_label.deleteLater()
            param_input.deleteLater()
            v_layout = self.layout()
            v_layout.removeWidget(param_label)
            v_layout.removeWidget(param_input)
            param_label.setParent(None)
            param_input.setParent(None)

    def data_preview(self):
        data_retriever = ApiDataRetriever(self.api_input, self.service_key_input, self.param_labels, self.param_inputs, self.preview_table)
        data_retriever.data_preview()

    def save_values(self):
        # 조회할 때마다 API URL과 서비스키를 저장
        with open("saved_values.txt", "w") as f:
            f.write(f"{self.api_input.text()}\n{self.service_key_input.text()}")

    def load_saved_values(self):
        try:
            with open("saved_values.txt", "r") as f:
                lines = f.readlines()
                if len(lines) >= 2:
                    self.api_input.setText(lines[0].strip())
                    self.service_key_input.setText(lines[1].strip())
        except FileNotFoundError:
            pass
    
    def download_data(self):
        print('다운로드 왜 안돼')

def main():
    # 이미 QApplication이 생성되었는지 확인하고, 없으면 생성
    if not QApplication.instance():
        global app
        app = QApplication(sys.argv)

    # GUI 실행
    downloader = DataDownloader()
    downloader.show()

    # 주피터 노트북에서 실행할 때 블로킹하지 않도록 이벤트 루프를 실행
    if app:
        sys.exit(app.exec_())

# 메인 실행
if __name__ == "__main__":
    main()
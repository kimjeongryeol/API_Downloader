import sys
import pymysql
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView, QSizePolicy, QMessageBox
from PyQt5.QtWidgets import QInputDialog
from PyQt5.QtWidgets import QHBoxLayout
import requests
import xml.etree.ElementTree as ET
import pandas as pd

class DataDownloader(QWidget):
    def __init__(self):
        super().__init__()

        self.init_ui()

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

        self.save_param_button = QPushButton('저장', self)
        self.save_param_button.clicked.connect(self.save_parameter)

        self.open_param_button = QPushButton('불러오기', self)
        self.open_param_button.clicked.connect(self.download_parameters)

        self.call_button = QPushButton('조회', self)
        self.call_button.clicked.connect(self.data_preview)

        self.preview_label = QLabel('미리보기:')
        self.preview_table = QTableWidget(self)
        self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.preview_table.verticalHeader().setVisible(False)

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

        h_button_layout2 = QHBoxLayout()
        h_button_layout2.addWidget(self.save_param_button)
        h_button_layout2.addWidget(self.open_param_button)
        v_layout.addLayout(h_button_layout2)

        v_layout.addWidget(self.call_button)
        v_layout.addWidget(self.preview_label)
        v_layout.addWidget(self.preview_table)

        self.setLayout(v_layout)

    def add_default_parameters(self):
        default_params = ['pageNo', 'numOfRows', 'dataType', 'base_date', 'base_time', 'nx', 'ny']
        for param_name in default_params:
            param_label = QLabel(f'{param_name}:')
            param_input = QLineEdit(self)
            self.param_labels.append(param_label)
            self.param_inputs.append(param_input)

    def add_parameter(self):
        param_name, ok = QInputDialog.getText(self, '파라미터 추가', '파라미터명:')
        if ok and param_name:
            param_label = QLabel(f'{param_name}:')
            param_input = QLineEdit(self)
            self.param_labels.append(param_label)
            self.param_inputs.append(param_input)
            v_layout = self.layout()
            v_layout.insertWidget(v_layout.count() - 3, param_label)  # Insert label before the "-" button
            v_layout.insertWidget(v_layout.count() - 3, param_input)  # Insert input before the "-" button

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

    def save_parameter(self):
        print('저장')

    def open_parameter(self):
        print('불러오기')

    def data_preview(self):
        api_url = self.api_input.text()
        service_key = self.service_key_input.text()

        if not service_key:
            QMessageBox.critical(self, '에러', '서비스 키를 입력하세요.')
            return

        params = {'serviceKey': service_key}

        for i, param_input in enumerate(self.param_inputs):
            param_name = self.param_labels[i].text().replace(':', '').strip()
            if param_name:
                params[param_name] = param_input.text()

        try:
            response = requests.get(api_url, params=params)
            response.raise_for_status()

            # XML 파싱
            root = ET.fromstring(response.text)

            # 열 이름 및 값 추출
            columns = ["baseDate", "baseTime", "category", "fcstDate", "fcstTime", "fcstValue", "nx", "ny"]
            data = []

            for item in root.find(".//items"):
                row = [item.find(col).text for col in columns]
                data.append(row)


            # 테이블 미리보기
            self.preview_table.setColumnCount(len(columns))
            self.preview_table.setHorizontalHeaderLabels(columns)
            self.preview_table.setRowCount(len(data))

            for row_idx, row_data in enumerate(data):
                for col_idx, col_data in enumerate(row_data):
                    item = QTableWidgetItem(col_data)
                    self.preview_table.setItem(row_idx, col_idx, item)

        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, '에러', f"다운로드 중 오류 발생: {e}")

    def download_parameters(self):
        # Gather parameters from inputs
        params_data = [{"label": label.text().replace(':', '').strip(), "value": input.text()} for label, input in zip(self.param_labels, self.param_inputs)]

        # Create a connection to the database
        try:
            connection = pymysql.connect(
                host='127.0.0.1',
                port = '5432',
                user='postgres',
                password='1234',
                database='kwater1',
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )

            with connection.cursor() as cursor:
                # Construct the SQL query for inserting data into the table
                columns = ["api_url", "service_key"] + [f"parameter{i+1}" for i in range(len(params_data))]
                values = [self.api_input.text(), self.service_key_input.text()] + [param["value"] for param in params_data]
                sql = f"INSERT INTO Parameters ({', '.join(columns)}) VALUES ({', '.join(['%s'] * len(values))})"

                # Execute the SQL query
                cursor.execute(sql, values)

            # Commit the changes
            connection.commit()

            QMessageBox.information(self, '성공', '파라미터가 성공적으로 저장되었습니다.')

        except pymysql.MySQLError as e:
            QMessageBox.critical(self, '에러', f"데이터베이스 오류 발생: {e}")

        finally:
            # Close the database connection
            if connection:
                connection.close()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    downloader = DataDownloader()
    downloader.show()
    sys.exit(app.exec_())
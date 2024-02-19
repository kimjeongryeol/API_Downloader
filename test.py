import sys
from urllib.parse import parse_qs, urlparse
import psycopg2
import requests
import xml.etree.ElementTree as ET
from tkinter import messagebox
from psycopg2.extras import execute_values
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, 
    QTableWidget, QHeaderView, QTableWidgetItem, QMessageBox, 
    QInputDialog, QHBoxLayout, QVBoxLayout
)

class ApiCall:
    def __init__(self, key, url):
        self.key = key
        self.url = url

    def call(self, **kwargs):
        params = {'dataType': 'XML'}
        params['serviceKey'] = self.key
    
        for key in kwargs.keys():
            params[key] = kwargs[key]
        try:
            response =  requests.get(self.url, params=params)
            return response
        except requests.exceptions.RequestException as e:
            messagebox.critical(None, '에러', f"호출 중 오류 발생: {e}")
            return None
        
class ParameterSaver:
    @staticmethod
    def F_connectPostDB():
        host = '127.0.0.1'
        port = '5432'
        user = 'postgres'
        password = '1234'
        database = 'kwater1'

        global isconnect

        try:
            # PostgreSQL 연결
            connection = psycopg2.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database
            )

            cursor = connection.cursor()
            print("PostgreSQL 데이터베이스 연결 성공!")

            isconnect = 1

        except (Exception, psycopg2.Error) as error:
            print("PostgreSQL 오류: ",error)
            return None, None

        return connection, cursor

    @staticmethod
    def F_ConnectionClose(cursor, connection):
        cursor.close()
        connection.close()
        isconnect = 0
        print("데이터 베이스 연결 해제")

    def __init__(self, url, api_input, service_key_input, param_labels, param_inputs):
        self.url = url
        self.api_input = api_input
        self.service_key_input = service_key_input
        self.param_labels = param_labels
        self.param_inputs = param_inputs

    def save_parameters(self):
        connection, cursor = self.F_connectPostDB()  # F_connectPostDB 함수로 연결
        if not connection or not cursor:
            return

        try:
            self.insert_parameters_data(cursor, connection)
            QMessageBox.information(None, '성공', 'URL이 성공적으로 저장되었습니다.')
        except Exception as e:
            QMessageBox.critical(None, '에러', f"데이터베이스 오류 발생: {e}")
        finally:
            if connection:
                connection.close()

    def insert_parameters_data(self, cursor, connection):
        try:
            cursor.execute("INSERT INTO URL_TB (url) VALUES (%s)", (self.url, ))
            connection.commit()
            print("URL이 성공적으로 저장되었습니다.")
        except psycopg2.Error as e:
            print(f"에러 발생: {e}")
            raise e

class MyWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setup()
        self.response = None

    def setup(self):
        self.setWindowTitle('API 다운로더')

        self.api_label = QLabel('API URL:')
        self.api_input = QLineEdit(self)

        self.service_key_label = QLabel('서비스 키:')
        self.service_key_input = QLineEdit(self)

        self.param_labels = []
        self.param_inputs = []

        self.add_param_button = QPushButton('+', self)
        self.add_param_button.clicked.connect(self.add_parameter)

        self.remove_param_button = QPushButton('-', self)
        self.remove_param_button.clicked.connect(self.remove_parameter)

        self.call_button = QPushButton('호출', self)
        self.call_button.clicked.connect(self.api_call)

        self.download_params_button = QPushButton('파라미터 다운로드', self)
        self.download_params_button.clicked.connect(self.download_parameters)

        self.download_button = QPushButton('파일 저장')
        #self.download_button.clicked.connect(self.download_data)

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
        h_button_layout = QHBoxLayout()
        h_button_layout.addWidget(self.add_param_button)
        h_button_layout.addWidget(self.remove_param_button)

        v_layout.addLayout(h_button_layout)

        v_layout.addWidget(self.call_button)
        v_layout.addWidget(self.download_params_button)
        
        v_layout.addWidget(self.preview_label)
        v_layout.addWidget(self.preview_table)

        v_layout.addWidget(self.download_button)

        self.setLayout(v_layout)

    def add_parameter(self):
        param_name, ok = QInputDialog.getText(self, '파라미터 추가', '파라미터명:')
        if ok and param_name:
            param_label = QLabel(f'{param_name}:')
            param_input = QLineEdit(self)
            self.param_labels.append(param_label)
            self.param_inputs.append(param_input)
            v_layout = self.layout()

            index = v_layout.indexOf(self.call_button)  # 호출 버튼의 인덱스 찾기
            v_layout.insertWidget(index-1, param_input)
            v_layout.insertWidget(index-1, param_label)

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

    def get_parameters(self):
        # 입력된 파라미터 수집
        params = {}
        for label, input_field in zip(self.param_labels, self.param_inputs):
            param_name = label.text().replace(':', '').strip()
            param_value = input_field.text()
            if param_name and param_value:
                params[param_name] = param_value
        return params

    def get_data(self, response_text):
        # XML 데이터 파싱 및 열 추출
        root = ET.fromstring(response_text)
        first_item = root.find(".//item")
        columns = [child.tag for child in first_item]

        # 데이터 추출
        data = []
        for item in root.find(".//items"):
            row = [item.find(col).text for col in columns]
            data.append(row)

        return columns, data

    def show_preview(self, columns, data):
        # 미리보기 테이블 업데이트
        self.preview_table.setColumnCount(len(columns))
        self.preview_table.setHorizontalHeaderLabels(columns)
        self.preview_table.setRowCount(len(data))

        for row_idx, row_data in enumerate(data):
            for col_idx, col_data in enumerate(row_data):
                item = QTableWidgetItem(col_data)
                self.preview_table.setItem(row_idx, col_idx, item)

    def api_call(self):
        url = self.api_input.text()
        service_key = self.service_key_input.text()
        
        if not service_key:
            QMessageBox.critical(None, '에러', '서비스 키를 입력하세요.')
            return
        
        # ApiCall 객체 생성
        api_caller = ApiCall(key=service_key, url=url)
        
        # 파라미터 설정
        params = self.get_parameters()
        
        # API 호출 및 응답 확인
        self.response = api_caller.call(serviceKey=service_key, **params)
        
        if self.response:
            # API 응답 처리 및 미리보기 업데이트
            columns, data = self.get_data(self.response.text)
            self.show_preview(columns, data)

    def download_parameters(self):
        if self.response:
            
            parameter_saver = ParameterSaver(self.response.url, self.api_input, self.service_key_input, self.param_labels, self.param_inputs)
            parameter_saver.save_parameters()
        else:
            QMessageBox.critical(None, '에러', '먼저 API를 호출하세요.')
            return

class DataDownload:
    def save_csv():
        pass
    def save_xml():
        pass
    def save_json():
        pass
    def save_xlsx():
        pass

def main():
    # QApplication이 생성되었는지 확인하고, 없으면 생성
    if not QApplication.instance():
        global app
        app = QApplication(sys.argv)
    
    # GUI 실행
    downloader = MyWidget()
    downloader.show()

    # 주피터 노트북에서 실행할 때 블로킹하지 않도록 이벤트 루프를 실행
    if app:
        sys.exit(app.exec_())

# 메인 실행
if __name__ == "__main__":
    main()
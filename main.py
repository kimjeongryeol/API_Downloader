import sys
import psycopg2
import requests
import xml.etree.ElementTree as ET
import codecs
import csv
import json
import sys
import traceback
import openpyxl
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QTableWidget, QTableWidgetItem, QFileDialog, QHeaderView, QMessageBox
from PyQt5.QtWidgets import QInputDialog
from PyQt5.QtWidgets import QHBoxLayout
from psycopg2.extras import execute_values

class ApiDataRetriever:
    def __init__(self, api_input, service_key_input, param_labels, param_inputs, preview_table):
        self.api_input = api_input
        self.service_key_input = service_key_input
        self.param_labels = param_labels
        self.param_inputs = param_inputs
        self.preview_table = preview_table
        self.columns = []
        self.api_data = None

    def call_api(self):
        api_url = self.api_input.text()
        service_key = self.service_key_input.text()

        if not service_key:
            QMessageBox.critical(None, '에러', '서비스 키를 입력하세요.')
            return None
        
        params = {'serviceKey': service_key, 'dataType': 'XML'}

        for i, param_input in enumerate(self.param_inputs):
            param_name = self.param_labels[i].text().replace(':', '').strip()
            if param_name:
                params[param_name] = param_input.text()

        try:
            response = requests.get(api_url, params=params)
            response.raise_for_status()
            self.api_data = response.text  # API 데이터를 저장
            return self.api_data

        except requests.exceptions.RequestException as e:
            QMessageBox.critical(None, '에러', f"다운로드 중 오류 발생: {e}")
            return None

    def show_preview(self):
        api_data = self.call_api()
        root = ET.fromstring(api_data)
        print(self.api_data)

        columns = self.get_columns()
        data = []     # 미리보기에 출력할 데이터를 저장할 리스트

         # XML 데이터를 탐색하면서 데이터 추출
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

    def get_columns(self):
        root = ET.fromstring(self.call_api())  # XML 데이터 파싱하여 루트 요소 가져오기
        first_item = root.find(".//item")
        columns = [child.tag for child in first_item]
        return columns
    
    def get_data(self):
        return self.api_data
    
def F_ConnectPostDB():
    host = '127.0.0.1'
    port = '5432'
    user = 'postgres'
    password = '1234'
    database = 'kwater1'
    
    global isconnect
    
    try :
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

    return connection, cursor
    
def F_ConnectionClose(cursor, connection):
    cursor.close()
    connection.close()
    isconnect = 0
    print("데이터 베이스 연결 해제")

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

    def __init__(self, api_input, service_key_input, param_labels, param_inputs):
        self.api_input = api_input
        self.service_key_input = service_key_input
        self.param_labels = param_labels
        self.param_inputs = param_inputs

    def save_url(self):
        connection, cursor = self.F_connectPostDB()  # F_connectPostDB 함수로 연결
        if not connection or not cursor:
            return

        try:
            self.insert_parameters_data(cursor, connection)
            QMessageBox.information(None, '성공', '파라미터가 성공적으로 저장되었습니다.')
        except Exception as e:
            QMessageBox.critical(None, '에러', f"데이터베이스 오류 발생: {e}")
        finally:
            if connection:
                connection.close()

    def insert_parameters_data(self, cursor, connection):
        # Initialize params_data with api_url and service_key
        params_data = [self.api_input.text(), self.service_key_input.text()]

        # Add parameter values to params_data
        for param_input in self.param_inputs:
            params_data.append(param_input.text() or None)

        try:
            execute_values(cursor, "INSERT INTO Parameters (api_url, service_key, parameter1, parameter2, parameter3, parameter4, parameter5, parameter6) VALUES %s", [params_data])
            connection.commit()
        except psycopg2.Error as e:
            print(f"에러 발생: {e}")
            raise e
        
class DataDownloader(QWidget):
    def __init__(self):
        super().__init__()

        self.init_ui()
        self.data_retriever = ApiDataRetriever(self.api_input, self.service_key_input, self.param_labels, self.param_inputs, self.preview_table)

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

        self.download_params_button = QPushButton('파라미터 다운로드', self)
        self.download_params_button.clicked.connect(self.download_parameters)

        self.download_button = QPushButton('다운로드')
        self.download_button.clicked.connect(self.download_data)

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

        v_layout.addWidget(self.call_button)
        v_layout.addWidget(self.download_params_button)
        
        v_layout.addWidget(self.preview_label)
        v_layout.addWidget(self.preview_table)

        v_layout.addWidget(self.download_button)

        self.setLayout(v_layout)

    def add_default_parameters(self):
        default_params = ['pageNo', 'numOfRows', 'base_date', 'base_time', 'nx', 'ny']
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

            index = v_layout.indexOf(self.call_button)  # 호출 버튼의 인덱스 찾기
            v_layout.insertWidget(index-1, param_label)
            v_layout.insertWidget(index-1, param_input)

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
        self.data_retriever.show_preview()

    def download_parameters(self):
        parameter_saver = ParameterSaver(self.api_input, self.service_key_input, self.param_labels, self.param_inputs)
        parameter_saver.save_parameters()
        
    def download_data(self):
        api_data = self.data_retriever.api_data

        if api_data:
            file_types = "CSV files (*.csv);;XML files (*.xml);;JSON files (*.json);;Excel files (*.xlsx)"
            file_path, file_type = QFileDialog.getSaveFileName(self, "Save File", "", file_types)
            if file_path:
                if file_type == "XML files (*.xml)":
                    self.save_xml(api_data, file_path)
                elif file_type == "JSON files (*.json)":
                    self.save_json(api_data, file_path)
                elif file_type == "CSV files (*.csv)":
                    self.save_csv(api_data, file_path)
                elif file_type == "Excel files (*.xlsx)":
                    self.save_xlsx(api_data, file_path)
    
    def save_xml(self, api_data, file_path):
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(api_data)

    def save_csv(self, api_data, file_path):
        root = ET.fromstring(api_data)  # XML 데이터 파싱하여 루트 요소 가져오기
        data = []

        first_item = root.find(".//item")
        columns = [child.tag for child in first_item]

        for item in root.findall(".//item"):
            row = [child.text for child in item]
            data.append(row)

        with codecs.open(file_path, 'w', 'utf-8-sig') as file:
            writer = csv.writer(file)
            writer.writerow(columns)
            writer.writerows(data)

    def save_json(self, api_data, file_path):
        # XML 데이터 파싱
        root = ET.fromstring(api_data)

        # 변환된 JSON 데이터를 저장할 리스트 초기화
        json_data = []

        # XML 요소를 반복하여 JSON 데이터로 변환
        for item in root.find(".//items"):
            row = {}
            for child in item:
                row[child.tag] = child.text
            json_data.append(row)

        # JSON 데이터를 파일에 저장
        with open(file_path, 'w') as json_file:
            json.dump(json_data, json_file, indent=4)
        print("JSON 파일 저장 성공")
    
    def save_xlsx(self, api_data, file_path):
        try:
            root = ET.fromstring(api_data)
            columns = ["baseDate", "baseTime", "category", "fcstDate", "fcstTime", "fcstValue", "nx", "ny"]
            data = []

            for item in root.find(".//items"):
                row = [item.find(col).text for col in columns]
                data.append(row)

            workbook = openpyxl.Workbook()
            sheet = workbook.active
            sheet.append(columns)
            for row_data in data:
                sheet.append(row_data)

            workbook.save(file_path)
            print("Excel 파일 저장 성공")

        except Exception as e:
            print("Excel 파일 저장 실패")
            print(traceback.format_exc())

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
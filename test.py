import csv
import json
import sys
import openpyxl
import xml.etree.ElementTree as ET
import psycopg2
import requests
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QDialog,
    QTableWidget, QHeaderView, QTableWidgetItem, QMessageBox, 
    QInputDialog, QHBoxLayout, QVBoxLayout, QFileDialog, QAbstractItemView
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
            QMessageBox.critical(None, '에러', f"호출 중 오류 발생: {e}")
            return None
        
class ParameterSaver:
    @staticmethod
    def F_connectPostDB():
        host = '127.0.0.1'
        port = '5432'
        user = 'postgres'
        password = '1234'
        database = 'kwater1'

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

            return connection, cursor

        except psycopg2.Error as error:
            print("PostgreSQL 오류: ", error)
            return None, None

    @staticmethod
    def F_ConnectionClose(cursor, connection):
        cursor.close()
        connection.close()
        print("데이터 베이스 연결 해제")

    def __init__(self, id, url):
        self.id = id
        self.url = url

    def save_parameters(self):
        connection, cursor = self.F_connectPostDB()  
        if not connection or not cursor:
            return

        try:
            # 중복된 ID인지 확인
            cursor.execute("SELECT COUNT(*) FROM URL_TB WHERE id = %s", (self.id,))
            count = cursor.fetchone()[0]
            if count > 0:
                QMessageBox.warning(None, '중복된 값', '중복된 ID 값입니다.')
                return

            cursor.execute("INSERT INTO URL_TB (id, url) VALUES (%s, %s)", (self.id, self.url))
            connection.commit()
            QMessageBox.information(None, '성공', 'URL이 성공적으로 저장되었습니다.')
        except psycopg2.Error as e:
            print(f"에러 발생: {e}")
            QMessageBox.critical(None, '에러', f"데이터베이스 오류 발생: {e}")
        finally:
            if connection:
                self.F_ConnectionClose(cursor, connection)

class DataParser:
    @staticmethod
    def parse_xml(api_data):
        try:
            root = ET.fromstring(api_data)
            columns = []
            data = []

            # items 요소가 있는지 확인
            items_element = root.find(".//items")
            if items_element:
                # items 요소가 있는 경우, 기존의 처리 방식으로 진행
                first_item = root.find(".//item")
                columns = [child.tag for child in first_item]

                for item in items_element:
                    row = [item.find(col).text for col in columns]
                    data.append(row)
            else:
                # items 요소가 없는 경우
                sub_data = []
                result_code = root.find(".//resultCode")
                if result_code is not None:
                    columns.append("resultCode")
                    sub_data.append(result_code.text)

                result_msg = root.find(".//resultMsg")
                if result_msg is not None:
                    columns.append("resultMsg")
                    sub_data.append(result_msg.text)
                data.append(sub_data)
            return columns, data
        except ET.ParseError as e:
            print("XML 파싱 오류:", e)
            return None, None  # XML 파싱 오류인 경우 None을 반환
        
class PreviewUpdater:
    @staticmethod
    def show_preview(preview_table, columns, data):
        # 미리보기 테이블 업데이트
        preview_table.setColumnCount(len(columns))
        preview_table.setHorizontalHeaderLabels(columns)
        preview_table.setRowCount(len(data))

        for row_idx, row_data in enumerate(data):
            for col_idx, col_data in enumerate(row_data):
                item = QTableWidgetItem(col_data)
                preview_table.setItem(row_idx, col_idx, item)

class ParameterViewer(QWidget):
    def __init__(self, my_widget_instance):
        super().__init__()
        self.my_widget_instance = my_widget_instance
        self.setWindowTitle('파라미터 목록')
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # 테이블 위젯 생성
        self.param_table = QTableWidget()
        self.param_table.resizeColumnsToContents()
        self.param_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.param_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.load_parameter_list()
        layout.addWidget(self.param_table)

        # 확인 버튼 추가
        confirm_button = QPushButton('확인')
        confirm_button.clicked.connect(self.on_confirm_button_clicked)
        layout.addWidget(confirm_button)

        self.setLayout(layout)
        
    def load_parameter_list(self):
        connection, cursor = ParameterSaver.F_connectPostDB()
        if not connection or not cursor:
            return

        try:
            cursor.execute("SELECT * FROM URL_TB")
            rows = cursor.fetchall()
            num_rows = len(rows)
            num_cols = len(rows[0]) if num_rows > 0 else 0

            # 행과 열 수 설정
            self.param_table.setRowCount(num_rows)
            self.param_table.setColumnCount(num_cols)

            # 헤더 설정
            header_labels = ["ID", "URL"]  # 컬럼 헤더 이름 설정
            self.param_table.setHorizontalHeaderLabels(header_labels)

            # 데이터 추가
            for row_idx, row in enumerate(rows):
                for col_idx, col_value in enumerate(row):
                    item = QTableWidgetItem(str(col_value))
                    self.param_table.setItem(row_idx, col_idx, item)

            self.param_table.resizeColumnsToContents()

        except psycopg2.Error as e:
            QMessageBox.critical(None, '에러', f"데이터베이스 오류 발생: {e}")

        finally:
            ParameterSaver.F_ConnectionClose(cursor, connection)

    def on_confirm_button_clicked(self):
        # 선택된 행 가져오기
        selected_items = self.param_table.selectedItems()
        if selected_items:
            selected_row = selected_items[0].row()
            # 선택된 행의 URL 출력
            url_item = self.param_table.item(selected_row, 1)  # URL 열에 해당하는 아이템 가져오기
            if url_item:
                url = url_item.text()
                self.my_widget_instance.response = requests.get(url)
                columns, data = DataParser.parse_xml(self.my_widget_instance.response.text)
                PreviewUpdater.show_preview(self.my_widget_instance.preview_table, columns, data)
            else:
                print("선택된 행의 URL이 없습니다.")
        else:
            print("선택된 행이 없습니다.")

class MyWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setup()
        self.response = None

    def setup(self):
        self.setWindowTitle('API 다운로더')

        self.param_layout = QVBoxLayout()

        self.api_label = QLabel('API URL')
        self.api_input = QLineEdit(self)
        self.add_param_row(self.api_label, self.api_input)

        self.key_label = QLabel('서비스 키')
        self.key_input = QLineEdit(self)
        self.add_param_row(self.key_label, self.key_input)

        self.param_labels = []
        self.param_inputs = []

        self.add_param_button = QPushButton('파라미터 추가', self)
        self.add_param_button.clicked.connect(self.add_parameter)

        self.remove_param_button = QPushButton('파라미터 삭제', self)
        self.remove_param_button.clicked.connect(self.remove_parameter)

        self.download_params_button = QPushButton('파라미터 저장', self)
        self.download_params_button.clicked.connect(self.download_parameters)

        self.show_params_button = QPushButton('파라미터 목록', self)
        self.show_params_button.clicked.connect(self.show_parameters)

        self.call_button = QPushButton('OpenAPI 호출', self)
        self.call_button.clicked.connect(self.api_call)

        self.download_button = QPushButton('API 호출정보 저장')
        self.download_button.clicked.connect(self.download_data)

        self.preview_label = QLabel('미리보기')
        self.preview_table = QTableWidget(self)
        self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.preview_table.verticalHeader().setVisible(False)

        # 수직 박스 레이아웃
        v_layout = QVBoxLayout()
        v_layout.addLayout(self.param_layout)

        # 파라미터 추가 및 제거 버튼을 수평 박스 레이아웃에 추가
        h_button_layout1 = QHBoxLayout()
        h_button_layout1.addWidget(self.add_param_button)
        h_button_layout1.addWidget(self.remove_param_button)

        v_layout.addLayout(h_button_layout1)

        h_button_layout2 = QHBoxLayout()
        h_button_layout2.addWidget(self.download_params_button)
        h_button_layout2.addWidget(self.show_params_button)

        v_layout.addLayout(h_button_layout2)

        v_layout.addWidget(self.call_button)
        
        v_layout.addWidget(self.preview_label)
        v_layout.addWidget(self.preview_table)

        v_layout.addWidget(self.download_button)

        self.setLayout(v_layout)

    def add_param_row(self, label_widget, edit_widget):
        h_layout = QHBoxLayout()
        label_widget.setMinimumWidth(100)  # 라벨의 최소 너비 설정
        h_layout.addWidget(label_widget)
        h_layout.addWidget(edit_widget)
        self.param_layout.addLayout(h_layout)

    def add_parameter(self):
        param_name, ok = QInputDialog.getText(self, '파라미터 추가', '파라미터명:')
        if ok and param_name:
            param_label = QLabel(f'{param_name}')
            param_input = QLineEdit(self)
            self.param_labels.append(param_label)
            self.param_inputs.append(param_input)
            self.add_param_row(param_label, param_input)

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
            param_name = label.text()
            param_value = input_field.text()
            if param_name and param_value:
                params[param_name] = param_value
        return params

    # def show_preview(self, columns, data):
    #     # 미리보기 테이블 업데이트
    #     self.preview_table.setColumnCount(len(columns))
    #     self.preview_table.setHorizontalHeaderLabels(columns)
    #     self.preview_table.setRowCount(len(data))

    #     for row_idx, row_data in enumerate(data):
    #         for col_idx, col_data in enumerate(row_data):
    #             item = QTableWidgetItem(col_data)
    #             self.preview_table.setItem(row_idx, col_idx, item)

    def api_call(self):
        url = self.api_input.text()
        service_key = self.key_input.text()

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
            columns, data = DataParser.parse_xml(self.response.text)
            PreviewUpdater.show_preview(self.preview_table, columns, data)
        else:
            print('호출 실패')
    def download_parameters(self):
        if self.response:
            id, ok = QInputDialog.getText(self, '저장명 입력', '저장할 ID를 입력하세요:')
            if ok:
                parameter_saver = ParameterSaver(id, self.response.url)
                parameter_saver.save_parameters()
        else:
            QMessageBox.critical(None, '에러', '먼저 API를 호출하세요.')
            return
        
    def show_parameters(self):
        self.parameter_viewer = ParameterViewer(self)
        self.parameter_viewer.show()

    def download_data(self):
        data = self.response.text

        if data:
            file_types = "CSV files (*.csv);;XML files (*.xml);;JSON files (*.json);;Excel files (*.xlsx)"
            file_path, file_type = QFileDialog.getSaveFileName(self, "Save File", "", file_types)
            if file_path:
                downloader = DataDownload(data)
                if file_type == "XML files (*.xml)":
                    downloader.save_xml(file_path)
                elif file_type == "JSON files (*.json)":
                    downloader.save_json(file_path)
                elif file_type == "CSV files (*.csv)":
                    downloader.save_csv(file_path)
                elif file_type == "Excel files (*.xlsx)":
                    downloader.save_xlsx(file_path)
        else:
            QMessageBox.critical(None, '에러', 'API 데이터를 가져오지 못했습니다.')

class DataDownload:
    def __init__(self, api_data):
        self.api_data = api_data

    def save_xml(self, file_path):
        try:
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(self.api_data)
            print("XML 파일 저장 성공")
        except Exception as e:
            print("XML 파일 저장 실패:", e)

    def save_csv(self, file_path):
        try:
             # XML 데이터 파싱 및 열 추출
            root = ET.fromstring(self.api_data)
            first_item = root.find(".//item")
            columns = [child.tag for child in first_item]

            # 데이터 추출
            csv_data = []
            for item in root.find(".//items"):
                row = [item.find(col).text for col in columns]
                csv_data.append(row)

            with open(file_path, 'w', newline='', encoding='utf-8-sig') as file:
                writer = csv.writer(file)
                writer.writerow(columns)
                writer.writerows(csv_data)

            print("CSV 파일 저장 성공")
        except Exception as e:
            print("CSV 파일 저장 실패:", e)

    def save_json(self, file_path):
        try:
            # XML 데이터 파싱 및 열 추출
            root = ET.fromstring(self.api_data)
            first_item = root.find(".//item")

            # 데이터 추출
            json_data = []
            
            # XML 요소를 반복하여 JSON 데이터로 변환
            for item in root.find(".//items"):
                row = {}
                for child in item:
                    row[child.tag] = child.text
                json_data.append(row)

            with open(file_path, 'w', encoding='utf-8') as json_file:
                json.dump(json_data, json_file, indent=4)

            print("JSON 파일 저장 성공")
        except Exception as e:
            print("JSON 파일 저장 실패:", e)

    def save_xlsx(self, file_path):
        try:
            # XML 데이터 파싱 및 열 추출
            root = ET.fromstring(self.api_data)
            first_item = root.find(".//item")
            columns = [child.tag for child in first_item]

            # 데이터 추출
            xlsx_data = []
            for item in root.find(".//items"):
                row = [item.find(col).text for col in columns]
                xlsx_data.append(row)

            workbook = openpyxl.Workbook()
            sheet = workbook.active
            sheet.append(columns)
            for row_data in xlsx_data:
                sheet.append(row_data)

            workbook.save(file_path)

            print("Excel 파일 저장 성공")
        except Exception as e:
            print("Excel 파일 저장 실패:", e)

def main():
    # QApplication이 생성되었는지 확인하고, 없으면 생성
    if not QApplication.instance():
        global app
        app = QApplication(sys.argv)
    
    # GUI 실행
    downloader = MyWidget()
    
    # 창 초기 상태를 최대화로 설정하여 창 크기를 조절할 수 있게 함
    downloader.setWindowState(Qt.WindowMaximized)
    downloader.setWindowFlags(downloader.windowFlags() | Qt.WindowMaximizeButtonHint)
    
    # 주피터 노트북에서 실행할 때 블로킹하지 않도록 이벤트 루프를 실행
    downloader.show()

    # 주피터 노트북에서 실행할 때 블로킹하지 않도록 이벤트 루프를 실행
    if app:
        sys.exit(app.exec_())

# 메인 실행
if __name__ == "__main__":
    main()
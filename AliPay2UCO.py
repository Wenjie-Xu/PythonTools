import datetime
import gc
import logging
import os
import pandas as pd
import re
import shutil
import traceback
import warnings
from pymysql import connect

import Config as conf
from repostory.Csv_to_utf8 import detectCode
from repostory.SwitchDB import switch_db_env

class SQL_Connect:
    def __init__(self, hostname, port, user, passwd, db):
        # 创捷连接对象
        self.connect = connect(host=hostname, port=port, user=user, passwd=passwd, db=db, charset='utf8');
        # 创建游标
        self.cursor = self.connect.cursor();

    def __del__(self):
        self.cursor.close()
        self.connect.close()

class Data_handle:
    # TODO 读取并处理国内店铺帐单
    def read_csv(self, filepath):
        file_code = detectCode(filepath)
        if conf.BILL_TYPE == 'local':
            # 从第四行开始读取
            df = pd.read_csv(filepath, sep=',', header=4, keep_default_na=False,
                             encoding=file_code, low_memory=False, chunksize=10000)

        if conf.BILL_TYPE == 'foreign':
            df = pd.read_csv(filepath, sep=',', header=0, keep_default_na=False,
                             encoding=file_code, low_memory=False, chunksize=10000)

        return df  # 可迭代对象

    # TODO 处理国内dataframe（字段提取和处理）
    def handle_local_frame(self, df):
        # TODO ELC和普通店铺的提取方式不一样
        if conf.ENVIR == 'UCO':
            columns = ['账务流水号', '业务流水号', '商户订单号', '商品名称', '发生时间',
                       '对方账号', '收入金额（+元）', '支出金额（-元）', '账户余额（元）',
                       '交易渠道', '业务类型', '备注']
            df = df[columns]
            df['账务流水号'] = df['账务流水号'].apply(lambda x: str(x).replace('\t', ''))
            df['业务流水号'] = df['业务流水号'].apply(lambda x: str(x).replace('\t', ''))
            df['商户订单号'] = df['商户订单号'].apply(lambda x: str(x).replace('\t', ''))
            df['商品名称'] = df['商品名称'].apply(lambda x: str(x).replace('\t', ''))
            df['对方账号'] = df['对方账号'].apply(lambda x: str(x).replace('\t', ''))
            df['备注'] = df['备注'].apply(lambda x: str(x).replace('\t', '')[0:10])

        if conf.ENVIR == 'ELC':
            columns = ['Financial batch No', 'Payment batch No', 'Merchant Order number', 'Subject', 'Payment time',
                       'To Account', 'Income Amt', 'Outcome Amt', 'Account balance',
                       'Transaction channel', 'Payment type', 'Supplementary note']
            df = df[columns]
            df['Financial batch No'] = df['Financial batch No'].apply(lambda x: str(x).replace('\t', ''))
            df['Payment batch No'] = df['Payment batch No'].apply(lambda x: str(x).replace('\t', ''))
            df['Merchant Order number'] = df['Merchant Order number'].apply(lambda x: str(x).replace('\t', ''))
            df['Subject'] = df['Subject'].apply(lambda x: str(x).replace('\t', ''))
            df['To Account'] = df['To Account'].apply(lambda x: str(x).replace('\t', ''))
            df['Supplementary note'] = df['Supplementary note'].apply(lambda x: str(x).replace('\t', '')[0:10])
        return df

    # TODO 处理海外帐单（字段提取和处理）
    def handle_foreign_frame(self, df):
        df['Transaction_id'] = df['Transaction_id'].apply(lambda x: str(x).replace('\t', ''))
        columns = ['', '']  # 待提取字段
        return df

    # TODO 将dataframe插入数据库（会识别国内还是海外）
    def insert_df_to_mysql(self, dataframe, filename, filepath):

        platform_name = filepath.split('/')[-3]  # 路径分割，获得店铺名称
        '插入数据'
        df = dataframe
        del dataframe

        # TODO 识别对应的数据表
        if conf.BILL_TYPE == 'local':
            table_name = 'localalipayorderuploading'
            field = ['`Platform_name`', '`File_name`',
                     '`Account_flow`', '`Bussiness_flow`', '`Order_id`', '`Pay_id`', '`Product_name`',
                     '`Happen_time`', '`Other_account`', '`Income_amount`', '`Expenditure_amount`', '`Account_balance`',
                     '`Trading_channel`', '`Bussiness_type`', '`Remark`',
                     '`Created`', '`Updated`']  # 国内表数据表列名列表

        elif conf.BILL_TYPE == 'foreign':
            table_name = 'foreignalipayorderuploading'
            field = ['`Platform_name`', '`File_name`',
                     '`Partner_transaction_id`', '`Transaction_id`', '`Amount`', '`Rmb_amount`',
                     '`Fee`', '`Refund`', '`Settlement`', '`Rmb_settlement`', '`Currency`',
                     '`Rate`', '`Payment_time`', '`Settlement_time`', '`Type`', '`Original_partner_transaction_ID`',
                     '`Created`', '`Updated`']  # 外币表数据表列名列表
        else:
            print("类型选择错误")
            exit(0)

        fields = ','.join(field)  # 数据表列名拼接
        rows = []  # TODO 用于保存每行完整的数据
        values = df.values.tolist()  # TODO 获取df里每一行数据
        # TODO 数据中插入一些自定义数据，并保存到rows列表里
        for value in values:

            value.insert(0, platform_name)  # 第一个位置插入店铺名称
            value.insert(1, filename)  # 第二个位置插入文件名称
            # 国内账单提取
            if conf.BILL_TYPE == 'local':
                value.insert(5, re.findall('T\d+P(\d+)', value[4])[0] if re.findall('T\d+P(\d+)', value[4]) else '')

            value.append(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))  # 每行末尾添加创建时间
            value.append(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))  # 每行末尾添加更新时间
            rows.append(value)

        s = ','.join(['%s' for _ in range(len(field))])
        insert_sql = 'INSERT INTO {}({}) VALUES({}) ON DUPLICATE KEY UPDATE Updated = '.format(table_name, fields, s) \
                     + "'" + datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "';"

        # TODO 插入每个块
        try:
            hostname,port,user,db,passwd = switch_db_env()
            Mysql = SQL_Connect(hostname=hostname, port=port,user=user, db=db, passwd=passwd)
            Mysql.connect.ping(reconnect=True)  # 执行之前判断连接对象是否丢失
            Mysql.cursor.executemany(insert_sql, rows)  # 数组中每一条数据来执行insert_sql
            Mysql.connect.ping(reconnect=True)
            Mysql.connect.commit()
            Mysql.connect.ping(reconnect=True)
            del Mysql  # 释放对象

        except:
            # 将错误日志输入到目录文件中
            f = open("./LOG/error.log", 'a')
            Mysql.connect.rollback()  # 出错回滚
            traceback.print_exc(file=f)
            f.flush()
            f.close()
            print(filename + "表数据异常，请查看日志并修复后重试")
            exit(0)

        print("模块化写入" + str(len(values)) + "行数据(" + datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ")")
        return len(values)

def My_config():
    # TODO 忽略警告
    warnings.filterwarnings("ignore")
    # TODO pd.set_option()就是pycharm输出控制显示的设置
    pd.set_option('expand_frame_repr', False)  # True就是可以换行显示。设置成False的时候不允许换行
    pd.set_option('display.max_columns', None)  # 显示所有列
    pd.set_option('colheader_justify', 'centre')  # 显示居中
    # TODO 配置文件
    log_format = '[%(levelname)s] %(message)s [%(asctime)s]'
    date_format = '%Y-%m-%d %H:%M:%S %p'
    log_file = './LOG/file_done.log'
    logging.basicConfig(filename=log_file, filemode='a',
                        format=log_format, datefmt=date_format, level=logging.INFO)


if __name__ == "__main__":
    # TODO 读取配置文件
    My_config()

    i = 0  # 计数器，后面可以用来统计一共导入了多少个文件
    total_row = 0  # 记录文件夹总共多少行

    tool = Data_handle()
    # TODO 读取根目录
    dir_root = conf.IMPORT_ROOT  # 店铺根目录
    # TODO 获取子目录
    for dir in os.listdir(dir_root):
        dir = os.path.join(dir_root, dir)  # 子目录的完整路径
        # TODO 遍历文件目录
        for file in os.listdir(dir):
            j = 0  # 计数器，记录一个文件一共多少行
            file_path = dir + '/' + file
            # 判断店铺类型
            if conf.BILL_TYPE == 'local':
                # 判断文件是不是汇总文件
                if file.split('.')[-1] in ['csv'] and '汇总' not in file and ('账务明细' in file or 'DETAILS' in file):
                    print("开始处理文件{}".format(file))
                    i += 1
                    dfs = tool.read_csv(file_path)
                    # TODO 迭代数据块
                    for df in dfs:
                        if str(df.iat[-1, 0])[0] == '#' and str(df.iat[-2, 0])[0] == '#':
                            df = df[:-4]  # 通过内容判断是否是最后一个块
                        # TODO 处理过后的dataframe块，和店铺名称
                        df = tool.handle_local_frame(df=df)
                        j += tool.insert_df_to_mysql(dataframe=df, filename=file, filepath=file_path)
                    # TODO 记录日志
                    file_done_info = "{}文件写入完成，共计{}行".format(file, str(j))
                    logging.info(file_done_info)
                    print(file_done_info)
                    total_row += j

                    # TODO 释放资源
                    del dfs  # 一个文件读完，释放dataframe变量
                    gc.collect()  # 释放内存
                    os.remove(file_path)  # 读取完毕删除文件

            elif conf.BILL_TYPE == 'foreign':
                if file.split('.')[-1] in ['csv'] and 'strade' in file:
                    print("开始处理文件{}".format(file))
                    i += 1
                    dfs = tool.read_csv(file_path)
                    # TODO 迭代数据块
                    for df in dfs:
                        # TODO 处理过后的dataframe块，和店铺名称
                        df = tool.handle_local_frame(df=df)
                        j += tool.insert_df_to_mysql(dataframe=df, filename=file, filepath=file_path)
                    # TODO 记录日志
                    file_done_info = "{}文件写入完成，共计{}行".format(file, str(j))
                    logging.info(file_done_info)
                    print(file_done_info)
                    total_row += j

                    # TODO 释放资源
                    del dfs  # 一个文件读完，释放dataframe变量
                    gc.collect()  # 释放内存
                    os.remove(file_path)  # 读取完毕删除文件

        # TODO 删除子文件夹
        shutil.rmtree(dir)

    dir_done_info = "文件夹读取完成，共处理了{}个文件~，共计{}行".format(str(i), str(total_row))
    logging.info(dir_done_info)
    print(dir_done_info)
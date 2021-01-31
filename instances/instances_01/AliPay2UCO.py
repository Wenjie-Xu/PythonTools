import datetime
import os
import pandas as pd
import re
import shutil
import traceback
from pymysql import connect

import Dev_Setting as dev_conf
import instances.instances_01.Config as conf
from repostory.Csv_to_utf8 import handleEncoding


class AliPay2UCO:
    def __init__(self, hostname, port, user, passwd, db):
        # 创捷连接对象
        self.connect = connect(host=hostname, port=port, user=user, passwd=passwd, db=db, charset='utf8');
        # 创建游标
        self.cursor = self.connect.cursor();

    # 读取并处理国内店铺帐单
    def read_local_csv(self, filepath):
        file_code = handleEncoding(filepath)
        # 从第四行开始读取
        df = pd.read_csv(filepath, sep=',', header=4, keep_default_na=False,
                         encoding=file_code, low_memory=False)
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
            df['备注'] = df['备注'].apply(lambda x: str(x).replace('\t', ''))

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
            df['Supplementary note'] = df['Supplementary note'].apply(lambda x: str(x).replace('\t', ''))
        df = df[:-4]  # 去除最后四行
        platform_name = filepath.split('/')[-3]  # 路径分割，获得店铺名称
        return df, platform_name

    # 读取海外帐单
    def read_foreign_csv(self, filepath):
        file_code = handleEncoding(filepath)
        df = pd.read_csv(filepath, sep=',', header=0, keep_default_na=False,
                         encoding=file_code, low_memory=False)
        df['Transaction_id'] = df['Transaction_id'].apply(lambda x: str(x).replace('\t', ''))
        platform_name = filepath.split('/')[-3]
        return df, platform_name

    # 将dataframe处理后插入mysql
    '''
        filename:文件名称
        filepath:文件路径
        platform:从文件路径中提取的店铺
        dataframe:经过处理的dataframe
    '''

    def insert_df_to_mysql(self, filename, filepath, platform, dataframe, type='local'):
        '插入数据'
        df = dataframe
        # 判断是哪种类型的帐单
        if type == 'local':
            table_name = 'localalipayorderuploading'
            field = ['`Platform_name`', '`File_name`',
                     '`Account_flow`', '`Bussiness_flow`', '`Order_id`', '`Pay_id`', '`Product_name`',
                     '`Happen_time`', '`Other_account`', '`Income_amount`', '`Expenditure_amount`', '`Account_balance`',
                     '`Trading_channel`', '`Bussiness_type`', '`Remark`',
                     '`Created`', '`Updated`']  # 国内表数据表列名列表

        elif type == 'foreign':
            table_name = 'ForeignAliPayOrderUploading'
            field = ['`Platform_name`', '`File_name`',
                     '`Partner_transaction_id`', '`Transaction_id`', '`Amount`', '`Rmb_amount`',
                     '`Fee`', '`Refund`', '`Settlement`', '`Rmb_settlement`', '`Currency`',
                     '`Rate`', '`Payment_time`', '`Settlement_time`', '`Type`', '`Original_partner_transaction_ID`',
                     '`Created`', '`Updated`']  # 外币表数据表列名列表
        else:
            print("类型选择错误")
            exit(0)

        fields = ','.join(field)  # 数据表列名拼接
        rows = []  # 用于保存每行完整的数据
        values = df.values.tolist()  # 获取每一行数据数组

        for value in values:
            value.insert(0, platform)  # 第一个位置插入店铺名称
            value.insert(1, filename)  # 第二个位置插入文件名称

            # 国内账单提取
            if type == 'local':
                value.insert(5, re.findall('T\d+P(\d+)', value[4])[0] if re.findall('T\d+P(\d+)', value[4]) else '')

            value.append(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))  # 每行末尾添加创建时间
            value.append(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))  # 每行末尾添加更新时间
            rows.append(value)

        # s = ','.join(['%s' for _ in range(len(df.columns.tolist()))])  # 获得文件数据有多少列，每个列用一个 %s 替代（列表生成式）
        s = ','.join(['%s' for _ in range(len(field))])
        insert_sql = 'INSERT INTO {}({}) VALUES({}) ON DUPLICATE KEY UPDATE Updated = '.format(table_name, fields, s) \
                     + "'" + datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "';"

        for i in range(0, len(rows), 3000):
            child_rows = []
            child_rows = rows[i:i + 3000]
            try:
                self.cursor.executemany(insert_sql, child_rows)  # 数组中每一条数据来执行insert_sql
                self.connect.commit()
                print("写入" + str(len(child_rows)) + "行(" + datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ")")

            except:
                # 将错误日志输入到目录文件中
                f = open("LOG.txt", 'a')
                self.connect.rollback()  # 出错回滚
                traceback.print_exc(file=f)
                f.flush()
                f.close()
                print(filename + "表数据异常，请查看日志并修复后重试")
                exit(0)
        print(filename + "表写入成功，共写入" + str(len(values)) + "行数据")
        return len(values)

    def __del__(self):
        self.cursor.close()
        self.connect.close()


if __name__ == "__main__":
    # pd.set_option()就是pycharm输出控制显示的设置
    pd.set_option('expand_frame_repr', False)  # True就是可以换行显示。设置成False的时候不允许换行
    pd.set_option('display.max_columns', None)  # 显示所有列
    pd.set_option('colheader_justify', 'centre')  # 显示居中

    try:
        tool = AliPay2UCO(hostname=dev_conf.EL_HOST, port=dev_conf.EL_PORT,
                          user=dev_conf.USERNAME, db=dev_conf.DATABASE, passwd=dev_conf.PASSWORD)
        print("数据库连接成功")
    except:
        print("数据库连接失败")

    '读取文件'
    i = 0  # 计数器，后面可以用来统计一共导入了多少个文件
    j = 0  # 计数器，记录一共导入多少行
    dir_root = conf.IMPORT_ROOT  # 店铺根目录
    dirs = os.listdir(dir_root)  # 获取目录列表

    for dir in dirs:
        dir = os.path.join(dir_root, dir)  # 店铺每月文件夹
        files = os.listdir(dir)  # 列出每月明细

        for file in files:  # 遍历文件目录
            file_path = dir + '/' + file
            # 判断店铺类型
            if conf.BILL_TYPE == 'local':
                # 判断文件是不是汇总文件
                if file.split('.')[-1] in ['csv'] and '汇总' not in file and ('账务明细' in file or 'DETAILS' in file):
                    i += 1
                    df, platform_name = tool.read_local_csv(file_path)
                    j += tool.insert_df_to_mysql(filename=file, filepath=file_path, platform=platform_name,
                                                 dataframe=df, type=conf.BILL_TYPE)
                    os.remove(file_path)

            elif conf.BILL_TYPE == 'foreign':
                if file.split('.')[-1] in ['csv'] and 'strade' in file:
                    i += 1
                    df, platform_name = tool.read_foreign_csv(file_path)
                    j += tool.insert_df_to_mysql(filename=file, filepath=file_path, platform=platform_name,
                                                 dataframe=df, type=conf.BILL_TYPE)
                    os.remove(file_path)
        shutil.rmtree(dir)

    print("文件夹读取完成，共处理了{}个文件~，共计{}行".format(str(i), str(j)))

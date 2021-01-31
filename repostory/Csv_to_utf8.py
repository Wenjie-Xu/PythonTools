import codecs
import chardet
import pandas as pd
import gc

def handleEncoding(original_file):
    f = open(original_file, 'rb+')
    content = f.read()  # 读取文件内容，content为bytes类型，而非string类型
    source_encoding = 'utf-8'
    #####确定encoding类型
    try:
        content.decode('utf-8').encode('utf-8')
        source_encoding = 'utf-8'
    except:
        try:
            content.decode('gbk').encode('utf-8')
            source_encoding = 'gbk'
        except:
            try:
                content.decode('gb2312').encode('utf-8')
                source_encoding = 'gb2312'
            except:
                try:
                    content.decode('gb18030').encode('utf-8')
                    source_encoding = 'gb18030'
                except:
                    try:
                        content.decode('big5').encode('utf-8')
                        source_encoding = 'gb18030'
                    except:
                        content.decode('cp936').encode('utf-8')
                        source_encoding = 'cp936'
    f.close()
    return source_encoding

def detectCode(path):
    with open(path, 'rb') as file:
        data = file.read(20000)
        dicts = chardet.detect(data)
    if 'GB' in dicts["encoding"]:
        file_code = 'GB18030'
    else:
        file_code = dicts["encoding"]

    return file_code

if __name__ == "__main__":
    filepath = "C:/Users/Baby_Duck/Desktop/财务账单/mac魅可官方旗舰店/201811_2088521574554923/20885215745549230156_201811_DETAILS.csv"
    file_code = detectCode(filepath)
    if 'GB' in file_code:
        file_code = 'gbk'

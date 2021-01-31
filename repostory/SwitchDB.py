import Config as conf
import Dev_Setting as dev_conf

def switch_db_env():
    if conf.DB_ENV == 'UCO':
        host = dev_conf.UCO_HOST
        port = dev_conf.UCO_PORT
        user = dev_conf.USERNAME
        db = dev_conf.DATABASE
        passwd = dev_conf.PASSWORD
    elif conf.DB_ENV == 'YY':
        host = dev_conf.YY_HOST
        port = dev_conf.YY_PORT
        user = dev_conf.USERNAME
        db = dev_conf.DATABASE
        passwd = dev_conf.PASSWORD
    elif conf.DB_ENV == 'EL':
        host = dev_conf.EL_HOST
        port = dev_conf.EL_PORT
        user = dev_conf.USERNAME
        db = dev_conf.DATABASE
        passwd = dev_conf.PASSWORD
    elif conf.DB_ENV == 'EL':
        host = dev_conf.ELC_HOST
        port = dev_conf.ELC_PORT
        user = dev_conf.USERNAME
        db = dev_conf.DATABASE
        passwd = dev_conf.PASSWORD
    else:
        host = dev_conf.LOCAL_HOST
        port = dev_conf.LOCAL_PORT
        user = dev_conf.LOCAL_USERNAME
        db = dev_conf.DATABASE
        passwd = dev_conf.LOCAL_PASSWORD

    return host,port,user,db,passwd


from PasswordManager.PASSWORDS import PASSWORDS

class Manager:
    def __init__(self):
        systems = [system for system in PASSWORDS.keys()]
        self.system = input(str(systems) + "\n系统：")
        try:
            envs = [env for env in PASSWORDS[self.system].keys()]
            self.env = input('\n' + str(envs) + "\n环境：")
        except:
            print('\n输入的系统不存在，请再次输入~')
            self.__init__()

    '''删除环境'''
    def delete(self):
        try:
            del PASSWORDS[self.system][self.env]
            print('删除成功！')
        except:
            print('删除失败')

    '''修改'''
    def update(self, new_password):
        try:
            PASSWORDS[self.system][self.env] = new_password
            print('\n修改成功！')
        except:
            print('\n修改失败，请重试！')
            self.update(new_password)

    '''查询'''
    def query(self):
        return '\n' + str(PASSWORDS[self.system][self.env])


if __name__ == '__main__':
    if_continue = 'yes' #是否退出

    while if_continue == 'yes':
        manager = Manager()
        actions = ['1:查询', '2:修改', '3:删除']
        action = input('\n' + str(actions) + '\n请输入需要进行的操作:')

        if action == '1':
            print(manager.query())
        elif action == '2':
            new_password = input('\n请输入需要更新的密码：')
            manager.update(new_password)
        elif action == '3':
            manager.delete()
        else:
            print('\n' + '操作无效')

        del manager

        if_continue = input('\n' + '是否继续？(yes/no)')

    print('Bye~')
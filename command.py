

from fabric import Connection
from fabric.transfer import Transfer
from pathlib import Path
from getpass import getpass
import shutil
import tempfile


class Command():
    """
    コマンド解析・構築・実行クラス
    """
    
    def __init__(self, name, data):
        """
        Command クラス コンストラクタ
        """
        self.__command_pool = []  # 構築したコマンドプールの保存
        self.__target_list = []   # ターゲットの一覧
        self.__worker_dir = tempfile.TemporaryDirectory() # 作業用一時ディレクトリ
        self.name = name
        self.data = data
        self.generate_command_pool()


    def run(self):
        """
        構築したコマンドの実行
        """

        result = []

        # コマンドプールが空だった場合
        # 空の配列を返す
        if len(self.__command_pool) <= 0:
            return result

        # 構築したコマンドの実行
        for pool in self.__command_pool:
            if "target" in pool["type"]:
                command = pool["run"]
                arg = pool["command"]
                # command が存在すれば実行する
                if arg != None:
                    result.append(command(arg))

            elif "proxy" in pool["type"]:
                pass

            elif "file" in pool["type"]:
                command = pool["run"]
                local_file = pool["local"]
                remote_file = pool["remote"]
                result.append(command(local_file, remote_file))

        # 各コマンドの実行結果を返す
        return result

    
    def rollback(self):
        """
        構築した rollback コマンドの実行
        """

        result = []

        # コマンドプールが空だった場合
        # 空の配列を返す
        if len(self.__command_pool) <= 0:
            return result

        # 構築したコマンドの実行
        for pool in self.__command_pool:
            if "target" in pool["type"]:
                command = pool["run"]
                arg = pool["rollback"]
                # rollback が存在すれば実行する
                if arg != None:
                    result.append(command(arg))

        # 各コマンドの実行結果を返す
        return result


    def generate_command_pool(self):
        """
        コマンドプールの構築
        """
        # プロキシの設定
        self.__generate_proxy_command()
        # ターゲットの一覧化
        self.__generate_target_list()
        # ファイルの転送準備
        self.__generate_file_command()
        # ターゲットコマンドの構築
        self.__generate_target_command()


    def __generate_file_command(self):
        """
        file キーワードの解釈・コマンドのジェネレーター
        """
        
        # file キーワードがなかった場合
        # またはターゲットリストが空だった場合
        # 何もせずに終了する
        if (not "file" in self.data) or len(self.__target_list) <= 0:
            return

        files = self.data["file"]

        # ファイル転送コマンドを構築する
        for send_file in files:
            dir_flag = False
            local_path = send_file["path"]
            remote_path = send_file["to"]

            # ディレクトリが指定された場合、プログラムで圧縮しファイルにする
            if Path(local_path).is_dir():
                dir_flag = True
                output = Path(self.__worker_dir.name).joinpath(Path(local_path).parts[-1])
                root_dir = Path(local_path).joinpath("..")
                base_dir = Path(local_path).parts[-1]
                local_path = shutil.make_archive(output,
                                                 "tar",
                                                 root_dir=root_dir,
                                                 base_dir=base_dir
                                                )

            # 送信先のパスがファイルでなかった場合、末尾に送信ファイル名を追加する
            # fabric のファイル送信の仕様
            if Path(remote_path).parts[-1] != Path(local_path).parts[-1]:
                remote_path = str(Path(remote_path) / Path(local_path).parts[-1])

            # ターゲットリストの一覧全てに転送する
            for target in self.__target_list:
                connect = Transfer(target["target"])

                # コマンドの構築
                pool = {
                    "type": "file",
                    "run": connect.put,
                    "local": local_path,
                    "remote": remote_path
                }

                # コマンドプールへの積み込み
                self.__command_pool.append(pool)

                # ディレクトリが指定された場合、送信先で解凍する
                if dir_flag == True:
                    connect = target["target"]
                    remote_dir = Path(remote_path).parent
                    remote_file = Path(remote_path).parts[-1]
                    command = "cd {} && tar -xf {} && rm -rf {}".format(
                        remote_dir, remote_file, remote_file)

                    # コマンドの構築
                    pool = {
                        "type": "target",
                        "run": connect.run,
                        "command": command,
                        "rollback": None
                    }

                    # コマンドプールへの積み込み
                    self.__command_pool.append(pool)


    def __generate_proxy_command(self):
        """
        proxy キーワードの解釈・コマンドのジェネレーター
        """
        
        # proxy キーワードがなかった場合
        # 何もせずに終了する
        if not "proxy" in self.data:
            return

        gateway = None
        proxies = self.data["proxy"]

        # プロキシのチェーンを作成する
        for proxy in proxies:
            host = proxy["host"]
            port = "22"
            if "port" in proxy:
                port = proxy["port"]
            user = None
            if "user" in proxy:
                user = proxy["user"]
            else:
                user = input("LOGIN USER {}: ".format(host))
            password = None
            if "password" in proxy:
                password = proxy["password"]
            else:
                password = getpass("LOGIN PASSWORD {}@{}: ".format(user, host))

            gateway = Connection(host=host,
                                 port=port,
                                 user=user,
                                 connect_kwargs={"password": password},
                                 gateway=gateway
                                )

        # コマンドの構築
        pool = {
            "type": "proxy",
            "gateway": gateway
        }

        # コマンドプールに積み込み
        self.__command_pool.append(pool)


    def __generate_target_list(self):
        """
        target キーワードの解釈・ターゲットの一覧化
        """
        
        # target キーワードがなかった場合
        # 何もせずに終了する
        if not "target" in self.data:
            return

        targets = self.data["target"]

        gateway = None
        # プロキシの設定
        for pool in self.__command_pool:
            if "proxy" in pool["type"]:
                gateway = pool["gateway"]
                break

        # ターゲットの接続情報・コマンド情報を一覧化する
        for target in targets:
            host = target["host"]
            port = "22"
            if "port" in target:
                port = target["port"]
            user = None
            if "user" in target:
                user = target["user"]
            else:
                user = input("LOGIN USER {}: ".format(host))
            password = None
            if "password" in target:
                password = target["password"]
            else:
                password = getpass("LOGIN PASSWORD {}@{}: ".format(user, host))
            command = None
            if "command" in target:
                command = " && ".join(target["command"])
            rollback = None
            if "rollback" in target:
                rollback = " && ".join(target["rollback"])

            conn = Connection(host=host,
                              port=port,
                              user=user,
                              connect_kwargs={"password": password},
                              gateway=gateway
                            )

            # ターゲット情報の構築
            data = {
                "target": conn,
                "command": command,
                "rollback": rollback
            }

            # ターゲットリストに追加
            self.__target_list.append(data)


    def __generate_target_command(self):
        """
        target キーワードの解釈・コマンドのジェネレーター
        """
        
        # ターゲットリストが空だった場合
        # 何もせずに終了する
        if len(self.__target_list) <= 0:
            return

        # ターゲットことにコマンド・ロールバックコマンドを構築
        for target in self.__target_list:
            connect = target["target"]
            command = target["command"]
            rollback = target["rollback"]

            # コマンドの構築
            pool = {
                "type": "target",
                "run": connect.run,
                "command": command,
                "rollback": rollback,
            }

            # コマンドプールに積み込み
            self.__command_pool.append(pool)


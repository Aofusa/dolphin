

import fabric
from fabric import Connection
from fabric.transfer import Transfer
from git import Repo
from pathlib import Path
from getpass import getpass
from concurrent.futures import ThreadPoolExecutor
import paramiko
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
        self.__command_result = [] # コマンドプールの実行結果
        self.__target_list = []   # ターゲットの一覧
        self.__worker_dir = tempfile.TemporaryDirectory() # 作業用一時ディレクトリ
        self.name = name
        self.data = data
        self.generate_command_pool()


    def get_result(self):
        """
        コマンドの実行結果を返します
        """
        return self.__command_result


    def run(self):
        """
        構築したコマンドの実行
        """

        import invoke

        # コマンドプールが空だった場合
        # 空の配列を返す
        if len(self.__command_pool) <= 0:
            return []

        # 構築したコマンドの実行
        for pool in self.__command_pool:
            try:
                if "target" in pool["type"]:
                    command = pool["run"]
                    arg = pool["command"]
                    # command が存在すれば実行する
                    if arg != None:
                        host = pool["target"]
                        result = command(arg, pty=True)
                        self.__command_result.append({host: result})

                elif "proxy" in pool["type"]:
                    pass

                elif "file" in pool["type"]:
                    command = pool["run"]
                    local_file = pool["local"]
                    remote_file = pool["remote"]
                    host = pool["target"]
                    result = command(local_file, remote_file)
                    self.__command_result.append({host: result})
            except invoke.exceptions.UnexpectedExit as e:
                self.__command_result.append({pool["target"]: e})
                raise e

        # 各コマンドの実行結果を返す
        return self.__command_result


    def __parallel_command_runner(self, command_result, command_pool):
        """
        コマンドを逐次実行するためのコマンドランナー
        """

        for pool in command_pool:
            if "target" in pool["type"]:
                command = pool["run"]
                arg = pool["command"]
                # command が存在すれば実行する
                if arg != None:
                    command_result.append(command(arg, pty=True))

            elif "file" in pool["type"]:
                command = pool["run"]
                local_file = pool["local"]
                remote_file = pool["remote"]
                command_result.append(command(local_file, remote_file))


    def parallel_run(self):
        """
        構築したコマンドの並列実行
        """

        # コマンドプールが空だった場合
        # 空の配列を返す
        if len(self.__command_pool) <= 0:
            return []

        # ターゲットリストの数だけキューを作成する
        parallel_queue = {}
        for target in self.__target_list:
            host = target["target"].host
            parallel_queue[host] = {
                "command_pool": [],
                "result": [],
                "error": None
            }

        # 構築したコマンドをキューに入れていく
        for pool in self.__command_pool:
            if "target" in pool["type"] or "file" in pool["type"]:
                t = pool["target"]
                parallel_queue[t]["command_pool"].append(pool)

        # コマンドプールのターゲット別並列実行
        with ThreadPoolExecutor(max_workers=None) as executor:
            future_runner = {}
            for host, queue in parallel_queue.items():
                exc = executor.submit(
                        self.__parallel_command_runner,
                        queue["result"],
                        queue["command_pool"]
                    )
                future_runner[host] = exc
            for k, v in future_runner.items():
                parallel_queue[k]["error"] = v.exception()

        # 各スレッドの実行結果を集約
        for host, queue in parallel_queue.items():
            if queue["error"] == None:
                for result in queue["result"]:
                    self.__command_result.append({host: result})
            else:
                self.__command_result.append({host: queue["error"]})

        # 各コマンドの実行結果を返す
        return self.__command_result

    
    def failback(self):
        """
         command の実行に失敗したターゲットマシンに対し rollback を実行する
        """

        result = []

        # コマンドの実行結果が空だった場合
        # 空の配列を返す
        if len(self.__command_result) <= 0:
            return result

        failed = []

        # command の実行に失敗したターゲットマシンの列挙
        for res in self.__command_result:
            for k, v in res.items():
                if type(v) != fabric.runners.Result:
                    failed.append(k)
        
        # failed に対し rollback コマンドの実行
        for pool in self.__command_pool:
            if "target" in pool["type"]:
                if pool["target"] in failed:
                    command = pool["run"]
                    arg = pool["rollback"]
                    # rollback が存在すれば実行する
                    if arg != None:
                        host = pool["target"]
                        r = command(arg, pty=True)
                        result.append({host: r})

        # 各コマンドの実行結果を返す
        return result


    def rollback(self):
        """
        構築した rollback コマンドの実行
        """

        # コマンドプールが空だった場合
        # 空の配列を返す
        if len(self.__command_pool) <= 0:
            return []

        # 構築したコマンドの実行
        for pool in self.__command_pool:
            if "target" in pool["type"]:
                command = pool["run"]
                arg = pool["rollback"]
                # rollback が存在すれば実行する
                if arg != None:
                    host = pool["target"]
                    result = command(arg, pty=True)
                    self.__command_result.append({host: result})

        # 各コマンドの実行結果を返す
        return self.__command_result


    def __parallel_rollback_runner(self, command_result, command_pool):
        """
         rollback コマンドを逐次実行するためのコマンドランナー
        """

        for pool in command_pool:
            if "target" in pool["type"]:
                command = pool["run"]
                arg = pool["rollback"]
                # rollback が存在すれば実行する
                if arg != None:
                    command_result.append(command(arg, pty=True))


    def parallel_rollback(self):
        """
        構築した rollback コマンドの実行
        """

        # コマンドプールが空だった場合
        # 空の配列を返す
        if len(self.__command_pool) <= 0:
            return []

        # ターゲットリストの数だけキューを作成する
        parallel_queue = {}
        for target in self.__target_list:
            host = target["target"].host
            parallel_queue[host] = {
                "command_pool": [],
                "result": [],
                "error": None
            }

        # 構築したコマンドをキューに入れていく
        for pool in self.__command_pool:
            if "target" in pool["type"]:
                t = pool["target"]
                parallel_queue[t]["command_pool"].append(pool)

        # コマンドプールのターゲット別並列実行
        with ThreadPoolExecutor(max_workers=None) as executor:
            future_runner = {}
            for host, queue in parallel_queue.items():
                exc = executor.submit(
                        self.__parallel_rollback_runner,
                        queue["result"],
                        queue["command_pool"]
                    )
                future_runner[host] = exc
            for k, v in future_runner.items():
                parallel_queue[k]["error"] = v.exception()

        # 各スレッドの実行結果を集約
        for host, queue in parallel_queue.items():
            if queue["error"] == None:
                for result in queue["result"]:
                    self.__command_result.append({host: result})
            else:
                self.__command_result.append({host: queue["error"]})

        # コマンドプールの実行結果を返す
        return self.__command_result


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
        # リポジトリの転送準備
        self.__generate_repo_command()
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
                local_path_t = Path(local_path).name
                output = Path(self.__worker_dir.name).joinpath(local_path_t)
                root_dir = Path(local_path).joinpath("..")
                base_dir = local_path_t
                local_path = shutil.make_archive(output,
                                                "tar",
                                                root_dir=root_dir,
                                                base_dir=base_dir
                                                )

            # 送信先のパスがファイルでなかった場合、末尾に送信ファイル名を追加する
            # fabric のファイル送信の仕様
            if Path(remote_path).name != Path(local_path).name:
                remote_path = Path(remote_path) / Path(local_path).name
                
            # 送信先のパスを PosixPath に変換する
            remote_path = Path(remote_path).as_posix()

            # ターゲットリストの一覧全てに転送する
            for target in self.__target_list:
                connect = Transfer(target["target"])

                # コマンドの構築
                pool = {
                    "type": "file",
                    "target": target["target"].host,
                    "run": connect.put,
                    "local": local_path,
                    "remote": remote_path
                }

                # コマンドプールへの積み込み
                self.__command_pool.append(pool)

                # ディレクトリが指定された場合、送信先で解凍する
                if dir_flag == True:
                    connect = target["target"]
                    remote_dir = Path(remote_path).parent.as_posix()
                    remote_file = Path(remote_path).name
                    command = "cd {} && tar -xf {} && rm -rf {}".format(
                        remote_dir, remote_file, remote_file)

                    # コマンドの構築
                    pool = {
                        "type": "target",
                        "target": target["target"].host,
                        "run": connect.run,
                        "command": command,
                        "rollback": None
                    }

                    # コマンドプールへの積み込み
                    self.__command_pool.append(pool)


    def __generate_repo_command(self):
        """
        repo キーワードの解釈・コマンドのジェネレーター
        """
        
        # repo キーワードがなかった場合
        # またはターゲットリストが空だった場合
        # 何もせずに終了する
        if (not "repo" in self.data) or len(self.__target_list) <= 0:
            return

        repos = self.data["repo"]

        # リポジトリ転送コマンドを構築する
        for repo in repos:
            # リポジトリのパス
            repo_path = repo["path"]

            # 転送先リモートパス
            remote_path = repo["to"]

            # TODO: Subversion 対応
            # リポジトリのタイプ(Git or Subversion)
            repo_type = None
            with Path(repo_path) as p:
                if ".git" in p.suffix or "git@" in p.parts[0]:
                    repo_type = "git"
                else:
                    repo_type = "svn"
            if "type" in repo:
                repo_type = repo["type"]

            # リポジトリのブランチ
            branch = "master"
            if "branch" in repo:
                repo_branch = repo["branch"]

            # リポジトリのクローン
            # リポジトリ名のディレクトリを一時ディレクトリに作成しそこに clone する
            cloned = Repo.clone_from(repo_path,
                Path(self.__worker_dir.name).joinpath(
                        Path(repo_path).name[:-len(Path(repo_path).suffix)]
                    ),
                branch=branch)
            
            # リポジトリのパスの取得
            local_path = cloned.working_dir

            # プログラムで圧縮しファイルにする
            output = Path(self.__worker_dir.name).joinpath(Path(local_path).name)
            root_dir = Path(local_path).joinpath("..")
            base_dir = Path(local_path).name
            local_path = shutil.make_archive(output,
                                            "tar",
                                            root_dir=root_dir,
                                            base_dir=base_dir
                                            )

            # 送信先のパスがファイルでなかった場合、末尾に送信ファイル名を追加する
            # fabric のファイル送信の仕様
            if Path(remote_path).name != Path(local_path).name:
                remote_path = Path(remote_path) / Path(local_path).name
                
            # 送信先のパスを PosixPath に変換する
            remote_path = Path(remote_path).as_posix()

            # ターゲットリストの一覧全てに転送する
            for target in self.__target_list:
                connect = Transfer(target["target"])

                # コマンドの構築
                pool = {
                    "type": "file",
                    "target": target["target"].host,
                    "run": connect.put,
                    "local": local_path,
                    "remote": remote_path
                }

                # コマンドプールへの積み込み
                self.__command_pool.append(pool)

                # 送信先で解凍する
                connect = target["target"]
                remote_dir = Path(remote_path).parent.as_posix()
                remote_file = Path(remote_path).name
                command = "cd {} && tar -xf {} && rm -rf {}".format(
                    remote_dir, remote_file, remote_file)

                # コマンドの構築
                pool = {
                    "type": "target",
                    "target": target["target"].host,
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
            # ホストアドレス
            host = proxy["host"]

            # ポート番号
            port = "22"
            if "port" in proxy:
                port = proxy["port"]

            # ユーザ名
            user = None
            if "user" in proxy:
                user = proxy["user"]
            else:
                user = input("LOGIN USER {}: ".format(host))

            # ログインパスワード
            # key が指定されている場合は鍵のパスワード
            password = None
            if "password" in proxy:
                password = proxy["password"]
            else:
                msg = "LOGIN PASSWORD {}@{}: "
                if "key" in proxy:
                    msg = "KEY PASSWORD {}@{}: "
                password = getpass(msg.format(user, host))

            # 鍵認証の鍵
            key = None
            if "key" in proxy:
                key = proxy["key"]

            # 接続の認証方式
            connect_kwargs = None
            if "key" in proxy:
                # DSS・RSA・ECDSA・Ed25519 鍵の調査
                key_list = [
                    paramiko.DSSKey.from_private_key_file,
                    paramiko.RSAKey.from_private_key_file,
                    paramiko.ECDSAKey.from_private_key_file,
                    paramiko.Ed25519Key.from_private_key_file
                ]

                pkey = None
                # 上記鍵にマッチするものを使用する
                for k in key_list:
                    try:
                        pkey = k(key, password)
                        break
                    except (paramiko.ssh_exception.SSHException):
                        continue
                
                connect_kwargs = {
                    "pkey": pkey
                }
            else:
                connect_kwargs = {
                    "password": password
                }

            # 接続情報の作成
            gateway = Connection(host=host,
                                 port=port,
                                 user=user,
                                 connect_kwargs=connect_kwargs,
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
            # ホストアドレス
            host = target["host"]

            # ポート番号
            port = "22"
            if "port" in target:
                port = target["port"]

            # ユーザ名
            user = None
            if "user" in target:
                user = target["user"]
            else:
                user = input("LOGIN USER {}: ".format(host))

            # ログインパスワード
            # key が指定されている場合は鍵のパスワード
            password = None
            if "password" in target:
                password = target["password"]
            else:
                msg = "LOGIN PASSWORD {}@{}: "
                if "key" in target:
                    msg = "KEY PASSWORD {}@{}: "
                password = getpass(msg.format(user, host))

            # 鍵認証の鍵
            key = None
            if "key" in target:
                key = target["key"]

            # 実行するコマンド
            command = None
            if "command" in target:
                command = target["command"]

            # rollback 時に実行するコマンド
            rollback = None
            if "rollback" in target:
                rollback = target["rollback"]

            # 接続に使用する認証方式
            connect_kwargs = None
            if "key" in target:
                # DSS・RSA・ECDSA・Ed25519 鍵の調査
                key_list = [
                    paramiko.DSSKey.from_private_key_file,
                    paramiko.RSAKey.from_private_key_file,
                    paramiko.ECDSAKey.from_private_key_file,
                    paramiko.Ed25519Key.from_private_key_file
                ]

                pkey = None
                # 上記鍵にマッチするものを使用する
                for k in key_list:
                    try:
                        pkey = k(key, password)
                        break
                    except (paramiko.ssh_exception.SSHException):
                        continue

                connect_kwargs = {
                    "pkey": pkey
                }

            else:
                connect_kwargs = {
                    "password": password
                }

            # 接続情報の作成
            conn = Connection(host=host,
                              port=port,
                              user=user,
                              connect_kwargs=connect_kwargs,
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

            if command != None:
                # コマンドの構築
                for c in command:
                    pool = {
                        "type": "target",
                        "target": connect.host,
                        "run": connect.run,
                        "command": c,
                        "rollback": None,
                    }

                    # コマンドプールに積み込み
                    self.__command_pool.append(pool)

            if rollback != None:
                # コマンドの構築
                for r in rollback:
                    pool = {
                        "type": "target",
                        "target": connect.host,
                        "run": connect.run,
                        "command": None,
                        "rollback": r,
                    }

                    # コマンドプールに積み込み
                    self.__command_pool.append(pool)


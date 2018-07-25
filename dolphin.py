#! python3


from command import Command


def arg():
    """
    コマンド引数の読み込み
    """
    import argparse

    parser = argparse.ArgumentParser(description="Dolphin - A Deploy-tool")
    parser.add_argument("file", help="dolphin config toml file", nargs="+")
    parser.add_argument("-e", "--env",
                        help="set environment value (key:value)", nargs="+")
    parser.add_argument("-p", "--parallel",
                        help="parallel run (default is sequential)",
                        action="store_true")
    parser.add_argument("--display",
                        help="display result to run command",
                        action="store_true")
    parser.add_argument("--no-enter",
                        help="exit without input Enter key", action="store_true")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--rollback",
                        help="do rollback instead of command", action="store_true")
    group.add_argument("--failback",
                        help="do rollback if missing command", action="store_true")
    args = parser.parse_args()

    return args


def load_toml(files, value):
    """
    TOML ファイルを読み込み dict 形式に変換する
    """
    import toml
    from preprocessor import Preprocessor

    result = {}

    for filepath in files:
        file_data = open(filepath, "r", encoding="utf-8")
        prep_data = Preprocessor(file_data, value).preprocess()
        toml_data = toml.load(prep_data)
        result[filepath] = toml_data

    return result


def command_generate(data):
    """
    コマンドを解析し Command　クラスのオブジェクトを生成する
    """

    result = []

    for name, value in data.items():
        result.append(Command(name, value))

    return result


def command_run(command, args):
    """
    構築したコマンドを実行する
    """

    result = {}

    for c in command:
        if not args.rollback:
            try:
                result[c.name] = c.run()
            except Exception as e:
                print("[{}] \033[31m".format(c.name) + str(e) + "\033[0m")
                result[c.name] = c.get_result()
                if args.failback:
                    print("[{}] failback now...".format(c.name))
                    c.rollback()
        else:
            result[c.name] = c.rollback()

    return result


def command_run_parallel(command, args):
    """
    構築したコマンドを並列実行する
    """

    result = {}

    for c in command:
        if not args.rollback:
            result[c.name] = c.parallel_run()
            if args.failback:
                c.failback()
        else:
            result[c.name] = c.parallel_rollback()

    return result


def display_result(result):
    """
    コマンド実行結果を JSON 形式で表示する
    """

    import json
    import fabric

    data = {}

    # コマンドの実行結果を整形する
    for filename, results in result.items():
        data[filename] = []
        # 各コマンドの実行結果
        for res in results:
            # ホストネームと実行結果
            for k, v in res.items():
                if v == None:
                    continue
                command = None
                status = None
                # 実行結果が成功か失敗か判別する
                if type(v) == fabric.runners.Result:
                    command = v.command
                    status = "Success"
                elif type(v) == fabric.transfer.Result:
                    command = "file transfer {} to {}".format(v.orig_local, v.remote)
                    status = "Success"
                else:
                    command = v.result.command
                    status = "Failed"

                # クエリの作成
                query = {
                    "host": k,
                    "command": command,
                    "status": status
                }

                # クエリを積み込んで行く
                data[filename].append(query)

    # Python dict 形式から JSON 形式に変換する
    data = json.dumps(data, indent=4, separators=(',', ': '))

    # 表示
    print(data)


def main():
    """
    メイン関数
    """

    # 引数の解釈
    args = arg()

    # TOML ファイルのロード
    data = load_toml(args.file, args.env)

    # TOML の情報からコマンドの構築
    command = command_generate(data)

    # 構築したコマンドの実行
    try:
        result = None
        if args.parallel:
            # コマンドの並列実行
            result = command_run_parallel(command, args)
        else:
            # コマンドの逐次実行
            result = command_run(command, args)

        # コマンドの実行結果の表示
        if args.display:
            display_result(result)
    except Exception as e:
        # エラーを赤文字で表示する
        print("\033[31m" + str(e) + "\033[0m")
    finally:
        # すぐ終了するのを防ぐためキー入力待ちにする
        if not args.no_enter:
            input("終了するにはエンターキーを入力してください")


if __name__ == "__main__":
    """
    このファイルが実行された場合に main 関数を実行する
    """
    main()


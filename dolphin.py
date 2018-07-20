#! python3


from command import Command


def arg():
    """
    コマンド引数の読み込み
    """
    import argparse

    parser = argparse.ArgumentParser(description="Dolphin - A Deploy-tool")
    parser.add_argument('file', help="dolphin config toml file", nargs="+")
    parser.add_argument("--no-enter",
                        help="exit without input Enter key", action="store_true")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--rollback",
                        help="do rollback instead of command", action="store_true")
    group.add_argument("--failback",
                        help="do rollback if missing command", action="store_true")
    args = parser.parse_args()

    return args


def load_toml(files):
    """
    TOML ファイルを読み込み dict 形式に変換する
    """
    import toml

    result = {}

    for filepath in files:
        file_data = open(filepath, "r", encoding="utf-8")
        toml_data = toml.load(file_data)
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

    result = []

    for c in command:
        if not args.rollback:
            try:
                result.append(c.run())
            except Exception as e:
                print("[{}] \033[31m".format(c.name) + str(e) + "\033[0m")
                if args.failback:
                    print("[{}] failback now...".format(c.name))
                    c.rollback()
                # else:
                #     raise Exception(e)
        else:
            result.append(c.rollback())

    return result


def main():
    """
    メイン関数
    """

    # 引数の解釈
    args = arg()

    # TOML ファイルのロード
    data = load_toml(args.file)

    # TOML の情報からコマンドの構築
    command = command_generate(data)

    # 構築したコマンドの実行
    try:
        command_run(command, args)
    except Exception as e:
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


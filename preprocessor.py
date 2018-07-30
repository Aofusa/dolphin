

from lark import Lark
from visitor import Visitor


class Preprocessor():
    """
    TOML を拡張しマクロを実装する
    """
    
    def __init__(self, data, value):
        """
        Preprocessor クラス　コンストラクタ
        """

        # ファイルを文字列として取り込みコメントを取り除く
        self.__pre_data = self.__decimating_comment(data.read())
        self.__advanced_data = None    # プリプロセス後の完全な TOML ファイル
        self.__env_map = self.__generate_env_map(value)  # 引数のマップ
        self.__macro_parser = self.__generate_parser()  # マクロの構文パーサー


    def preprocess(self):
        """
        プリプロセッサによるマクロの解釈
        """

        result = None

        # 字句・構文解析
        tree = self.__macro_parser.parse(self.__pre_data)

        # 構文を実行し TOML ファイルを生成する
        result = Visitor(self.__env_map).visit(tree)

        # TOML ファイルを返す
        return result


    def __decimating_comment(self, data):
        """
        読み込んだファイルからコメントを削除する
        """

        result = []

        # 各行ごとにコメントを削除
        for line in data.splitlines():
            if "#" in line:
                line = line[:line.find("#")]
            result.append(line)

        # 結合
        return "\n".join(result)


    def __generate_env_map(self, value):
        """
        引数マップの作成
        """

        # 引数で変数が渡されていなかった場合、Noneを返す
        if value == None:
            return None

        result = None

        # 引数で渡された変数を変数名と値に分割する
        li = ":".join(value).split(":")

        # 変数名をキー、値をバリューとした dict を作成
        result = dict(zip(li[0::2], li[1::2]))

        return result


    def __generate_parser(self):
        """
        マクロ構文の定義
        """

        rule = r"""
            ?start: symbol*

            ?symbol: toml_table
                    | toml_value
                    | operation
                    | assignment
                    | value
                    | var
                    | env
                    | fact
                    | comment
                    | array_inner

            toml_table: "[[" value "]]"

            toml_value: fact "=" (value|array)

            array: "[" ((operation|value) ","?)* "]"
            array_inner: value ","

            ?operation: loop
                        | end

            loop: "%for" new_var "in" iterator ":" symbol* end
            iterator: fact
                    | var

            end: "%end"

            ?assignment: assignment_value
                        | array_assignment_value
                        | array_assignment_array

            assignment_value: new_var "=" (value|array)
            array_assignment_value: new_var_array "=" value
            array_assignment_array: new_var_array "=" array

            ?value: fact
                    | env
                    | var

            new_var: "@" fact
                    | "@" "{" fact "}"

            new_var_array: "@" fact "[" fact "]"
                            | "@" "{" fact "}" "[" fact "]"

            ?var: var_value
                    | var_array

            var_value: "@" fact
                    | "@" "{" fact "}"

            var_array: "@" fact "[" fact "]"
                    | "@" "{" fact "}" "[" fact "]"

            env: "%" fact
                | "%" "{" fact "}"

            fact: STRING
                    | WORD
                    | "'" WORD "'"
                    | NUMBER

            comment: "#"+ symbol*

            %import common.ESCAPED_STRING   -> STRING
            %import common.SIGNED_NUMBER    -> NUMBER
            %import common.WORD
            %import common.WS
            %ignore WS
        """

        parser = Lark(rule, start="start")

        return parser


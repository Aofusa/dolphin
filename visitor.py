

class Visitor():
    """
    独自拡張した TOML を通常の TOML に変換する
    """

    def __init__(self, env=None):
        """
        Visitor クラスコンストラクタ
        """
        self.__env = env


    def __default__(self, tree, env):
        """
        未定義の構文が来た場合エラーを発生させる
        """
        raise AttributeError(tree, env)

    
    def visit(self, tree, env = dict()):
        """
        構文木を辿りキーワード毎に処理を振り分ける
        """
        f = getattr(self, tree.data, self.__default__)
        return f(tree, env)


    def start(self, tree, env):
        """
        構文解析の開始地点
        """
        result = []
        for sub_tree in tree.children:
            data = self.visit(sub_tree, env)
            if data != None:
                result.append(data)
        return "".join(result)


    def toml_table(self, tree, env):
        """
        TOML テーブル構文
        """
        return "\n[[" + self.visit(tree.children[0], env) + "]]\n"


    def toml_value(self, tree, env):
        """
        TOML 変数構文
        """
        left = self.visit(tree.children[0], env)
        right = self.visit(tree.children[1], env)
        return left + "=" + str(right) + "\n"


    def toml_array(self, tree, env):
        """
        TOML 配列構文
        """
        left = self.visit(tree.children[0], env)
        data = left + "=["
        for index in range(1, len(tree.children)):
            data = data +str(self.visit(tree.children[index], env)) + ","
        return data + "]\n"


    def loop(self, tree, env):
        """
        繰り返し構文
        """
        pass


    def end(self, tree, env):
        """
        オペレーションの終了
        """
        pass


    def assignment_value(self, tree, env):
        """
        変数に代入
        """
        key = self.visit(tree.children[0], env)
        value = self.visit(tree.children[1], env)
        env[key] = value
        return


    def assignment_array(self, tree, env):
        """
        変数に配列を代入
        """
        key = self.visit(tree.children[0], env)
        value = []
        for index in range(1, len(tree.children)):
            value.append(self.visit(tree.children[index], env))
        env[key] = value
        return


    def array_assignment_value(self, tree, env):
        """
        配列の要素に再代入
        """
        (key, index) = self.visit(tree.children[0], env)
        value = self.visit(tree.children[1], env)
        env[key][index] = value
        return


    def array_assignment_array(self, tree, env):
        """
        配列の要素に配列を再代入
        """
        (key, index) = self.visit(tree.children[0], env)
        value = []
        for index in range(1, len(tree.children)):
            value.append(self.visit(tree.children[index], env))
        env[key][index] = value
        return


    def new_var(self, tree, env):
        """
        変数定義
        """
        return self.visit(tree.children[0], env)


    def new_var_array(self, tree, env):
        """
        配列の要素の定義
        """
        name = self.visit(tree.children[0], env)
        index = self.visit(tree.children[1], env)
        return (name, int(index))


    def var_value(self, tree, env):
        """
        変数の呼び出し
        """
        return env[self.visit(tree.children[0], env)]


    def var_array(self, tree, env):
        """
        配列の要素の呼び出し
        """
        return env[self.visit(tree.children[0], env)][int(self.visit(tree.children[1], env))]


    def env(self, tree, env):
        """
        引数で渡された値
        """
        return "\"" + self.__env[self.visit(tree.children[0], env)] + "\""


    def fact(self, tree, env):
        """
        ただの数値・文字列
        """
        return tree.children[0].value


    def comment(self, tree, env):
        """
        # から始まるコメントアウト
        """
        return tree.children[0].value + "\n"


Dolphin - A Deploymet-tool
---


ファイルの転送・コマンドの実行・踏み台の経由  
ただそれだけのデプロイツール  
設定は TOML ファイルを作成する  
書き方は sample.toml を参照  


# 環境構築
```sh
# Python3
pip install -r requirements.txt
```


# 実行
```sh
python dolphin playbook.toml [.. playbooks.toml] [--no-enter] [--rollback | --failback]
```


## オプションの説明
--no-enter: プログラム実行後のキー入力待ちを無効化する  
--rollback: TOML に記述された command の代わりに rollback を実行する  
--failback: command の実行に失敗した場合、その地点から rollback を実行する  


# TOML ファイルの書き方
- file  
[[file]]で記述  
SFTP によるファイル転送を行います  
※ 今はファイルだけ。ディレクトリは事前に zip や tar に固めてネ  
path: ローカルのファイルパス  
to: リモートのファイルパス  


- proxy  
[[proxy]]で記述  
SSH で経由する踏み台サーバを指定します  
複数指定した場合、上から順番に多段 SSH を実施します  
host: アドレス  
port: SSH ポート
user: ログインユーザ  ※省略した場合入力プロンプトが開きます  
password: ログインパスワード  ※省略した場合入力プロンプトが開きます  


- target  
[[target]]で記述  
デプロイ先のターゲットマシンを指定します  
複数指定した場合、全てに対し file で指定されたファイルの転送、
 proxy で指定した踏み台を経由して接続します  
host: アドレス
port: SSH ポート
user: ログインユーザ  ※省略した場合入力プロンプトが開きます  
password: ログインパスワード  ※省略した場合入力プロンプトが開きます  
command: ターゲットマシン上で実行するコマンド。[]で囲み配列形式で指定します。  
rollback: ターゲットマシン上で実行するコマンド。[]で囲み配列形式で指定します。
実行時に --rollback オプションが指定された場合、 command の代わりに実行されます。
また、 --failback オプションが指定された状態で、 command の実行途中に実行時エラーが
生じた場合、失敗地点から rollback で指定されたコマンドを実行します。  


## 書き方サンプル
ファイル転送  
```toml
[[file]]
path = "path/to/file"
to   = "/path/to/destination"
```

複数書くこともできる  
その場合、全てのファイルがターゲットマシンに転送される  
```toml
[[file]]
path = "path/to/file"
to   = "/path/to/destination"

[[file]]
path = "path/to/other_file"
to   = "/path/to/other_destination"
```

プロキシの指定  
```toml
[[proxy]]
host = "192.168.1.10"
port = "22"
user = "user"
password = "password"
```

複数指定することもできる  
その場合、上から順番に経由していく  
```toml
[[proxy]]
host = "192.168.1.10"
port = "22"
user = "user"
password = "password"

# コメントを書くこともできる
# user・password を指定しなかった場合、入力プロンプトが表示される
# また、 port を省略した場合 22 ポートがデフォルトで使用される
[[proxy]]
host = "172.23.1.10"
```

デプロイ先ターゲットマシンの指定  
```toml
[[target]]
host = "10.1.1.10"
port = "22"
user = "user"
password = "password"
# command・rollback は複数書くことができ、上から順番に処理される
command = [
    "hostname",
    "uname -a"
]
rollback = [
    "who",
    "w",
]
```

複数指定することができる  
その場合、全てのマシンに対して処理がされる  
```toml
[[target]]
host = "10.1.1.10"
port = "22"
user = "user"
password = "password"
command = [
    "hostname",
    "uname -a"
]
rollback = [
    "who"
]

# user・password を省略すると入力プロンプトが表示される
# また、port を省略した場合 22 番ポートがデフォルトで使用される
# command・rollback を省略した場合は何もしない
# (ファイルの転送のみを行うことができる)
[[target]]
host = "10.1.1.20"
```


# 悲しいこと
- ディレクトリは送信できない。zip や tar などでファイルに固めてネ  
- 対話的な処理はできない。Yes or No で聞かれるとエラーになるので yes コマンドなんかで対処してネ  
- SSH のログイン方式はパスワード方式しかサポートしていない  



Dolphin - A Deployment-tool
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


# ビルド
```sh
# dist 配下を配布する
pyinstaller --onefile dolphin.py
```


# 実行
```sh
python dolphin playbook.toml [.. playbooks.toml] [--no-enter] [--parallel] [--rollback | --failback]
```


## オプションの説明
--no-enter: プログラム実行後のキー入力待ちを無効化する  
--parallel: 各 target へのコマンド発行を並列化する  
--rollback: TOML に記述された command の代わりに rollback を実行する  
--failback: command の実行に失敗した場合、その地点から rollback を実行する  


# TOML ファイルの書き方
- file  
[[file]]で記述  
SFTP によるファイル転送を行います  
ディレクトリの場合 tar に圧縮して転送するため、転送先に tar コマンドがない場合転送に失敗します  
path: ローカルのファイルパス  
to: リモートのファイルパス  


- repo  
[[repo]]で記述  
Git リポジトリをダウンロードし SFTP によるファイル転送を行います。  
 tar に圧縮して転送するため、転送先に tar コマンドがない場合転送に失敗します  
path: リポジトリのURL ※git@github.com/https://どちらにも対応しています  
to: リモートのファイルパス  
branch: Git リポジトリのブランチ ※省略した場合 master になります。


- proxy  
[[proxy]]で記述  
SSH で経由する踏み台サーバを指定します  
複数指定した場合、上から順番に多段 SSH を実施します  
host: アドレス  
port: SSH ポート  ※省略した場合 22 番ポートが使用されます  
user: ログインユーザ  ※省略した場合入力プロンプトが開きます  
key: 鍵認証に使用する鍵。  ※省略された場合パスワード認証方式になります。  
password: ログイン or 鍵のパスワード  ※省略した場合入力プロンプトが開きます  


- target  
[[target]]で記述  
デプロイ先のターゲットマシンを指定します  
複数指定した場合、全てに対し file で指定されたファイルの転送、
 proxy で指定した踏み台を経由して接続します  
host: アドレス  
port: SSH ポート  ※省略した場合 22 番ポートが使用されます  
user: ログインユーザ  ※省略した場合入力プロンプトが開きます  
key: 鍵認証に使用する鍵。  ※省略された場合パスワード認証方式になります。  
password: ログイン or 鍵のパスワード  ※省略した場合入力プロンプトが開きます  
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

リポジトリの指定
```toml
[[repo]]
path = "git@github.com:your/repository.git"
to   = "/path/to/destination"
branch = "master"
```

複数書くこともできる  
その場合、全てのリポジトリがターゲットマシンにクローンされる  
```toml
[[repo]]
path = "git@github.com:your/repository.git"
to   = "/path/to/destination"
branch = "master"

# branch を省略した場合は master ブランチを使用します
[[repo]]
path = "https://github.com/your/repository.git"
to   = "/path/to/destination"
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
# 公開鍵認証方式で使用する鍵
# password を省略した場合鍵のパスワードが実行中に聞かれる
key  = "/path/to/.ssh/keyfile"

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
# sudo コマンドも実行できる
command = [
    "hostname",
    "sudo uname -a"
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
key  = "/path/to/.ssh/keyfile"  # 公開鍵認証方式で使う鍵
password = "password"           # 公開鍵認証で使う鍵が指定されている場合は鍵のパスワード
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
- ディレクトリを転送する場合、ターゲットマシン上で tar コマンドが使用できないと失敗する  
- SSH のログイン方式はパスワード認証と公開鍵認証(RSA・DSS・ECDSA・Ed25519)をサポート  
- ファイル転送する場合強制的に上書きされるため、 /tmp 配下など安全な場所に転送することを推奨  



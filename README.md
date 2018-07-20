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
python dolphin playbook.toml [--no-enter] [.. playbooks.toml]
```


# Всезнамус (Allknower)

Мультимодальный поисковый сервис, разрабатываемый командой студентов на курсе "Информационный поиск" факультета МКН СПбГУ

# Установка

1. Создаём окружение и ставим зависимости

```bash
conda create -n allknower python=3.12.5 -y
conda activate allknower
pip install --no-cache-dir -r requirements/requirements.txt
```

2. Включаем `pre-commit` чеки (что это такое можно посмотреть [здесь](https://pre-commit.com/))

```bash
pre-commit install
```

3. Создаём файл `.git/hooks/prepare-commit-msg` и копируем в него следующее:

```
#!/bin/bash

MESSAGE=$(cat $1) 
COMMITFORMAT="^(build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test): .*$"

if ! [[ "$MESSAGE" =~ $COMMITFORMAT ]]; then
  echo "Your commit was rejected due to the commit message. Skipping..." 
  echo ""
  echo "Please use the following format:"
  echo "feat: feature example comment"
  echo "fix(ui): bugfix example comment"
  echo ""
  echo "More details on https://www.conventionalcommits.org/en/v1.0.0/"
  exit 1
fi
```

4. Создаём файл `.git/hooks/pre-push` и копируем в него следующее:

```
#!/bin/bash

BRANCH_NAME=$(git rev-parse --abbrev-ref HEAD)

# Define the pattern: feature/AK[sprint_number]-[ticket-number-within-sprint]{/developer-nickname-in-GitHub]} -- last part in curly brackets is optional and can be omitted
PATTERN="^feature\/AK[1-9][0-9]*-[1-9][0-9]*(\/[a-zA-Z0-9-]+)?$"

if [[ ! $BRANCH_NAME =~ $PATTERN ]]; then
  echo "Error: branch name '$BRANCH_NAME' does not match the naming convention."
  echo "Please use the PATTERN: feature/AK[sprint_number]-[ticket-number-within-sprint]{/developer-nickname-in-GitHub]} -- last part in curly brackets is optional and can be omitted"
  exit 1
fi

exit 0
```

5. Даём право на исполнение созданным файлам:

```bash
chmod +x .git/hooks/pre-push
chmod +x .git/hooks/prepare-commit-msg
```

# Конвенция о названии веток

Векти следует называть в формате `feature/AKX-Y` или `feature/AKX-Y/Z`, где

- X -- номер текущего спринта (см. текущий спринт в Notion)
- Y -- номер тикета в рамках этого спринта. Он всегда будет появляться как свойство страницы в Kanban-борде
- Z -- Ваш ник на GitHub, если работа над веткой ведётся одновременно несколькими людьми. В этом случае стоит сначала сделать основную ветку `feature/AKX-Y`, затем счекаутиться от неё со своей веткой

Пример названии ветки: `feature/AK4-5` -- то есть ветка соответствует 5-му тикету в 4-ом спринте проекта `Allknower`.

# Конвенция о разрешённых сообщениях в коммите

Придерживаемся упрощённой структуры сообщений [отсюда](https://www.conventionalcommits.org/en/v1.0.0/):

```
"^(build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test): .*$"
```

То есть тип изменения (про типы можно прочитать [тут](https://github.com/angular/angular/blob/22b96b9/CONTRIBUTING.md#type)), после двоеточие, пробел и собственно сообщение, про что коммит.

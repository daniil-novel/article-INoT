# article-INoT

Репозиторий статьи о мега-агентной архитектуре с внутренней ролевой сегрегацией на основе Introspection of Thought (INoT).

В репозитории поддерживаются две рабочие версии статьи:

- `converted_article_springer.tex` — английская версия
- `converted_article_springer_ru.tex` — русская версия

## Состав репозитория

- `converted_article_springer.tex` — основной английский исходник статьи
- `converted_article_springer_ru.tex` — основной русский исходник статьи
- `sn-jnl.cls` — класс Springer Nature Journal
- `.vscode/settings.json` — локальные настройки LaTeX Workshop для сборки через MiKTeX
- `.gitignore` — исключения для артефактов сборки и локального шума
- `CHANGELOG.md` — журнал изменений проекта

## Принципы ведения статьи

- Английская и русская версии хранятся отдельно и поддерживаются в актуальном состоянии одновременно.
- В Git коммитятся только исходники и действительно нужные служебные файлы.
- Артефакты LaTeX-сборки в репозиторий не добавляются.
- Сгенерированные PDF используются локально для проверки, но не хранятся в Git.

## Сборка

Проект настроен под `LaTeX Workshop` и `MiKTeX`.

### В VS Code

1. Откройте нужный файл `.tex`.
2. Сохраните файл.
3. Запустите `LaTeX Workshop: Build LaTeX project`.
4. Откройте `LaTeX Workshop: View LaTeX PDF file`.

### Из терминала

Для английской версии:

```powershell
latexmk -synctex=1 -interaction=nonstopmode -file-line-error -pdf converted_article_springer.tex
```

Для русской версии:

```powershell
latexmk -synctex=1 -interaction=nonstopmode -file-line-error -pdf converted_article_springer_ru.tex
```

## Важные замечания

- Если в статье появятся реальные рисунки, их нужно добавлять в репозиторий отдельно.
- Пока файлов `figure1.png` ... `figure7.png` нет, в документе используются встроенные заглушки.
- Если меняется структура статьи, желательно в том же коммите обновлять обе языковые версии.

## Рекомендуемый Git workflow

```powershell
git status
git add .
git commit -m "Short meaningful message"
git push
```

## Лицензирование и шаблон

Класс `sn-jnl.cls` относится к шаблону Springer Nature и используется здесь как техническая основа для подготовки статьи.

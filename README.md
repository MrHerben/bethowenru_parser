# Парсер bethowen.ru

(Тестовое задание PromoData)

## Установка

```pip install -r requirements.txt```

## Настройка

В config.json можно настраивать количество одновременных потоков, город, адрес, категории через запятую, прокси для ускорения путём обхода ограничений запросов с одного iP (для использования без прокси можно указать localhost) и само собой путь к chromedriver

```json
{
    "max_connection": 1,
    "city": "Санкт-Петербург",
    "address_tt": "Заневский пр-т., д 67к2",
    "categories": "dogs,cats,vetapteka,birds,akvariumistika,rodents,dlya-vladeltsev",
    "proxies": ["localhost"],
    "chromedriver_path": "E:\\Chrome-bin\\131.0.6778.205\\chromedriver.exe"
}
```

## Запуск

По окончанию установки и настройки просто запустите main.py

## Логика

Сначала скрипт инициирует все нужные для функционирования данные, а после запускает в соответствии с указанным max_connection браузеры, потому как иначе собрать oid невозможно из-за ограничений сайта на подобные запросы и парсит oid всех товаров со всех указанных категорий. После получения всех oid браузеры закрываются, так как на этом ограничения заканчиваются и можно получать всю нужную нам информацию (код, имя, цена обычная, цена со скидкой, количество и наличие) через их API. По окончанию парсинга в папке будет лежать таблица с результатами парсинга results.csv

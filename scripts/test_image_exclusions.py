#!/usr/bin/env python3
"""
Тест функции _apply_image_exclusions для демонстрации работы
"""


def test_image_exclusions():
    """Демонстрация работы исключения изображений"""

    # Исходные данные - список изображений (10 штук)
    original_images = [
        "image_001.jpg",
        "image_002.jpg",
        "image_003.jpg",
        "image_004.jpg",
        "image_005.jpg",
        "image_006.jpg",
        "image_007.jpg",
        "image_008.jpg",
        "image_009.jpg",
        "image_010.jpg",
    ]

    # Правила исключений как в вашем примере
    exclusion_rules = {
        "Autohaus Sedlmaier GmbH & Co. KG": {
            "start": "1",
            "penultimate": "*",
            "last": "*",
        },
        "Autohaus Schmidt & Söhne Aschersleben GmbH & Co. KG": {
            "start": "1",
            "penultimate": "",
            "last": "",
        },
    }

    print("=== ТЕСТ ИСКЛЮЧЕНИЯ ИЗОБРАЖЕНИЙ ===\n")
    print(f"Исходные изображения ({len(original_images)} штук):")
    for i, img in enumerate(original_images, 1):
        print(f"  {i:2d}. {img}")
    print()

    # Тестируем для каждого дилера
    for dealer, rules in exclusion_rules.items():
        print(f"🏪 ДИЛЕР: {dealer}")
        print(f"📋 ПРАВИЛА: {rules}")

        # Эмулируем логику из _apply_image_exclusions
        result = original_images.copy()
        removed_images = []

        print(f"\n📸 Начальные изображения: {len(result)} штук")

        # Шаг 1: Удаляем последнюю фотку если указана звездочка
        last = rules.get("last", "")
        if last == "*" and len(result) >= 1:
            removed_image = result.pop(-1)
            removed_images.append(f"последняя (позиция {len(result) + 1})")
            print(f"  ❌ Удаляем ПОСЛЕДНЮЮ: {removed_image}")
            print(f"     Осталось: {len(result)} изображений")

        # Шаг 2: Удаляем предпоследнюю фотку если указана звездочка
        penultimate = rules.get("penultimate", "")
        if penultimate == "*" and len(result) >= 2:
            removed_image = result.pop(-2)
            removed_images.append(f"предпоследняя (позиция {len(result) + 1})")
            print(f"  ❌ Удаляем ПРЕДПОСЛЕДНЮЮ: {removed_image}")
            print(f"     Осталось: {len(result)} изображений")

        # Шаг 3: Удаляем фотки по позициям из начала
        start_remove = rules.get("start", "")
        if start_remove and start_remove.strip():
            positions_to_remove = []

            # Разбиваем по запятой и преобразуем в числа
            for pos_str in start_remove.split(","):
                pos_str = pos_str.strip()
                if pos_str.isdigit():
                    pos = int(pos_str)
                    if pos > 0:  # Позиции в CSV начинаются с 1
                        index = (
                            pos - 1
                        )  # Преобразуем в индекс массива (начинается с 0)
                        if index < len(result):
                            positions_to_remove.append(index)

            # Сортируем позиции по убыванию, чтобы удалять с конца
            positions_to_remove.sort(reverse=True)

            for index in positions_to_remove:
                if index < len(result):
                    removed_image = result.pop(index)
                    removed_images.append(f"позиция {index + 1}")
                    print(f"  ❌ Удаляем позицию {index + 1}: {removed_image}")
                    print(f"     Осталось: {len(result)} изображений")

        print(f"\n✅ РЕЗУЛЬТАТ для {dealer}:")
        print(f"   Исходно: {len(original_images)} изображений")
        print(
            f"   Удалено: {len(removed_images)} изображений - {', '.join(removed_images)}"
        )
        print(f"   Осталось: {len(result)} изображений")

        if result:
            print(f"   Итоговые изображения:")
            for i, img in enumerate(result, 1):
                print(f"     {i:2d}. {img}")
        else:
            print(f"   ⚠️ НЕТ ИЗОБРАЖЕНИЙ!")

        print("\n" + "=" * 80 + "\n")


def test_multiple_positions():
    """Тест с несколькими позициями в start"""

    original_images = [f"photo_{i:03d}.jpg" for i in range(1, 11)]  # 10 фоток

    print("=== ТЕСТ С НЕСКОЛЬКИМИ ПОЗИЦИЯМИ ===\n")
    print(f"Исходные изображения ({len(original_images)} штук):")
    for i, img in enumerate(original_images, 1):
        print(f"  {i:2d}. {img}")
    print()

    # Тестируем правило с несколькими позициями
    rules = {"start": "1,3,7", "penultimate": "*", "last": "*"}
    print(f"📋 ПРАВИЛА: {rules}")
    print(f"   start: '1,3,7' - удаляем 1-ю, 3-ю и 7-ю фотки")
    print(f"   penultimate: '*' - удаляем предпоследнюю")
    print(f"   last: '*' - удаляем последнюю\n")

    result = original_images.copy()
    removed_images = []

    # Удаляем последнюю
    if len(result) >= 1:
        removed_image = result.pop(-1)
        removed_images.append(f"последняя")
        print(
            f"❌ Удаляем ПОСЛЕДНЮЮ: {removed_image} (было на позиции {len(result) + 1})"
        )

    # Удаляем предпоследнюю
    if len(result) >= 2:
        removed_image = result.pop(-2)
        removed_images.append(f"предпоследняя")
        print(
            f"❌ Удаляем ПРЕДПОСЛЕДНЮЮ: {removed_image} (было на позиции {len(result) + 1})"
        )

    # Удаляем по позициям 1,3,7
    positions_to_remove = [0, 2, 6]  # Индексы для позиций 1,3,7
    positions_to_remove.sort(reverse=True)  # [6, 2, 0]

    for index in positions_to_remove:
        if index < len(result):
            removed_image = result.pop(index)
            removed_images.append(f"позиция {index + 1}")
            print(f"❌ Удаляем позицию {index + 1}: {removed_image}")

    print(f"\n✅ ИТОГОВЫЙ РЕЗУЛЬТАТ:")
    print(f"   Исходно: {len(original_images)} изображений")
    print(f"   Удалено: {len(removed_images)} изображений")
    print(f"   Осталось: {len(result)} изображений")

    if result:
        print(f"   Финальные изображения:")
        for i, img in enumerate(result, 1):
            print(f"     {i:2d}. {img}")


if __name__ == "__main__":
    test_image_exclusions()
    test_multiple_positions()

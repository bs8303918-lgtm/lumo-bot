from services.interest_matcher import build_opportunity_tags

title = "AI'preneurs — акселератор AI-предпринимателей (5-й поток, Алматы)"
description = (
    "Программа Astana Hub и Almaty Hub: от идеи до работающего AI-продукта. "
    "5-й поток впервые в Алматы (Almaty Hub), 14 недель — команды, MVP, выход на рынок. "
    "Конкурсный отбор."
)
requirements = "Основатели стартапов, AI/продуктовые специалисты"

print("without requirements:")
print(build_opportunity_tags(title, title=title, description=description, primary_type="конкурс"))

print("with requirements param:")
print(
    build_opportunity_tags(
        title,
        title=title,
        description=description,
        requirements=requirements,
        primary_type="конкурс",
    )
)

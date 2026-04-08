import os
from django.core.files import File
from services.models import Service

images_mapping = {
    'kolirovka': r'C:\Users\dima_\.gemini\antigravity\brain\1537fd37-25a0-471d-91f6-54510ee2ddfc\service_kolirovka_1775502836493.png',
    'raspil': r'C:\Users\dima_\.gemini\antigravity\brain\1537fd37-25a0-471d-91f6-54510ee2ddfc\service_raspil_1775502852687.png',
    'dostavka': r'C:\Users\dima_\.gemini\antigravity\brain\1537fd37-25a0-471d-91f6-54510ee2ddfc\service_dostavka_1775502869574.png',
    'raschet-materialov': r'C:\Users\dima_\.gemini\antigravity\brain\1537fd37-25a0-471d-91f6-54510ee2ddfc\service_raschet_1775502886641.png'
}

def run():
    print("Прикрепляем сгенерированные изображения к услугам...")
    for slug, image_path in images_mapping.items():
        try:
            service = Service.objects.get(slug=slug)
            if os.path.exists(image_path):
                with open(image_path, 'rb') as f:
                    # Сохраняем файл в модель. 
                    # Имя файла будет построено на основе slug.
                    service.image.save(f'{slug}_premium.png', File(f), save=True)
                print(f"Успешно прикреплено изображение к: {service.title}")
            else:
                print(f"Файл {image_path} не найден!")
        except Exception as e:
            print(f"Ошибка с услугой {slug}: {str(e)}")

if __name__ == '__main__':
    run()

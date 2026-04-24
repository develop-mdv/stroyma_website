import os
from django.core.files import File
from services.models import Service, ServicePhoto

gallery_images = [
    r'C:\Users\dima_\.gemini\antigravity\brain\1537fd37-25a0-471d-91f6-54510ee2ddfc\gallery_kolirovka_1_1775503095019.png',
    r'C:\Users\dima_\.gemini\antigravity\brain\1537fd37-25a0-471d-91f6-54510ee2ddfc\gallery_kolirovka_2_1775503110133.png'
]

def run():
    print("Прикрепляем фотки для галереи Колеровки...")
    try:
        service = Service.objects.get(slug='kolirovka')
        # Удаляем старые, если они есть
        ServicePhoto.objects.filter(service=service).delete()
        
        for i, img_path in enumerate(gallery_images):
            if os.path.exists(img_path):
                with open(img_path, 'rb') as f:
                    photo = ServicePhoto(service=service, title=f"Пример работы {i+1}")
                    photo.image.save(f'gallery_kolirovka_{i+1}.png', File(f), save=True)
                print(f"Добавлено фото в галерею!")
            else:
                print(f"Файл {img_path} не найден!")
    except Exception as e:
        print(f"Ошибка {str(e)}")

if __name__ == '__main__':
    run()

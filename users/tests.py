from django.conf import settings
from django.test import TestCase
from django.contrib.auth import get_user_model
from .serializers import UserSerializer


class UserSerializerTests(TestCase):
    def test_serializer_accepts_residence_and_chapter_fields(self):
        user = get_user_model().objects.create_user(
            username='chapteruser',
            email='chapter@example.com',
            password='StrongPass123!'
        )

        serializer = UserSerializer(user, data={
            'country': 'Nigeria',
            'state_of_residence': 'Lagos',
            'state_of_origin': 'Lagos Chapter',
        }, partial=True)

        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_user = serializer.save()
        self.assertEqual(updated_user.country, 'Nigeria')
        self.assertEqual(updated_user.state_of_residence, 'Lagos')
        self.assertEqual(updated_user.state_of_origin, 'Lagos Chapter')


class CloudinaryStorageTests(TestCase):
    def test_default_storage_uses_cloudinary_when_credentials_are_configured(self):
        self.assertEqual(
            settings.STORAGES['default']['BACKEND'],
            'cloudinary_storage.storage.MediaCloudinaryStorage',
        )

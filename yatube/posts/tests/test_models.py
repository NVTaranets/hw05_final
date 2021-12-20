from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import Group, Post

User = get_user_model()


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост с длинным текстом',
        )

    def test_models_have_correct_object_names(self):
        """Проверяем, что у моделей корректно работает __str__."""
        models = {
            'Post': (str(PostModelTest.post), PostModelTest.post.text[:15]),
            'Group': (str(PostModelTest.group), PostModelTest.group.title)
        }
        for model in models:
            value, expected = models[model]
            with self.subTest(text=model):
                self.assertEqual(expected, value,
                                 f'модель {model} не корректна работа __str__'
                                 )

    def test_verbose_name_and_help_text(self):
        """verbose_name и help_text в полях совпадает с ожидаемым."""
        post = PostModelTest.post
        field_verboses = {
            'text': ('Текст поста', 'Введите текст поста'),
            'pub_date': ('Дата создания', ),
            'author': ('Автор', ),
            'group': ('Группа', 'Выберите группу'),
        }
        for field, expected_value in field_verboses.items():
            with self.subTest(field=field):
                self.assertEqual(
                    post._meta.get_field(field).verbose_name,
                    expected_value[0]
                )
                if len(expected_value) > 1:
                    self.assertEqual(
                        post._meta.get_field(field).help_text,
                        expected_value[1]
                    )

# posts/tests/test_forms.py
import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Comment, Group, Post

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class TaskFormsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.groups = list()
        for num in range(3):
            cls.groups.append(
                Group.objects.create(
                    title='Тестовая группа ' + str(num),
                    slug='slug' + str(num),
                    description='Тестовое описание ' + str(num),
                )
            )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.user1 = User.objects.create_user(username='Author1')
        self.user2 = User.objects.create_user(username='Author2')
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user1)
        self.post = Post.objects.create(
            author=self.user1,
            text='Тестовый пост первого автора',
            group=TaskFormsTests.groups[0]
        )

    def test_post_create_form_correct(self):
        """проверяем форму создания поста"""

        form_fields_type = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }

        response = self.authorized_client.get(reverse('posts:post_create'))

        # Проверяем, что типы полей формы в словаре context
        # соответствуют ожиданиям
        for value, expected in form_fields_type.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                # Проверяет, что поле формы является экземпляром
                # указанного класса
                self.assertIsInstance(form_field, expected)

    def test_create_autorized(self):
        """проверяем создание поста авторизованым пользователем"""

        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )

        url_create = reverse('posts:post_create')
        count_begin = Post.objects.count()
        response = self.authorized_client.post(
            url_create,
            {'text': 'create',
             'group': TaskFormsTests.groups[0].pk,
             'image': uploaded
             },
        )
        self.assertEqual(
            response.status_code, 302,
            'Не верный статус ответа после создания поста'
        )
        self.assertEqual(
            count_begin + 1,
            Post.objects.count(),
            'Не работает создание поста'
        )
        self.assertTrue(
            Post.objects.filter(
                text='create',
                group=TaskFormsTests.groups[0].pk,
                image='posts/small.gif'
            ).exists()
        )

    def test_create_not_autorized(self):
        """проверяем создание поста не авторизованым пользователем"""
        url_login = reverse('login')
        url_create = reverse('posts:post_create')
        count_begin = Post.objects.count()
        response = self.guest_client.post(
            url_create,
            {'text': 'create',
             'group': TaskFormsTests.groups[0].pk
             },
            follow=True
        )
        self.assertRedirects(
            response,
            f'{url_login}?next={url_create}',
        )
        self.assertEqual(
            count_begin,
            Post.objects.count(),
            'Создался пост неавторизованым пользователем'
        )

    def test_post_edit_form_correct(self):
        """проверяем форму и правильность редактирования поста"""
        post_id = str(self.post.pk)
        post_text = self.post.text

        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': post_id})
        )
        form_fields_type = {
            'text': (forms.fields.CharField,
                     post_text
                     ),
            'group': (forms.fields.ChoiceField, self.post.group.pk),
        }

        # Проверяем, что типы полей формы в словаре context
        # соответствуют ожиданиям и их содержимое правильно
        for value, expected in form_fields_type.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                data_field = response.context.get('form').initial.get(value)
                # Проверяет, что поле формы является экземпляром
                # указанного класса и его содержимое правильно
                self.assertIsInstance(form_field, expected[0])
                self.assertEqual(data_field, expected[1])
        response = self.authorized_client.post(
            reverse('posts:post_edit',
                    kwargs={'post_id': str(self.post.pk)}
                    ),
            {'text': 'editing',
             },
        )
        self.assertRedirects(
            response,
            reverse('posts:post_detail',
                    kwargs={'post_id': str(self.post.pk)}
                    ),
            msg_prefix='Не работает редирект после редактирования поста'
        )

        post = Post.objects.get(pk=self.post.pk)
        self.assertEqual(
            post.text,
            'editing',
            'пост не редактируется('
        )
        self.assertIsNone(post.group, 'пост не редактируется(')

    def test_post_comment_user(self):
        """проверяем создание коментариев поста
           авторизованным пользователем"""

        text_comment = 'test text comment'
        post_id = str(self.post.pk)

        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': post_id})
        )
        form_fields_type = {
            'text': forms.fields.CharField,
        }

        # Проверяем, что типы полей формы в словаре context
        for value, expected in form_fields_type.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                # Проверяет, что поле формы является экземпляром
                # указанного класса
                self.assertIsInstance(form_field, expected)
        response = self.authorized_client.post(
            reverse('posts:add_comment',
                    kwargs={'post_id': post_id}
                    ),
            {'text': text_comment,
             },
        )
        self.assertRedirects(
            response,
            reverse('posts:post_detail',
                    kwargs={'post_id': str(self.post.pk)}
                    ),
            msg_prefix='Не работает редирект после коментирования поста'
        )

        # проверим, что на страницу поста передан один коментарий
        # и его содержимое соответствует ожидаемому
        # но опять же здесь было бы уместнее проверить, что комментарий
        # появился в базе, а так может мы со вьюхой напортачили и форма
        # то отработала, а на страницу коментарий не отдали в контексте
        with self.subTest(subTest='отображение коментария на странице поста'):
            response = self.guest_client.get(
                reverse('posts:post_detail', kwargs={'post_id': post_id})
            )
            self.assertEqual(len(response.context['comments']), 1)
            self.assertEqual(
                response.context['comments'][0].text,
                text_comment
            )
            self.assertEqual(
                response.context['comments'][0].author,
                self.user1
            )

    def test_post_comment_guest(self):
        """проверяем создание коментариев поста
           не авторизованным пользователем"""

        text_comment = 'test text comment guest'
        post_id = str(self.post.pk)

        # снова старый спор?
        # невозможность отправки формы комментирования не авторизованным
        # пользователем проверена в test_urls.py не важно какой тип запроса
        # будет GET или POST с формой или без
        # но если сильно надо, то повторимся здесь...
        self.guest_client.post(
            reverse('posts:add_comment',
                    kwargs={'post_id': post_id}
                    ),
            {'text': text_comment
             },
        )

        # проверим, что комментарий не появился в базе,
        self.assertEqual(
            Comment.objects.count(),
            0,
            'Не авторизованный пользователь смог прокоментировать пост'
        )

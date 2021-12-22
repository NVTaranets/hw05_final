# posts/tests/test_views.py
import datetime as dt
import shutil
import tempfile
from http import HTTPStatus

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files import File
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils.timezone import make_aware
from sorl.thumbnail import get_thumbnail

from ..models import Follow, Group, Post

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class TaskPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.groups = Group.objects.bulk_create(
            Group(
                pk=num,
                title='Тестовая группа ' + str(num),
                slug='slug' + str(num),
                description='Тестовое описание ' + str(num),
            ) for num in range(3)
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        # Создаем авторизованный клиент
        self.user1 = User.objects.create_user(username='Author1')
        self.user2 = User.objects.create_user(username='Author2')
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user1)
        self.posts = Post.objects.bulk_create(
            Post(
                pk=nom,
                author=self.user1,
                text='Тестовый пост первого автора №' + str(nom),
                group=TaskPagesTests.groups[0],
            ) for nom in range(settings.PAGINATOR_PER_PAGE + 1)
        )

        # заменим дату последнего созданного поста на "завтра"
        # для проверки сортировки и добавим ему картинку для
        # проверки вывода ее на страницы
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
        date_posts = dt.datetime.now() + dt.timedelta(days=1)
        post = Post.objects.get(pk=(self.posts[-1]).pk)
        post.pub_date = make_aware(date_posts)
        post.save()
        post.image.save(uploaded.name, File(uploaded))

        self.post = Post.objects.create(
            author=self.user2,
            text='Тестовый пост второго автора',
        )
        date_posts = (dt.datetime.now()
                      - dt.timedelta(days=1)
                      )
        self.post.pub_date = make_aware(date_posts)
        self.post.save()

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        # Собираем в словарь пары "имя_html_шаблона: reverse(name)"
        # если имя_html_шаблона повторяются, то добавляем
        # в конец ':любой не повторяюшийся текст' - он будет отброшен
        slug = TaskPagesTests.groups[0].slug
        username = self.user1.username
        post_id = self.posts[0].pk
        templates_pages_names = {
            'posts/index.html': reverse('posts:index'),
            'posts/group_list.html': reverse('posts:group_list',
                                             kwargs={'slug': slug}
                                             ),
            'posts/profile.html': reverse('posts:profile',
                                          kwargs={'username': username}
                                          ),
            'posts/post_detail.html:1': (
                reverse('posts:post_detail', kwargs={'post_id': post_id})
            ),
            'posts/post_detail.html:2': (
                reverse('posts:add_comment', kwargs={'post_id': post_id})
            ),
            'posts/create_post.html:1': (
                reverse('posts:post_edit', kwargs={'post_id': post_id})
            ),
            'posts/create_post.html:2': (
                reverse('posts:post_create')
            ),
        }
        # Проверяем, что при обращении к name
        # вызывается соответствующий HTML-шаблон
        for template, reverse_name in templates_pages_names.items():
            template = template.split(':')[0]
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(
                    reverse_name,
                    follow=True
                )
                self.assertTemplateUsed(response, template)

    def test_post_edit_page_correct(self):
        """проверяем форму и правильность редактирования поста"""
        post_id = str(self.posts[0].pk)
        post_text = self.posts[0].text

        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': post_id})
        )
        form_fields_type = {
            'text': (forms.fields.CharField,
                     post_text
                     ),
            'group': (forms.fields.ChoiceField, 0),
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
                    kwargs={'post_id': str(self.posts[0].pk)}
                    ),
            {'text': 'editing'}
        )
        post = Post.objects.get(pk=self.posts[0].pk)
        self.assertEqual(
            post.text,
            'editing',
            'пост не редактируется('
        )
        self.assertIsNone(post.group, 'пост не редактируется(')

    def test_paginator_and_sort(self):
        slug = TaskPagesTests.groups[0].slug
        username = self.user1.username
        post_text = self.posts[-1].text
        pages_tests = (
            reverse('posts:index'),
            reverse('posts:group_list',
                    kwargs={'slug': slug}
                    ),
            reverse('posts:profile',
                    kwargs={'username': username}
                    ),
        )
        for url in pages_tests:
            with self.subTest(url=url):
                count_obj_second_page = 1 + (url == reverse('posts:index'))
                response = self.authorized_client.get(url)
                self.assertEqual(len(response.context['page_obj']),
                                 settings.PAGINATOR_PER_PAGE,
                                 (f'Первая страница должна содержать '
                                  f'{settings.PAGINATOR_PER_PAGE} постов')
                                 )
                self.assertEqual(
                    post_text,
                    response.context['page_obj'][0].text,
                    'Проверьте сортировку постов на странице!!!'
                )
                response = self.authorized_client.get(url + '?page=2')
                self.assertEqual(len(response.context['page_obj']),
                                 count_obj_second_page
                                 )

    def test_group_posts(self):
        username3 = 'Author3'
        username2 = self.user2.username
        User.objects.create_user(username=username3)
        sub_tests = {
            'Созданный пост не отобразился на главной странице': (
                reverse('posts:index') + '?page=2',
                3
            ),
            'Созданный пост отобразился в чужом профиле': (
                reverse('posts:profile',
                        kwargs={'username': username3}
                        ),
                0
            ),
            'Созданный пост не отобразился в профиле автора': (
                reverse('posts:profile',
                        kwargs={'username': username2}
                        ),
                2
            ),
            'Созданный пост не отобразился в группе': (
                reverse('posts:group_list',
                        kwargs={'slug': TaskPagesTests.groups[2].slug}
                        ),
                1
            ),
            'Созданный пост отобразился не в своей группе': (
                reverse('posts:group_list',
                        kwargs={'slug': TaskPagesTests.groups[1].slug}
                        ),
                0
            )

        }
        self.authorized_client.force_login(self.user2)
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            {'text': 'create',
             'group': TaskPagesTests.groups[2].pk
             }
        )
        for sub_test in sub_tests:
            with self.subTest(text=sub_test):
                url, control = sub_tests[sub_test]
                response = self.authorized_client.get(url)
                self.assertEqual(len(response.context['page_obj']),
                                 control,
                                 sub_test
                                 )

    def test_image_on_pages(self):
        post = Post.objects.get(pk=(self.posts[-1]).pk)
        slug = post.group.slug
        username = post.author.username
        post_id = post.pk
        img_url = post.image
        thumbnail_url = get_thumbnail(img_url,
                                      '960x339',
                                      crop="center",
                                      upscale=True
                                      ).url
        pages_tests = (
            reverse('posts:index'),
            reverse('posts:group_list',
                    kwargs={'slug': slug}
                    ),
            reverse('posts:profile',
                    kwargs={'username': username}
                    ),
            reverse('posts:post_detail',
                    kwargs={'post_id': post_id}
                    ),
        )
        for url in pages_tests:
            with self.subTest(url=url):
                cache.clear()
                response = self.guest_client.get(url)
                self.assertContains(
                    response,
                    f'<img class=\"card-img my-2\" src=\"{thumbnail_url}\">',
                    1,
                    HTTPStatus.OK,
                    msg_prefix=(f'Ошибка вывода поста с '
                                f'изображением на странице {url}'
                                )
                )

    def test_cash_index_pages(self):
        url_index = reverse('posts:index')
        response = self.guest_client.get(url_index)
        post = Post.objects.create(
            author=self.user2,
            text='Тестовый пост',
        )
        date_posts = (dt.datetime.now()
                      - dt.timedelta(days=1)
                      )
        post.pub_date = make_aware(date_posts)
        post.save()
        self.assertEqual(
            self.guest_client.get(url_index).content,
            response.content,
            'Не работает кэш')
        cache.clear()
        self.assertNotEqual(
            self.guest_client.get(url_index).content,
            response.content,
            f'Не работает кэш или страница {url_index}')

    def test_follow(self):
        url_follow = reverse(
            'posts:profile_follow',
            kwargs={'username': self.user2.username}
        )
        self.authorized_client.get(url_follow)
        self.assertTrue(
            Follow.objects.filter(
                user=self.user1,
                author=self.user2
            ).exists(),
            'Не работает подписка на автора')

    def test_unfollow(self):
        url_unfollow = reverse(
            'posts:profile_unfollow',
            kwargs={'username': self.user2.username}
        )
        Follow.objects.create(
            user=self.user1,
            author=self.user2
        )
        self.authorized_client.get(url_unfollow)
        self.assertFalse(
            Follow.objects.filter(
                user=self.user1,
                author=self.user2
            ).exists(),
            'Не работает отписка от автора')

    def test_follow_index(self):
        Follow.objects.create(
            user=self.user1,
            author=self.user2
        )
        url_follow_index = reverse(
            'posts:follow_index'
        )
        response = self.authorized_client.get(url_follow_index)
        self.assertEqual(
            len(response.context['page_obj']),
            1,
            'Не отобразился пост на странице подписанного пользователя'
        )

    def test_not_follow_index(self):
        url_follow_index = reverse(
            'posts:follow_index'
        )
        response = self.authorized_client.get(url_follow_index)
        self.assertEqual(
            len(response.context['page_obj']),
            0,
            ('Отобразился пост на странице '
             'подписок не подписанного пользователя')
        )
